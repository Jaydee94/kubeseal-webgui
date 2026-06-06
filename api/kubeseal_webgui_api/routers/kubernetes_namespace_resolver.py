import logging

from kubernetes import client, config

from kubeseal_webgui_api.routers.kubernetes_utils import fix_incluster_bearer_token

LOGGER = logging.getLogger("kubeseal-webgui")


def kubernetes_namespaces_resolver() -> list[str]:
    """Retrieve a list of namespaces from current kubernetes cluster."""
    config.load_incluster_config()
    fix_incluster_bearer_token()
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
