import logging
from typing import Dict

import fastapi

from kubeseal_webgui_api.app_config import settings

LOGGER = logging.getLogger("uvicorn")
router = fastapi.APIRouter()


@router.get("/config")
def get_configs() -> Dict[str, str]:
    if settings.mock_enabled:
        return {"kubeseal_version": "0.1.0"}
    try:
        return {
            "kubeseal_version": settings.kubeseal_version,
        }
    except RuntimeError:
        raise fastapi.HTTPException(
            status_code=500, detail="Failed to retrieve application configs."
        )
