import logging

import fastapi
from fastapi.middleware.cors import CORSMiddleware

from .app_config import settings
from .dependencies import get_kubeseal_client
from .routers import config, kubernetes, kubeseal

LOGGER = logging.getLogger("kubeseal-webgui")

app = fastapi.FastAPI()

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


@app.on_event("startup")
def startup_event():
    LOGGER.info("Running startup tasks...")
    if settings.kubeseal_autofetch:
        with open(settings.kubeseal_cert, "w") as file:
            LOGGER.info("Saving certificate in '%s'", settings.kubeseal_cert)
            file.write(get_kubeseal_client().get_certificate())
    LOGGER.info("Startup tasks complete.")


@app.get("/")
def root():
    return {"status": "Kubeseal-WebGui API"}
