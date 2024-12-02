from contextlib import asynccontextmanager
import logging
import time

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .app_config import fetch_sealed_secrets_cert
from .routers import config, kubernetes, kubeseal

LOGGER = logging.getLogger("kubeseal-webgui")

HTTP_REQUESTS = Counter(
    "kubeseal_webgui_http_requests_total", "Total HTTP requests", ["method", "endpoint", "http_status"]
)
HTTP_LATENCY = Histogram(
    "kubeseal_webgui_http_request_latency_seconds", "HTTP request latency in seconds", ["method", "endpoint"]
)

@asynccontextmanager
async def lifespan(fastapi_app: fastapi.FastAPI):  # noqa: ANN201 skipcq: PYL-W0613
    LOGGER.info("Running startup tasks...")
    fetch_sealed_secrets_cert()
    LOGGER.info("Startup tasks complete.")
    yield


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
)

@app.middleware("http")
async def prometheus_middleware(request: fastapi.Request, call_next):  # noqa: ANN001, ANN201
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    HTTP_REQUESTS.labels(
        method=request.method, endpoint=request.url.path, http_status=response.status_code
    ).inc()
    HTTP_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(process_time)

    return response

@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

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
