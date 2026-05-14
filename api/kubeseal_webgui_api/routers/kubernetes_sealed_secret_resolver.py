import logging

from kubernetes import client, config

from kubeseal_webgui_api.routers.models import ExistingSealedSecret

LOGGER = logging.getLogger("kubeseal-webgui")


def kubernetes_sealed_secret_resolver(namespace: str) -> list[ExistingSealedSecret]:
    """Retrieve SealedSecrets and their keys for a namespace from the cluster."""
    config.load_incluster_config()
    custom_objects_api = client.CustomObjectsApi()

    LOGGER.info("Resolving in-cluster SealedSecrets for namespace '%s'", namespace)
    sealed_secret_list = custom_objects_api.list_namespaced_custom_object(
        group="bitnami.com",
        version="v1alpha1",
        namespace=namespace,
        plural="sealedsecrets",
    )

    resolved_sealed_secrets: list[ExistingSealedSecret] = []
    items = sealed_secret_list.get("items", [])
    if not isinstance(items, list):
        LOGGER.warning("Unexpected SealedSecrets response payload type for namespace '%s'", namespace)
        return resolved_sealed_secrets

    for sealed_secret in items:
        if not isinstance(sealed_secret, dict):
            continue

        metadata = sealed_secret.get("metadata", {})
        spec = sealed_secret.get("spec", {})
        if not isinstance(metadata, dict) or not isinstance(spec, dict):
            continue

        name = metadata.get("name")
        encrypted_data = spec.get("encryptedData", {})
        if not isinstance(name, str) or not isinstance(encrypted_data, dict):
            continue

        keys = sorted(encrypted_data.keys())
        resolved_sealed_secrets.append(ExistingSealedSecret(name=name, keys=keys))

    return sorted(resolved_sealed_secrets, key=lambda sealed_secret: sealed_secret.name)
