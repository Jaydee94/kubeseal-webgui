import logging
from typing import List

import fastapi

from kubeseal_webgui_api.app_config import settings
from kubeseal_webgui_api.routers.kubernetes_namespace_resolver import (
    kubernetes_namespaces_resolver,
)
from kubeseal_webgui_api.routers.mock_namespace_resolver import mock_namespaces_resolver

router = fastapi.APIRouter()
LOGGER = logging.getLogger("kubeseal-webgui")

if settings.mock_enabled:
    namespace_resolver = mock_namespaces_resolver
else:
    namespace_resolver = kubernetes_namespaces_resolver


@router.get("/namespaces")
def get_namespaces() -> List[str]:
    try:
        return namespace_resolver()
    except RuntimeError:
        raise fastapi.HTTPException(
            status_code=500, detail="Can't get namespaces from cluster."
        )
