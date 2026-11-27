import logging
from contextlib import asynccontextmanager
from pathlib import Path

import fastapi
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse

from .app_config import (
    cors_origins,
    fetch_sealed_secrets_cert,
    get_kubeseal_version,
    settings,
)
from .clusters import ClusterConfigError, get_clusters
from .logging_utils import LOGGER_NAME, REQUEST_ID_HEADER, RequestIdMiddleware
from .routers import clusters, config, kubernetes, kubeseal

LOGGER = logging.getLogger(LOGGER_NAME)


def check_clusters() -> None:
    """Fail at start-up, not on the first request, if a cluster is unusable."""
    try:
        configured = get_clusters()
    except ClusterConfigError as error:
        LOGGER.error("Invalid cluster configuration: %s", error)
        raise
    for cluster in configured:
        LOGGER.info(
            "Cluster '%s': certificate '%s'%s",
            cluster.name,
            cluster.cert,
            ", in this cluster" if cluster.in_cluster else "",
        )
        # Only for an explicit list: without one, a missing certificate stays
        # what it always was, an error of the first sealing request.
        explicit = bool(settings.kubeseal_clusters_file)
        if explicit and not settings.mock_enabled and not Path(cluster.cert).is_file():
            message = (
                f"The certificate '{cluster.cert}' of cluster '{cluster.name}' "
                "does not exist."
            )
            LOGGER.error(message)
            raise ClusterConfigError(message)


@asynccontextmanager
async def lifespan(fastapi_app: fastapi.FastAPI):  # noqa: ANN201 skipcq: PYL-W0613
    # Resolved here, once: a deployment with an unusable kubeseal binary has
    # to fail at start-up and not on the first request.
    kubeseal_version = get_kubeseal_version()
    LOGGER.info(
        "Starting kubeseal-webgui API (kubeseal version: %s, binary: '%s', "
        "certificate: '%s', certificate auto-fetch: %s, mock mode: %s)",
        kubeseal_version,
        settings.kubeseal_binary,
        settings.kubeseal_cert,
        settings.kubeseal_autofetch,
        settings.mock_enabled,
    )
    LOGGER.info(
        "Cross-origin requests are allowed from: %s",
        ", ".join(origins) or "nowhere (ORIGIN_URL is not an absolute URL)",
    )
    fetch_sealed_secrets_cert()
    check_clusters()
    LOGGER.info("Startup tasks complete.")
    yield
    LOGGER.info("Shutting down kubeseal-webgui API.")


# /docs is defined below, see swagger_ui().
app = fastapi.FastAPI(lifespan=lifespan, docs_url=None)

# Only needed when the UI is not served from the same origin as the API, as
# with the dev server. The default is the dev server's address.
origins = cors_origins(settings.origin_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Lets the UI read the id and show it next to error messages.
    expose_headers=[REQUEST_ID_HEADER],
)
# Added last so it is the outermost middleware and covers CORS responses too.
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(RequestValidationError)
async def log_validation_error(
    request: fastapi.Request, exc: RequestValidationError
) -> JSONResponse:
    # Only location and error type are logged: the offending input (which the
    # validation error also carries) may be a cleartext secret.
    LOGGER.warning(
        "Rejected invalid request %s %s: %s",
        request.method,
        request.url.path,
        "; ".join(
            f"{'.'.join(str(part) for part in error.get('loc', ()))} "
            f"({error.get('type')})"
            for error in exc.errors()
        ),
    )
    return await request_validation_exception_handler(request, exc)


app.include_router(
    kubernetes.router,
)
app.include_router(
    config.router,
)
app.include_router(
    clusters.router,
)
app.include_router(
    kubeseal.router,
)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "Kubeseal-WebGui API"}


@app.get("/docs", include_in_schema=False)
def swagger_ui() -> HTMLResponse:
    # The schema is loaded by a URL relative to this page. FastAPI's own /docs
    # page uses "/openapi.json", which misses the API when the UI's nginx
    # serves it under a path prefix (e.g. https://example.com/kubeseal-webgui/docs).
    return get_swagger_ui_html(
        openapi_url="openapi.json", title=f"{app.title} - Swagger UI"
    )
