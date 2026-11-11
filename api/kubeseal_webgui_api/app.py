from contextlib import asynccontextmanager
import logging

import fastapi
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .app_config import fetch_sealed_secrets_cert, get_kubeseal_version, settings
from .logging_utils import REQUEST_ID_HEADER, RequestIdMiddleware
from .routers import config, kubernetes, kubeseal

LOGGER = logging.getLogger("kubeseal-webgui")


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
    fetch_sealed_secrets_cert()
    LOGGER.info("Startup tasks complete.")
    yield
    LOGGER.info("Shutting down kubeseal-webgui API.")


app = fastapi.FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:8080",
]

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
    kubeseal.router,
)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "Kubeseal-WebGui API"}
