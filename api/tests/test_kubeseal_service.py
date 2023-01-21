import logging
from os import environ

import pytest
from fastapi.testclient import TestClient

from kubeseal_webgui_api.app import app

LOGGER = logging.getLogger(__name__)
environ["ORIGIN_URL"] = "http://no-server-here"

client = TestClient(app)


@pytest.mark.container()
@pytest.mark.cluster()
def test_post_secrets_object():
    sealing_request_data = {
        "namespace": "default",
        "secret": "bar",
        "scope": "strict",
        "secrets": [{"key": "my", "value": "cHJlY2lvdXMK"}],
    }
    res = client.post("/secrets", json=sealing_request_data)
    assert res.status_code == 200
    sealed = res.json()
    for index, secret in enumerate(sealing_request_data["secrets"]):
        assert secret["key"] == sealed[index]["key"]
        assert len(sealed[index]["value"]) > 0


@pytest.mark.container()
@pytest.mark.cluster()
def test_get_api():
    # given running http server
    # when GET /secrets
    res = client.get("/secrets")
    # then return non empty result
    assert res.status_code == 405
    assert res.json() != ""


@pytest.mark.container()
@pytest.mark.cluster()
def test_post_api():
    # given running http server
    # when POST /secrets
    data = {
        "secret": "default",
        "namespace": "test-namespace",
        "scope": "strict",
        "secrets": [
            {"key": "foo", "value": "YmFyCg=="},
            {"key": "bar", "value": "Zm9vCg=="},
        ],
    }

    res = client.post("/secrets", json=data)

    # then return non empty result
    assert res.status_code == 200
    assert res.json() != ""
