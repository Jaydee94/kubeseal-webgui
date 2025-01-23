from contextlib import asynccontextmanager
import logging
import time

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .app_config import fetch_sealed_secrets_cert
from .routers import config, kubernetes, kubeseal

LOGGER = logging.getLogger("kubeseal-webgui")

exporter = PrometheusMetricReader()
metrics.set_meter_provider(MeterProvider(metric_readers=[exporter]))
meter = metrics.get_meter("kubeseal-webgui")

http_requests = meter.create_counter(
    name="kubeseal_webgui_http_requests_total",
    description="Total HTTP requests",
    unit="1",
)
http_latency = meter.create_histogram(
    name="kubeseal_webgui_http_request_latency_seconds",
    description="HTTP request latency in seconds",
    unit="seconds",
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

    # Record metrics
    http_requests.add(1, {"method": request.method, "endpoint": request.url.path, "http_status": response.status_code})
    http_latency.record(process_time, {"method": request.method, "endpoint": request.url.path})

    return response

@app.get("/metrics")
def metrics_endpoint() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

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
