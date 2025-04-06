import logging

from kubernetes import client

LOGGER = logging.getLogger("kubeseal-webgui")


def kubernetes_namespaces_parser(resources: list) -> list[str]:
    """Extract the metadata name from the provided namespace list."""
    namespaces_list = []

    for ns in resources:
        namespaces_list.append(ns.metadata.name)

    LOGGER.debug("Namespaces list %s", namespaces_list)
    return namespaces_list


def kubernetes_namespaces_resolver(core) -> list[str]:
    """Retrieve a list of namespaces from current kubernetes cluster."""
    LOGGER.info("Resolving %s Namespaces", core)
    namespaces = core.list_namespace()

    if isinstance(namespaces, client.V1NamespaceList) and namespaces.items:
        return kubernetes_namespaces_parser(namespaces.items)

    LOGGER.warning("No valid namespace list available via %s", namespaces)
    return []
