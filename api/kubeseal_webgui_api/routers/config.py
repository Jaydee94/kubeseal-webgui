import logging

import fastapi

from kubeseal_webgui_api.app_config import settings
from kubeseal_webgui_api.routers.models import WebGuiConfig

LOGGER = logging.getLogger("kubeseal-webgui")
router = fastapi.APIRouter()


@router.get("/config", response_model=WebGuiConfig)
def get_configs() -> WebGuiConfig:
    if settings.mock_enabled:
        return WebGuiConfig(kubeseal_version="0.1.0")
    try:
        return WebGuiConfig(kubeseal_version=settings.kubeseal_version)
    except RuntimeError:
        raise fastapi.HTTPException(
            status_code=500, detail="Failed to retrieve application configs."
        )
