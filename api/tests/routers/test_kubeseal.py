import pytest
from fastapi.testclient import TestClient

from kubeseal_webgui_api.app import app
from kubeseal_webgui_api.app_config import settings

settings.mock_enabled = True
client = TestClient(app)


@pytest.mark.parametrize(
    "body",
    [
        {
            "scope": "strict",
            "secret": "test-case-01",
            "namespace": "spec-01",
            "secrets": [],
        },
        {"secrets": [{"key": "I", "value": "SQ=="}, {"key": "II", "value": "SUk="}]},
    ],
)
def test_encrypt_data(body):
    response = client.post("/secrets", json=body)
    assert response.status_code == 200

    payload = response.json()
    assert payload is not None

    secrets = body["secrets"]
    assert len(payload) == len(secrets)

    for idx, pair in enumerate(payload):
        assert pair is not None
        assert "key" in pair.keys()
        assert "value" in pair.keys()
        assert secrets[idx] is not None
        assert pair["key"] == secrets[idx]["key"]
        assert pair["value"] != ""
