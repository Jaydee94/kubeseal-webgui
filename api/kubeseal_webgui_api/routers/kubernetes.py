import logging
from typing import List

import fastapi

from kubeseal_webgui_api.app_config import settings
from kubeseal_webgui_api.internal import (
    InclusterCoreClient,
    MockCoreClient,
    kubernetes_namespaces_resolver,
    kubernetes_resource_namespaces_resolver,
)

router = fastapi.APIRouter()
LOGGER = logging.getLogger("kubeseal-webgui")

if settings.mock_enabled:
    core_client = MockCoreClient(namespace_count=settings.mock_namespace_count)
else:
    core_client = InclusterCoreClient()

if settings.k8s_namespace_resource == "namespace":
    namespace_resolver = kubernetes_namespaces_resolver
else:
    namespace_resolver = kubernetes_resource_namespaces_resolver


@router.get("/namespaces", response_model=List[str])
def get_namespaces() -> List[str]:
    try:
        return namespace_resolver(core_client)
    except RuntimeError:
        raise fastapi.HTTPException(
            status_code=500, detail="Can't get namespaces from cluster."
        )
