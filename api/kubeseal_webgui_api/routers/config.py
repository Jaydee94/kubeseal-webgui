import logging

from fastapi import APIRouter, Depends, HTTPException

from kubeseal_webgui_api.dependencies import get_kubeseal_client
from kubeseal_webgui_api.internal import KubesealClient
from kubeseal_webgui_api.routers.models import WebGuiConfig

LOGGER = logging.getLogger("kubeseal-webgui")
router = APIRouter()


@router.get("/config", response_model=WebGuiConfig)
def get_configs(
    client: KubesealClient = Depends(get_kubeseal_client),  # noqa: B008
) -> WebGuiConfig:
    try:
        kubeseal_version = client.get_version()
        return WebGuiConfig(kubeseal_version=kubeseal_version)
    except RuntimeError:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve application configs."
        )
