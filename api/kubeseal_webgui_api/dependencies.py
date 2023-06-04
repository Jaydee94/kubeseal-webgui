from kubeseal_webgui_api.app_config import settings
from kubeseal_webgui_api.internal import (
    KubernetesClient,
    KubesealClient,
    MockKubernetesClient,
    MockKubesealClient,
)


def get_kubeseal_client() -> KubesealClient:
    if settings.mock_enabled:
        return MockKubesealClient()

    return KubesealClient(
        cert=settings.kubeseal_cert,
        binary=settings.kubeseal_binary,
        namespace=settings.sealed_secrets_namespace,
        controller=settings.sealed_secrets_controller_name,
    )


def get_kubernetes_client() -> KubernetesClient:
    if settings.mock_enabled:
        return MockKubernetesClient(namespace_count=settings.mock_namespace_count)

    return KubernetesClient()
