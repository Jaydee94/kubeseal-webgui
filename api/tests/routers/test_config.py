from fastapi.testclient import TestClient

from kubeseal_webgui_api.app import app
from kubeseal_webgui_api.app_config import settings

settings.mock_enabled = True
client = TestClient(app)


def test_get_configs():
    response = client.get("/config")
    assert response.status_code == 200

    payload = response.json()
    assert payload is not None
    assert payload["kubesealVersion"] == "0.1.0"
