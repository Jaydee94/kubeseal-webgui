import logging

import fastapi
from fastapi.middleware.cors import CORSMiddleware

from .app_config import fetch_sealed_secrets_cert, LOGGER, settings
from .routers import config, kubernetes, kubeseal

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.origin_url],
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


@app.on_event("startup")
def startup_event():
    LOGGER.info("Running startup tasks...")
    fetch_sealed_secrets_cert()
    LOGGER.info("Startup tasks complete.")


@app.get("/")
def root():
    return {"status": "Kubeseal-WebGui API"}
