import logging

from kubernetes import client

from kubeseal_webgui_api.logging_utils import LOGGER_NAME
from kubeseal_webgui_api.routers.kubernetes_utils import ensure_incluster_config

LOGGER = logging.getLogger(LOGGER_NAME)


def kubernetes_namespaces_resolver() -> list[str]:
    """Retrieve a list of namespaces from current kubernetes cluster."""
    ensure_incluster_config()

    LOGGER.debug("Resolving in-cluster Namespaces")
    namespaces = client.CoreV1Api().list_namespace()
    if not isinstance(namespaces, client.V1NamespaceList) or not namespaces.items:
        LOGGER.warning("No valid namespace list available via %s", namespaces)
        return []

    names = [
        namespace.metadata.name
        for namespace in namespaces.items
        if namespace.metadata is not None and namespace.metadata.name
    ]
    LOGGER.info("Resolved %d in-cluster Namespaces", len(names))
    LOGGER.debug("Namespaces list %s", names)
    return names
