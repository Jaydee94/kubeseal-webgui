import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from kubeseal_webgui_api.dependencies import get_kubernetes_client
from kubeseal_webgui_api.internal import KubernetesClient

LOGGER = logging.getLogger("kubeseal-webgui")
router = APIRouter()


@router.get("/namespaces", response_model=List[str])
def get_namespaces(
    client: KubernetesClient = Depends(get_kubernetes_client),  # noqa: B008
) -> List[str]:
    try:
        return client.get_namespaces()
    except RuntimeError:
        raise HTTPException(
            status_code=500, detail="Can't get namespaces from cluster."
        )
