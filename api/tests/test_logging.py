import json
import logging
import logging.config
import sys
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from kubeseal_webgui_api.app import app
from kubeseal_webgui_api.logging_utils import (
    NO_REQUEST_ID,
    HealthCheckAccessFilter,
    JsonFormatter,
    RequestIdFilter,
    request_id_var,
)
from kubeseal_webgui_api.routers import kubernetes

client = TestClient(app)
CLEARTEXT_BASE64 = "c3VwZXItc2VjcmV0LXZhbHVl"  # "super-secret-value"


def access_record(method: str, path: str, status: int) -> logging.LogRecord:
    return logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("10.0.0.1:1234", method, path, "1.1", status),
        None,
    )


def test_response_carries_generated_request_id():
    response = client.get("/")
    assert len(response.headers["X-Request-ID"]) == 32


def test_incoming_request_id_is_reused():
    response = client.get("/", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"


@pytest.mark.parametrize("request_id", ["with space", "a" * 65, "evil\tid", "x=y"])
def test_unsafe_incoming_request_id_is_replaced(request_id):
    response = client.get("/", headers={"X-Request-ID": request_id})
    assert response.headers["X-Request-ID"] != request_id
    assert len(response.headers["X-Request-ID"]) == 32


def test_request_id_filter_adds_current_id():
    record = access_record("GET", "/namespaces", 200)
    token = request_id_var.set("req-1")
    try:
        assert RequestIdFilter().filter(record) is True
    finally:
        request_id_var.reset(token)
    assert record.request_id == "req-1"


@pytest.mark.parametrize(
    ("method", "path", "status", "kept"),
    [
        ("GET", "/", 200, False),
        ("GET", "/", 500, True),
        ("GET", "/namespaces", 200, True),
        ("POST", "/", 200, True),
    ],
)
def test_health_check_filter(method, path, status, kept):
    record = access_record(method, path, status)
    assert HealthCheckAccessFilter().filter(record) is kept


def test_health_check_filter_keeps_foreign_records():
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "plain", None, None)
    assert HealthCheckAccessFilter().filter(record) is True


def test_json_formatter_access_record():
    record = access_record("GET", "/namespaces", 200)
    record.request_id = "req-1"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == '10.0.0.1:1234 - "GET /namespaces HTTP/1.1" 200'
    assert payload["level"] == "INFO"
    assert payload["logger"] == "uvicorn.access"
    assert payload["request_id"] == "req-1"
    assert payload["method"] == "GET"
    assert payload["path"] == "/namespaces"
    assert payload["status"] == 200
    assert payload["time"].endswith("+00:00")


def test_json_formatter_includes_exception():
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        record = logging.getLogger("kubeseal-webgui").makeRecord(
            "kubeseal-webgui",
            logging.ERROR,
            __file__,
            1,
            "failed",
            (),
            sys.exc_info(),
        )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["request_id"] == NO_REQUEST_ID
    assert "RuntimeError: boom" in payload["exception"]


def test_logging_config_is_loadable():
    config_file = Path(__file__).parent.parent / "config" / "logging_config.yaml"
    config = yaml.safe_load(config_file.read_text())
    saved = logging.getLogger().handlers[:], logging.getLogger().level
    try:
        logging.config.dictConfig(config)
    finally:
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        for handler in saved[0]:
            root.addHandler(handler)
        root.setLevel(saved[1])
        for name in ("kubeseal-webgui", "uvicorn.error", "uvicorn.access"):
            logger = logging.getLogger(name)
            logger.handlers.clear()
            logger.propagate = True
            logger.setLevel(logging.NOTSET)


def test_resolver_failure_is_logged_with_traceback(caplog):
    def broken_resolver() -> list[str]:
        # Not a RuntimeError, like kubernetes.client.ApiException.
        raise ValueError("403 Forbidden")

    kubernetes.namespace_resolver = broken_resolver
    with caplog.at_level(logging.ERROR, logger="kubeseal-webgui"):
        response = client.get("/namespaces")
    assert response.status_code == 500
    assert response.json() == {"detail": "Can't get namespaces from cluster."}
    (record,) = caplog.records
    assert "Failed to list namespaces" in record.getMessage()
    assert record.exc_info is not None


def test_validation_error_is_logged_without_input(caplog):
    with caplog.at_level(logging.WARNING, logger="kubeseal-webgui"):
        response = client.post(
            "/secrets",
            json={
                "secret": "name",
                "namespace": "default",
                "secrets": [
                    {"key": "k", "value": CLEARTEXT_BASE64, "file": CLEARTEXT_BASE64}
                ],
            },
        )
    assert response.status_code == 422
    assert "Rejected invalid request POST /secrets" in caplog.text
    assert CLEARTEXT_BASE64 not in caplog.text


def test_sealing_logs_metadata_but_no_secret_values(caplog, monkeypatch):
    monkeypatch.setattr(
        "kubeseal_webgui_api.routers.kubeseal.settings.mock_enabled", True
    )
    with caplog.at_level(logging.DEBUG, logger="kubeseal-webgui"):
        response = client.post(
            "/secrets",
            json={
                "secret": "my-secret",
                "namespace": "default",
                "scope": "strict",
                "secrets": [{"key": "password", "value": CLEARTEXT_BASE64}],
            },
        )
    assert response.status_code == 200
    assert "Sealed 1 key(s) ['password'] of secret 'my-secret'" in caplog.text
    assert "in namespace 'default'" in caplog.text
    assert CLEARTEXT_BASE64 not in caplog.text
    assert "super-secret-value" not in caplog.text


def test_invalid_sealing_request_is_logged_as_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="kubeseal-webgui"):
        response = client.post(
            "/secrets",
            json={
                "namespace": "default",
                "scope": "strict",
                "secrets": [{"key": "password", "value": CLEARTEXT_BASE64}],
            },
        )
    assert response.status_code == 400
    (record,) = caplog.records
    assert record.levelno == logging.WARNING
    assert "secret_name was not given" in record.getMessage()


def test_undecodable_secret_value_is_not_quoted_in_log(caplog, monkeypatch):
    monkeypatch.setattr(
        "kubeseal_webgui_api.routers.kubeseal.settings.mock_enabled", False
    )
    with caplog.at_level(logging.WARNING, logger="kubeseal-webgui"):
        response = client.post(
            "/secrets",
            json={
                "secret": "my-secret",
                "namespace": "default",
                # base64 of the single byte 0xff, which is not valid UTF-8
                "secrets": [{"key": "password", "value": "/w=="}],
            },
        )
    assert response.status_code == 400
    (record,) = caplog.records
    assert "UnicodeDecodeError" in record.getMessage()
    assert "0xff" not in record.getMessage()


def test_client_supplied_names_cannot_forge_log_lines(caplog):
    with caplog.at_level(logging.WARNING, logger="kubeseal-webgui"):
        response = client.post(
            "/secrets",
            json={
                "secret": "name\nFAKE - kubeseal-webgui - ERROR - forged",
                "namespace": "default",
                "scope": "strict",
                "secrets": [{"key": "password", "value": CLEARTEXT_BASE64}],
            },
        )
    assert response.status_code == 400
    (record,) = caplog.records
    assert "\n" not in record.getMessage()


def test_secret_name_keeps_its_json_key():
    schema = client.get("/openapi.json").json()
    properties = schema["components"]["schemas"]["Data"]["properties"]
    assert "secret" in properties
    assert "name" not in properties
