from fastapi.testclient import TestClient

from kubeseal_webgui_api.app import app
from kubeseal_webgui_api.app_config import settings

settings.mock_enabled = True
client = TestClient(app)


def test_get_namespaces():
    response = client.get("/namespaces")
    assert response.status_code == 200

    payload = response.json()
    assert payload is not None
    assert len(payload) > 0
