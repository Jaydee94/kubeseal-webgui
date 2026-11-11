import logging
from typing import List

import fastapi

from kubeseal_webgui_api.app_config import settings
from kubeseal_webgui_api.routers.kubernetes_namespace_resolver import (
    kubernetes_namespaces_resolver,
)
from kubeseal_webgui_api.routers.mock_namespace_resolver import mock_namespaces_resolver
from kubeseal_webgui_api.routers.mock_sealed_secret_resolver import (
    mock_sealed_secret_resolver,
)
from kubeseal_webgui_api.routers.models import ExistingSealedSecret
from kubeseal_webgui_api.routers.kubernetes_sealed_secret_resolver import (
    kubernetes_sealed_secret_resolver,
)

router = fastapi.APIRouter()
LOGGER = logging.getLogger("kubeseal-webgui")

if settings.mock_enabled:
    namespace_resolver = mock_namespaces_resolver
    sealed_secret_resolver = mock_sealed_secret_resolver
else:
    namespace_resolver = kubernetes_namespaces_resolver
    sealed_secret_resolver = kubernetes_sealed_secret_resolver


@router.get("/namespaces", response_model=List[str])
def get_namespaces() -> List[str]:
    # Kubernetes client errors (e.g. a 403 caused by missing RBAC) are not
    # RuntimeErrors, hence the broad catch at this API boundary.
    try:
        return namespace_resolver()
    except Exception:
        LOGGER.exception("Failed to list namespaces from the cluster.")
        raise fastapi.HTTPException(
            status_code=500, detail="Can't get namespaces from cluster."
        ) from None


@router.get("/sealed-secrets/{namespace}", response_model=List[ExistingSealedSecret])
def get_sealed_secrets(namespace: str) -> List[ExistingSealedSecret]:
    try:
        return sealed_secret_resolver(namespace)
    except Exception:
        LOGGER.exception(
            "Failed to list SealedSecrets in namespace '%s' from the cluster.",
            namespace,
        )
        raise fastapi.HTTPException(
            status_code=500, detail="Can't get SealedSecrets from cluster."
        ) from None
