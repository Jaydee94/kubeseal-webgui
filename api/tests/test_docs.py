from fastapi.testclient import TestClient

from kubeseal_webgui_api.app import app

client = TestClient(app)


def test_docs_page_loads_the_schema_by_a_relative_url():
    # Relative, so that the page also works under a path prefix of the UI's
    # nginx, e.g. https://example.com/kubeseal-webgui/docs.
    response = client.get("/docs")
    assert response.status_code == 200
    assert "url: 'openapi.json'" in response.text
    assert "'/openapi.json'" not in response.text


def test_docs_page_is_not_part_of_the_schema():
    assert "/docs" not in client.get("/openapi.json").json()["paths"]
