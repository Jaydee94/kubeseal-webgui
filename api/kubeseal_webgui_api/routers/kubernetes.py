import logging
import random
import string
from typing import List

import fastapi
from kubernetes import client, config

from kubeseal_webgui_api.app_config import settings

router = fastapi.APIRouter()
LOGGER = logging.getLogger(__name__)


@router.get("/namespaces")
def get_namespaces() -> List[str]:
    if settings.mock_enabled:
        return generate_namespace_names(settings.mock_namespace_count)
    try:
        return get_incluster_namespaces()
    except RuntimeError:
        raise fastapi.HTTPException(
            status_code=500, detail="Can`t get namespaces from cluster."
        )


def get_incluster_namespaces() -> list[str]:
    """Retrieve a list of namespaces from current kubernetes cluster."""
    config.load_incluster_config()
    namespaces_list = []

    LOGGER.info("Resolving in-cluster Namespaces")
    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace()
    if isinstance(namespaces, client.V1NamespaceList) and namespaces.items:
        for ns in namespaces.items:
            namespaces_list.append(ns.metadata.name)
    else:
        LOGGER.warning("No valid namespace list available via %s", namespaces)

    LOGGER.debug("Namespaces list %s", namespaces_list)
    return namespaces_list


def random_string(length):
    return "".join(random.choice(string.ascii_lowercase) for i in range(length))


def generate_namespace_names(count: int):
    result = []
    max_length = 10
    [result.append(random_string(random.randint(1, max_length))) for i in range(count)]
    return result
