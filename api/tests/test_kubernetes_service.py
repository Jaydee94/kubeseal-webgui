from typing import List

from fastapi.testclient import TestClient

from kubeseal_webgui_api.app import app
from kubeseal_webgui_api.routers import kubernetes


def dummy_namespace_resolver() -> List[str]:
    return ["default", "namespace-one", "namespace-two"]


def broken_namespace_resolver() -> List[str]:
    raise RuntimeError("Go away")


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
