from contextlib import asynccontextmanager
import logging

import fastapi
from fastapi.middleware.cors import CORSMiddleware

from .app_config import fetch_sealed_secrets_cert
from .routers import config, kubernetes, kubeseal

LOGGER = logging.getLogger("kubeseal-webgui")


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
