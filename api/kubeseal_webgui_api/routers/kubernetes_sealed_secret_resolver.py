import logging

from kubernetes import client

from kubeseal_webgui_api.logging_utils import LOGGER_NAME
from kubeseal_webgui_api.routers.kubernetes_utils import ensure_incluster_config
from kubeseal_webgui_api.routers.models import ExistingSealedSecret

LOGGER = logging.getLogger(LOGGER_NAME)


def kubernetes_sealed_secret_resolver(namespace: str) -> list[ExistingSealedSecret]:
    """Retrieve SealedSecrets and their keys for a namespace from the cluster."""
    ensure_incluster_config()
    custom_objects_api = client.CustomObjectsApi()

    LOGGER.debug("Resolving in-cluster SealedSecrets for namespace '%s'", namespace)
    sealed_secret_list = custom_objects_api.list_namespaced_custom_object(
        group="bitnami.com",
        version="v1alpha1",
        namespace=namespace,
        plural="sealedsecrets",
    )

    items = (
        sealed_secret_list.get("items", [])
        if isinstance(sealed_secret_list, dict)
        else None
    )
    if not isinstance(items, list):
        LOGGER.warning(
            "Unexpected SealedSecrets response payload type for namespace '%s'",
            namespace,
        )
        return []

    resolved_sealed_secrets: list[ExistingSealedSecret] = []

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
