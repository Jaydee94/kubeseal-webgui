import pytest
from fastapi.testclient import TestClient

from kubeseal_webgui_api.app import app
from kubeseal_webgui_api.routers import kubernetes
from kubeseal_webgui_api.routers.models import ExistingSealedSecret


def dummy_namespace_resolver() -> list[str]:
    return ["default", "namespace-one", "namespace-two"]


def broken_namespace_resolver() -> list[str]:
    raise RuntimeError("Go away")


def dummy_sealed_secret_resolver(namespace: str) -> list[ExistingSealedSecret]:
    return [
        ExistingSealedSecret(name=f"{namespace}-first", keys=["ALPHA", "BETA"]),
        ExistingSealedSecret(name=f"{namespace}-second", keys=["DELTA"]),
    ]


def broken_sealed_secret_resolver(namespace: str) -> list[ExistingSealedSecret]:
    raise RuntimeError(f"Go away from {namespace}")


client = TestClient(app)


def test_get_namespaces_with_exception():
    kubernetes.namespace_resolver = broken_namespace_resolver
    response = client.get("/namespaces")
    assert response.status_code == 500
    assert response.json() == {"detail": "Can't get namespaces from cluster."}


def test_get_namespaces():
    kubernetes.namespace_resolver = dummy_namespace_resolver
    response = client.get("/namespaces")
    assert response.status_code == 200
    assert response.json() == dummy_namespace_resolver()


def test_get_sealed_secrets_with_exception():
    kubernetes.sealed_secret_resolver = broken_sealed_secret_resolver
    response = client.get("/sealed-secrets/default")
    assert response.status_code == 500
    assert response.json() == {"detail": "Can't get SealedSecrets from cluster."}


def test_get_sealed_secrets():
    namespace = "default"
    kubernetes.sealed_secret_resolver = dummy_sealed_secret_resolver
    response = client.get(f"/sealed-secrets/{namespace}")
    assert response.status_code == 200
    assert response.json() == [
        item.model_dump() for item in dummy_sealed_secret_resolver(namespace)
    ]


@pytest.mark.parametrize(
    "namespace",
    ["Not_Valid", "with.dot", "ends-with-dash-", "a" * 64, "line%0Abreak"],
)
def test_get_sealed_secrets_rejects_an_invalid_namespace(namespace):
    def resolver_must_not_run(_namespace):
        raise AssertionError("the resolver was called")

    kubernetes.sealed_secret_resolver = resolver_must_not_run
    response = client.get(f"/sealed-secrets/{namespace}")
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid namespace name."}
