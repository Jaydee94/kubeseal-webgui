import logging

from kubeseal_webgui_api.app_config import settings

LOGGER = logging.getLogger("kubeseal-webgui")


def kubernetes_resource_namespaces_parser(resources: list) -> list[str]:
    """Extract the metadata namespace from the provided resource list."""
    namespaces_list = set()

    for res in resources:
        namespaces_list.add(res.metadata.namespace)

    LOGGER.debug("Namespaces list %s", namespaces_list)
    return list(namespaces_list)


def kubernetes_resource_provider(core, resource: str):
    """Dynamic list provider for Kubernetes Core API resources."""
    provider = getattr(core, f"list_{resource}_for_all_namespaces", None)

    if not callable(provider):
        return None

    return provider(watch=False)


def kubernetes_resource_namespaces_resolver(core) -> list[str]:
    """Retrieve a list of namespaces from objects in the current kubernetes cluster."""
    LOGGER.info(
        "Resolving %s Namespaces from %s resources",
        core,
        settings.k8s_namespace_resource,
    )
    resources = kubernetes_resource_provider(core, settings.k8s_namespace_resource)

    if not resources:
        LOGGER.warning(
            "Kubernetes client does not provide access to %s resources",
            settings.k8s_namespace_resource,
        )
        return []
    if not resources.items:
        LOGGER.warning("No valid resource list available via %s", resources)
        return []

    return kubernetes_resource_namespaces_parser(resources.items)
