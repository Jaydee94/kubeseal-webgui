import logging

import fastapi

from kubeseal_webgui_api.app_config import settings
from kubeseal_webgui_api.logging_utils import LOGGER_NAME
from kubeseal_webgui_api.routers.kubernetes_namespace_resolver import (
    kubernetes_namespaces_resolver,
)
from kubeseal_webgui_api.routers.kubernetes_sealed_secret_resolver import (
    kubernetes_sealed_secret_resolver,
)
from kubeseal_webgui_api.routers.mock_namespace_resolver import mock_namespaces_resolver
from kubeseal_webgui_api.routers.mock_sealed_secret_resolver import (
    mock_sealed_secret_resolver,
)
from kubeseal_webgui_api.routers.models import ExistingSealedSecret

router = fastapi.APIRouter()
LOGGER = logging.getLogger(LOGGER_NAME)


def namespace_resolver() -> list[str]:
    """List the namespaces of the cluster, or made-up ones in mock mode."""
    if settings.mock_enabled:
        return mock_namespaces_resolver()
    return kubernetes_namespaces_resolver()


def sealed_secret_resolver(namespace: str) -> list[ExistingSealedSecret]:
    """List the SealedSecrets of a namespace, or made-up ones in mock mode."""
    if settings.mock_enabled:
        return mock_sealed_secret_resolver(namespace)
    return kubernetes_sealed_secret_resolver(namespace)


@router.get("/namespaces", response_model=list[str])
def get_namespaces() -> list[str]:
    # Kubernetes client errors (e.g. a 403 caused by missing RBAC) are not
    # RuntimeErrors, hence the broad catch at this API boundary.
    try:
        return namespace_resolver()
    except Exception:
        LOGGER.exception("Failed to list namespaces from the cluster.")
        raise fastapi.HTTPException(
            status_code=500, detail="Can't get namespaces from cluster."
        ) from None


@router.get("/sealed-secrets/{namespace}", response_model=list[ExistingSealedSecret])
def get_sealed_secrets(namespace: str) -> list[ExistingSealedSecret]:
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
