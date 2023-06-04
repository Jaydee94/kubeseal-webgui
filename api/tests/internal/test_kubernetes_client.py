from typing import List
from unittest.mock import Mock

import pytest
from kubernetes.client import ApiClient, V1Namespace, V1NamespaceList, V1ObjectMeta

from kubeseal_webgui_api.internal.kubernetes_client import (
    KubernetesClient,
    MockKubernetesClient,
)


@pytest.fixture
def namespace_metadata() -> V1ObjectMeta:
    return V1ObjectMeta(name="test")


@pytest.fixture
def namespace_items(namespace_metadata):
    return [V1Namespace(metadata=namespace_metadata)]


@pytest.fixture
def namespace_list(namespace_items) -> List[V1Namespace]:
    return V1NamespaceList(items=namespace_items)


@pytest.fixture
def api_client() -> ApiClient:
    client = Mock()
    client.select_header_accept = lambda accept: accept[0]


def test_kubernetes_client_get_namespaces(api_client, namespace_list):
    api_client.call_api = lambda _: namespace_list

    subject = KubernetesClient(api_client=api_client)
    result = subject.get_namespaces()

    assert len(result) == 1
    assert result[0] == "test"


def test_mock_kubernetes_client_get_namespaces():
    subject = MockKubernetesClient(namespace_count=10)
    result = subject.get_namespaces()

    assert len(result) == 10
