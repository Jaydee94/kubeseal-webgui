"""Several clusters, each sealed with its own certificate."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kubeseal_webgui_api.app import app, check_clusters
from kubeseal_webgui_api.app_config import settings
from kubeseal_webgui_api.clusters import (
    ClusterConfigError,
    cert_fingerprint,
    get_cluster,
    parse_clusters,
)
from kubeseal_webgui_api.routers.kubeseal import build_kubeseal_command, seal_secrets
from kubeseal_webgui_api.routers.models import Scope, Secret

client = TestClient(app)

# A syntactically valid, throw-away certificate.
PEM = """-----BEGIN CERTIFICATE-----
MIIBtjCCAVugAwIBAgITBmyf1XSXNmY/Owua2eiedgPySjAKBggqhkjOPQQDAjA5
MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6b24g
Um9vdCBDQSAzMB4XDTE1MDUyNjAwMDAwMFoXDTQwMDUyNjAwMDAwMFowOTELMAkG
A1UEBhMCVVMxDzANBgNVBAoTBkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJvb3Qg
Q0EgMzBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABCmXp8ZBf8ANm+gBG1bG8lKl
ui2yEujSLtf6ycXYqm0fc4E7O5hrOXwzpcVOho6AF2hiRVd9RFgdszflZwjrZt6j
QjBAMA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgGGMB0GA1UdDgQWBBSr
ttvXBp43rDCGB5Fwx5zEGbF4wDAKBggqhkjOPQQDAgNJADBGAiEA4IWSoxe3jfkr
BqWTrBqYaGFy+uGh0PsceGCmQ5nFuMQCIQCcAu/xlJyzlvnrxir4tiz+OpAUFteM
YyRIHN8wfdVoOw==
-----END CERTIFICATE-----
"""


@pytest.fixture
def clusters_file(tmp_path: Path, monkeypatch):
    """Configure clusters from a document; returns the writer."""

    def configure(document: object) -> Path:
        path = tmp_path / "clusters.json"
        path.write_text(json.dumps(document))
        monkeypatch.setattr(settings, "kubeseal_clusters_file", str(path))
        return path

    return configure


TWO_CLUSTERS = [
    {"name": "acc", "inCluster": True},
    {"name": "prod", "cert": "/clusters/prod.pem"},
]


def test_without_a_clusters_file_there_is_one_default_cluster(monkeypatch):
    monkeypatch.setattr(settings, "kubeseal_clusters_file", "")
    monkeypatch.setattr(settings, "kubeseal_cert", "/cert/own.pem")

    cluster = get_cluster(None)

    assert (cluster.name, cluster.cert, cluster.in_cluster) == (
        "default",
        "/cert/own.pem",
        True,
    )


def test_an_in_cluster_entry_without_cert_uses_the_controller_certificate(
    clusters_file, monkeypatch
):
    clusters_file(TWO_CLUSTERS)
    monkeypatch.setattr(settings, "kubeseal_cert", "/cert/own.pem")

    assert get_cluster("acc").cert == "/cert/own.pem"
    assert get_cluster("prod").cert == "/clusters/prod.pem"


def test_the_first_cluster_is_the_default(clusters_file):
    clusters_file(TWO_CLUSTERS)

    assert get_cluster(None).name == "acc"
    assert get_cluster("").name == "acc"


def test_an_unknown_cluster_is_an_error_naming_the_known_ones(clusters_file):
    clusters_file(TWO_CLUSTERS)

    with pytest.raises(ValueError, match="Unknown cluster 'dev'.*acc, prod"):
        get_cluster("dev")


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ([], "non-empty"),
        ({"name": "a"}, "non-empty"),
        (["a"], "not an object"),
        ([{"cert": "/c.pem"}], "needs a 'name'"),
        ([{"name": "Prod", "cert": "/c.pem"}], "needs a 'name'"),
        ([{"name": "../x", "cert": "/c.pem"}], "needs a 'name'"),
        ([{"name": "a"}], "needs a 'cert'"),
        ([{"name": "a", "cert": "/c.pem", "inCluster": "yes"}], "true or false"),
        (
            [{"name": "a", "cert": "/a.pem"}, {"name": "a", "cert": "/b.pem"}],
            "duplicate cluster names: a",
        ),
        (
            [
                {"name": "a", "cert": "/a.pem", "inCluster": True},
                {"name": "b", "cert": "/b.pem", "inCluster": True},
            ],
            "at most one",
        ),
    ],
)
def test_invalid_cluster_documents_are_rejected(document, message):
    with pytest.raises(ClusterConfigError, match=message):
        parse_clusters(document)


def test_a_broken_clusters_file_stops_the_start(clusters_file, monkeypatch):
    path = clusters_file(TWO_CLUSTERS)
    path.write_text("not json")

    with pytest.raises(ClusterConfigError, match="cannot read"):
        check_clusters()


def test_a_missing_certificate_stops_the_start(clusters_file, monkeypatch):
    clusters_file([{"name": "prod", "cert": "/does/not/exist.pem"}])
    monkeypatch.setattr(settings, "mock_enabled", False)

    with pytest.raises(ClusterConfigError, match="'prod' does not exist"):
        check_clusters()


def test_the_command_uses_the_certificate_of_the_cluster(clusters_file):
    clusters_file(TWO_CLUSTERS)

    command = build_kubeseal_command(
        "ns", "name", Scope.STRICT, get_cluster("prod").cert
    )

    assert command[command.index("--cert") + 1] == "/clusters/prod.pem"


def test_seal_secrets_rejects_an_unknown_cluster(clusters_file):
    clusters_file(TWO_CLUSTERS)

    with pytest.raises(ValueError, match="Unknown cluster"):
        seal_secrets([Secret(key="k", value="YQ==")], "ns", "name", cluster="dev")


def test_the_clusters_endpoint_lists_the_clusters(clusters_file, tmp_path):
    prod_cert = tmp_path / "prod.pem"
    prod_cert.write_text(PEM)
    clusters_file(
        [
            {"name": "acc", "inCluster": True},
            {"name": "prod", "cert": str(prod_cert)},
        ]
    )

    response = client.get("/clusters")

    assert response.status_code == 200
    acc, prod = response.json()
    assert acc["name"] == "acc"
    assert acc["inCluster"] is True
    assert prod["name"] == "prod"
    assert prod["inCluster"] is False
    assert prod["fingerprint"] == cert_fingerprint(str(prod_cert))
    assert len(prod["fingerprint"].split(":")) == 32


def test_the_clusters_endpoint_without_configuration(monkeypatch):
    monkeypatch.setattr(settings, "kubeseal_clusters_file", "")

    response = client.get("/clusters")

    assert response.json() == [
        {"name": "default", "inCluster": True, "fingerprint": None}
    ]


def test_the_fingerprint_of_an_unreadable_certificate_is_none(tmp_path):
    broken = tmp_path / "broken.pem"
    broken.write_text("nope")

    assert cert_fingerprint(str(broken)) is None
    assert cert_fingerprint(str(tmp_path / "missing.pem")) is None


def test_the_sealing_endpoint_answers_an_unknown_cluster_with_400(
    clusters_file, monkeypatch
):
    clusters_file(TWO_CLUSTERS)
    monkeypatch.setattr(settings, "mock_enabled", True)

    response = client.post(
        "/secrets",
        json={
            "secret": "s",
            "namespace": "ns",
            "cluster": "dev",
            "scope": "strict",
            "secrets": [{"key": "k", "value": "YQ=="}],
        },
    )

    assert response.status_code == 400
    assert "Unknown cluster" in response.json()["detail"]


def test_the_sealing_endpoint_uses_the_cluster_certificate(
    clusters_file, monkeypatch, tmp_path
):
    binary = tmp_path / "fake-kubeseal"
    binary.write_text(
        f'#!/bin/sh\ncat >/dev/null\necho "$@" > "{tmp_path}/args"\necho sealed\n'
    )
    binary.chmod(0o755)
    clusters_file(TWO_CLUSTERS)
    monkeypatch.setattr(settings, "mock_enabled", False)
    monkeypatch.setattr(settings, "kubeseal_binary", str(binary))

    response = client.post(
        "/secrets",
        json={
            "secret": "s",
            "namespace": "ns",
            "cluster": "prod",
            "scope": "strict",
            "secrets": [{"key": "k", "value": "YQ=="}],
        },
    )

    assert response.status_code == 200
    assert "--cert /clusters/prod.pem" in (tmp_path / "args").read_text()
