import logging

from kubernetes import client, config

from kubeseal_webgui_api.routers.kubernetes_utils import fix_incluster_bearer_token
from kubeseal_webgui_api.routers.models import ExistingSealedSecret

LOGGER = logging.getLogger("kubeseal-webgui")


def kubernetes_sealed_secret_resolver(namespace: str) -> list[ExistingSealedSecret]:
    """Retrieve SealedSecrets and their keys for a namespace from the cluster."""
    config.load_incluster_config()
    fix_incluster_bearer_token()
    custom_objects_api = client.CustomObjectsApi()

    LOGGER.debug("Resolving in-cluster SealedSecrets for namespace '%s'", namespace)
    sealed_secret_list = custom_objects_api.list_namespaced_custom_object(
        group="bitnami.com",
        version="v1alpha1",
        namespace=namespace,
        plural="sealedsecrets",
    )

    resolved_sealed_secrets: list[ExistingSealedSecret] = []
    items = sealed_secret_list.get("items", [])
    if not isinstance(items, list):
        LOGGER.warning(
            "Unexpected SealedSecrets response payload type for namespace '%s'",
            namespace,
        )
        return resolved_sealed_secrets

    skipped = 0
    for sealed_secret in items:
        if not isinstance(sealed_secret, dict):
            skipped += 1
            continue

        metadata = sealed_secret.get("metadata", {})
        spec = sealed_secret.get("spec", {})
        if not isinstance(metadata, dict) or not isinstance(spec, dict):
            skipped += 1
            continue

        name = metadata.get("name")
        encrypted_data = spec.get("encryptedData", {})
        if not isinstance(name, str) or not isinstance(encrypted_data, dict):
            skipped += 1
            continue

        keys = sorted(encrypted_data.keys())
        resolved_sealed_secrets.append(ExistingSealedSecret(name=name, keys=keys))

    if skipped:
        LOGGER.warning(
            "Skipped %d malformed SealedSecret object(s) in namespace '%s'",
            skipped,
            namespace,
        )
    LOGGER.info(
        "Resolved %d in-cluster SealedSecrets for namespace '%s'",
        len(resolved_sealed_secrets),
        namespace,
    )
    return sorted(resolved_sealed_secrets, key=lambda sealed_secret: sealed_secret.name)
