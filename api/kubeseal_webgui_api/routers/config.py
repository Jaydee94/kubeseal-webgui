import fastapi

from kubeseal_webgui_api.app_config import get_kubeseal_version
from kubeseal_webgui_api.routers.models import WebGuiConfig

router = fastapi.APIRouter()


@router.get("/config", response_model=WebGuiConfig)
def get_configs() -> WebGuiConfig:
    return WebGuiConfig(kubeseal_version=get_kubeseal_version())
