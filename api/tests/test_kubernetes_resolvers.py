import datetime
import logging
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from kubernetes import client
from kubernetes.config import ConfigException, incluster_config

from kubeseal_webgui_api.app import app
from kubeseal_webgui_api.app_config import settings
from kubeseal_webgui_api.routers import (
    kubernetes,
    kubernetes_namespace_resolver,
    kubernetes_sealed_secret_resolver,
    kubernetes_utils,
)
from kubeseal_webgui_api.routers.models import ExistingSealedSecret

# Other test modules replace these module attributes without restoring them.
ORIGINAL_NAMESPACE_RESOLVER = kubernetes.namespace_resolver
ORIGINAL_SEALED_SECRET_RESOLVER = kubernetes.sealed_secret_resolver

http_client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_cluster_config(monkeypatch) -> Iterator[None]:
    monkeypatch.setattr(kubernetes_utils._state, "config_loaded", False)
    saved_default = client.Configuration._default
    client.Configuration.set_default(None)
    yield
    client.Configuration.set_default(saved_default)


@pytest.fixture
def original_resolvers(monkeypatch):
    monkeypatch.setattr(kubernetes, "namespace_resolver", ORIGINAL_NAMESPACE_RESOLVER)
    monkeypatch.setattr(
        kubernetes, "sealed_secret_resolver", ORIGINAL_SEALED_SECRET_RESOLVER
    )


def fake_loader(monkeypatch, token_key: str) -> list[int]:
    """Replace load_incluster_config; it stores a token under `token_key`."""
    calls: list[int] = []

    def load() -> None:
        calls.append(len(calls) + 1)
        configuration = client.Configuration()
        configuration.api_key[token_key] = f"bearer token-{len(calls)}"
        client.Configuration.set_default(configuration)

    monkeypatch.setattr(kubernetes_utils.config, "load_incluster_config", load)
    return calls


def current_token() -> str:
    settings_for_auth = client.Configuration.get_default_copy().auth_settings()
    token = settings_for_auth["BearerToken"]["value"]
    assert token is not None
    return token


def test_cluster_config_is_loaded_once(monkeypatch):
    calls = fake_loader(monkeypatch, "BearerToken")

    for _ in range(3):
        kubernetes_utils.ensure_incluster_config()

    assert calls == [1]
    assert current_token() == "bearer token-1"


def test_client_that_needs_the_token_fix_is_reloaded_every_time(monkeypatch):
    # Such a client refreshes rotated tokens only under 'authorization'.
    calls = fake_loader(monkeypatch, "authorization")

    kubernetes_utils.ensure_incluster_config()
    assert current_token() == "bearer token-1"
    kubernetes_utils.ensure_incluster_config()

    assert calls == [1, 2]
    assert current_token() == "bearer token-2"


def test_failed_load_is_retried(monkeypatch):
    attempts: list[int] = []

    def failing_load() -> None:
        attempts.append(1)
        raise ConfigException("Service host/port is not set.")

    monkeypatch.setattr(kubernetes_utils.config, "load_incluster_config", failing_load)

    for _ in range(2):
        with pytest.raises(ConfigException):
            kubernetes_utils.ensure_incluster_config()
    assert len(attempts) == 2


def test_rotated_service_account_token_is_picked_up_after_one_load(
    monkeypatch, tmp_path
):
    """The installed client re-reads the token file although we load once."""
    token_file = tmp_path / "token"
    token_file.write_text("first-token")
    ca_file = tmp_path / "ca.crt"
    ca_file.write_text("certificate")
    monkeypatch.setattr(incluster_config, "SERVICE_TOKEN_FILENAME", str(token_file))
    monkeypatch.setattr(incluster_config, "SERVICE_CERT_FILENAME", str(ca_file))
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    monkeypatch.setenv("KUBERNETES_SERVICE_PORT", "443")

    class Clock:
        """Stands in for `datetime.datetime` in the client's token loader."""

        skew = datetime.timedelta(0)

        @classmethod
        def now(cls) -> datetime.datetime:
            return datetime.datetime.now() + cls.skew  # noqa: DTZ005 like the client

    monkeypatch.setattr(
        incluster_config,
        "datetime",
        SimpleNamespace(datetime=Clock, timedelta=datetime.timedelta),
    )

    kubernetes_utils.ensure_incluster_config()
    assert current_token() == "bearer first-token"

    # the kubelet rotates the projected token; the client checks every minute
    token_file.write_text("second-token")
    Clock.skew = datetime.timedelta(minutes=2)
    kubernetes_utils.ensure_incluster_config()

    assert kubernetes_utils._state.config_loaded is True
    assert current_token() == "bearer second-token"
    # API objects are created per request and must see the new token as well
    api_configuration = client.CoreV1Api().api_client.configuration
    assert api_configuration.auth_settings()["BearerToken"]["value"] == (
        "bearer second-token"
    )


def namespace(name: str | None) -> client.V1Namespace:
    return client.V1Namespace(metadata=client.V1ObjectMeta(name=name))


def patch_core_api(monkeypatch, response) -> None:
    monkeypatch.setattr(
        kubernetes_namespace_resolver, "ensure_incluster_config", lambda: None
    )
    monkeypatch.setattr(
        kubernetes_namespace_resolver.client,
        "CoreV1Api",
        lambda: SimpleNamespace(list_namespace=lambda: response),
    )


def test_namespace_resolver_returns_the_names(monkeypatch):
    patch_core_api(
        monkeypatch,
        client.V1NamespaceList(items=[namespace("default"), namespace("kube-system")]),
    )
    assert kubernetes_namespace_resolver.kubernetes_namespaces_resolver() == [
        "default",
        "kube-system",
    ]


def test_namespace_resolver_skips_namespaces_without_a_name(monkeypatch):
    patch_core_api(
        monkeypatch,
        client.V1NamespaceList(
            items=[namespace("default"), client.V1Namespace(), namespace(None)]
        ),
    )
    assert kubernetes_namespace_resolver.kubernetes_namespaces_resolver() == ["default"]


@pytest.mark.parametrize("response", [None, {}, client.V1NamespaceList(items=[])])
def test_namespace_resolver_warns_about_an_unusable_response(
    monkeypatch, caplog, response
):
    patch_core_api(monkeypatch, response)
    with caplog.at_level(logging.WARNING, logger="kubeseal-webgui"):
        assert kubernetes_namespace_resolver.kubernetes_namespaces_resolver() == []
    assert "No valid namespace list available" in caplog.text


def patch_custom_objects_api(monkeypatch, response) -> list[dict]:
    requests: list[dict] = []

    def list_namespaced_custom_object(**kwargs: str) -> object:
        requests.append(kwargs)
        return response

    monkeypatch.setattr(
        kubernetes_sealed_secret_resolver, "ensure_incluster_config", lambda: None
    )
    monkeypatch.setattr(
        kubernetes_sealed_secret_resolver.client,
        "CustomObjectsApi",
        lambda: SimpleNamespace(
            list_namespaced_custom_object=list_namespaced_custom_object
        ),
    )
    return requests


def test_sealed_secret_resolver_returns_sorted_names_and_keys(monkeypatch, caplog):
    requests = patch_custom_objects_api(
        monkeypatch,
        {
            "items": [
                {
                    "metadata": {"name": "zeta"},
                    "spec": {"encryptedData": {"b": "AgB", "a": "AgA"}},
                },
                "not-an-object",
                {"metadata": {"name": "no-spec"}, "spec": None},
                {"metadata": {}, "spec": {"encryptedData": {}}},
                {"metadata": {"name": "alpha"}, "spec": {}},
            ]
        },
    )

    with caplog.at_level(logging.WARNING, logger="kubeseal-webgui"):
        result = kubernetes_sealed_secret_resolver.kubernetes_sealed_secret_resolver(
            "my-namespace"
        )

    assert result == [
        ExistingSealedSecret(name="alpha", keys=[]),
        ExistingSealedSecret(name="zeta", keys=["a", "b"]),
    ]
    assert requests == [
        {
            "group": "bitnami.com",
            "version": "v1alpha1",
            "namespace": "my-namespace",
            "plural": "sealedsecrets",
        }
    ]
    assert "Skipped 3 malformed SealedSecret object(s)" in caplog.text
    # sealed values are not logged
    assert "AgA" not in caplog.text


@pytest.mark.parametrize("response", [None, [], {"items": "nope"}, {"items": None}])
def test_sealed_secret_resolver_warns_about_an_unusable_response(
    monkeypatch, caplog, response
):
    patch_custom_objects_api(monkeypatch, response)
    with caplog.at_level(logging.WARNING, logger="kubeseal-webgui"):
        result = kubernetes_sealed_secret_resolver.kubernetes_sealed_secret_resolver(
            "my-namespace"
        )
    assert result == []
    assert "Unexpected SealedSecrets response payload type" in caplog.text


def test_mock_mode_is_decided_per_request(monkeypatch, original_resolvers):
    monkeypatch.setattr(settings, "mock_enabled", True)
    monkeypatch.setattr(settings, "mock_namespace_count", 5)

    namespaces = http_client.get("/namespaces")
    sealed_secrets = http_client.get("/sealed-secrets/team-a")

    assert namespaces.status_code == 200
    assert 1 <= len(namespaces.json()) <= 5
    assert sealed_secrets.status_code == 200
    assert [item["name"] for item in sealed_secrets.json()] == [
        "team-a-app-secrets",
        "team-a-db-secrets",
    ]


def test_without_mock_mode_the_cluster_is_asked(monkeypatch, original_resolvers):
    monkeypatch.setattr(settings, "mock_enabled", False)
    monkeypatch.setattr(
        kubernetes, "kubernetes_namespaces_resolver", lambda: ["from-cluster"]
    )
    monkeypatch.setattr(
        kubernetes,
        "kubernetes_sealed_secret_resolver",
        lambda namespace: [ExistingSealedSecret(name=namespace, keys=["KEY"])],
    )

    assert http_client.get("/namespaces").json() == ["from-cluster"]
    assert http_client.get("/sealed-secrets/team-a").json() == [
        {"name": "team-a", "keys": ["KEY"]}
    ]


def test_outside_a_cluster_the_request_fails_with_a_500(
    monkeypatch, original_resolvers
):
    monkeypatch.setattr(settings, "mock_enabled", False)
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)

    response = http_client.get("/namespaces")

    assert response.status_code == 500
    assert response.json() == {"detail": "Can't get namespaces from cluster."}
