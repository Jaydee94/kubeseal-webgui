import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kubeseal_webgui_api import app_config
from kubeseal_webgui_api.app import app
from kubeseal_webgui_api.app_config import AppSettings

SETTINGS_ENV_NAMES = [
    "KUBESEAL_BINARY",
    "KUBESEAL_CERT",
    "KUBESEAL_AUTOFETCH",
    "KUBESEAL_CONTROLLER_NAMESPACE",
    "KUBESEAL_CONTROLLER_NAME",
    "MOCK_ENABLED",
    "MOCK_NAMESPACE_COUNT",
]


@pytest.fixture
def clean_env(monkeypatch):
    for name in SETTINGS_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture(autouse=True)
def _fresh_version_cache():
    app_config._detect_kubeseal_version.cache_clear()
    yield
    app_config._detect_kubeseal_version.cache_clear()


def write_fake_kubeseal(directory: Path, script_body: str) -> Path:
    """Create an executable that records each call and runs `script_body`."""
    binary = directory / "fake-kubeseal"
    calls = directory / "calls.log"
    binary.write_text(f'#!/bin/sh\necho "$@" >> "{calls}"\n{script_body}\n')
    binary.chmod(0o755)
    return binary


def recorded_calls(directory: Path) -> list[str]:
    calls = directory / "calls.log"
    return calls.read_text().splitlines() if calls.exists() else []


def test_settings_defaults(clean_env):
    settings = AppSettings()
    assert settings.kubeseal_binary == "/bin/false"
    assert settings.kubeseal_cert == "/kubeseal-webgui/cert/kubeseal-cert.pem"
    assert settings.kubeseal_autofetch is False
    assert settings.kubeseal_controller_namespace == "sealed-secrets"
    assert settings.kubeseal_controller_name == "sealed-secrets-controller"
    assert settings.mock_enabled is False
    assert settings.mock_namespace_count == 120


def test_settings_are_read_from_the_documented_env_names(clean_env):
    clean_env.setenv("KUBESEAL_BINARY", "/opt/kubeseal")
    clean_env.setenv("KUBESEAL_CERT", "/certs/cert.pem")
    clean_env.setenv("KUBESEAL_AUTOFETCH", "true")
    clean_env.setenv("KUBESEAL_CONTROLLER_NAMESPACE", "kube-system")
    clean_env.setenv("KUBESEAL_CONTROLLER_NAME", "seal")
    clean_env.setenv("MOCK_ENABLED", "true")

    settings = AppSettings()

    assert settings.kubeseal_binary == "/opt/kubeseal"
    assert settings.kubeseal_cert == "/certs/cert.pem"
    assert settings.kubeseal_autofetch is True
    assert settings.kubeseal_controller_namespace == "kube-system"
    assert settings.kubeseal_controller_name == "seal"
    assert settings.mock_enabled is True


@pytest.mark.parametrize(
    ("name", "raw", "expected"),
    [
        (name, raw, expected)
        for name in ("KUBESEAL_AUTOFETCH", "MOCK_ENABLED")
        for raw, expected in [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("off", False),
        ]
    ],
)
def test_boolean_settings_accept_the_usual_spellings(clean_env, name, raw, expected):
    clean_env.setenv(name, raw)
    assert getattr(AppSettings(), name.lower()) is expected


def test_unparseable_boolean_setting_is_rejected(clean_env):
    clean_env.setenv("KUBESEAL_AUTOFETCH", "maybe")
    with pytest.raises(ValueError, match="kubeseal_autofetch"):
        AppSettings()


@pytest.mark.parametrize(
    "extra_env",
    [
        {},
        {"MOCK_ENABLED": "true"},
        {"KUBESEAL_BINARY": "/bin/no-such-thing-here"},
    ],
)
def test_importing_the_app_does_not_run_the_binary(extra_env):
    env = {k: v for k, v in os.environ.items() if k not in SETTINGS_ENV_NAMES}
    completed = subprocess.run(
        [sys.executable, "-c", "import kubeseal_webgui_api.app"],
        env={**env, **extra_env},
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_startup_fails_when_the_binary_is_unusable(monkeypatch):
    monkeypatch.setattr(app_config.settings, "mock_enabled", False)
    monkeypatch.setattr(app_config.settings, "kubeseal_binary", "/bin/false")
    with (
        pytest.raises(
            RuntimeError,
            match=r"Failed to determine the kubeseal version \(exit code 1\)",
        ),
        TestClient(app),
    ):
        pytest.fail("the application must not start")


def test_startup_fails_when_the_binary_is_missing(monkeypatch):
    monkeypatch.setattr(app_config.settings, "mock_enabled", False)
    monkeypatch.setattr(
        app_config.settings, "kubeseal_binary", "/bin/no-such-thing-here"
    )
    with (
        pytest.raises(RuntimeError, match="cannot execute '/bin/no-such-thing-here'"),
        TestClient(app),
    ):
        pytest.fail("the application must not start")


def test_startup_fails_when_the_binary_is_not_kubeseal(monkeypatch, tmp_path):
    binary = write_fake_kubeseal(tmp_path, "echo hello")
    monkeypatch.setattr(app_config.settings, "mock_enabled", False)
    monkeypatch.setattr(app_config.settings, "kubeseal_binary", str(binary))
    with (
        pytest.raises(RuntimeError, match="Check that KUBESEAL_BINARY points to"),
        TestClient(app),
    ):
        pytest.fail("the application must not start")


def test_mock_mode_starts_without_a_binary(monkeypatch):
    monkeypatch.setattr(app_config.settings, "mock_enabled", True)
    monkeypatch.setattr(
        app_config.settings, "kubeseal_binary", "/bin/no-such-thing-here"
    )
    with TestClient(app) as client:
        response = client.get("/config")
    assert response.status_code == 200
    assert response.json() == {"kubesealVersion": "0.1.0"}


def test_version_is_resolved_once_at_startup(monkeypatch, tmp_path):
    binary = write_fake_kubeseal(tmp_path, 'echo "kubeseal version: 0.27.1"')
    monkeypatch.setattr(app_config.settings, "mock_enabled", False)
    monkeypatch.setattr(app_config.settings, "kubeseal_autofetch", False)
    monkeypatch.setattr(app_config.settings, "kubeseal_binary", str(binary))

    with TestClient(app) as client:
        assert recorded_calls(tmp_path) == ["--version"]
        for _ in range(2):
            response = client.get("/config")
            assert response.status_code == 200
            assert response.json() == {"kubesealVersion": "0.27.1"}

    assert recorded_calls(tmp_path) == ["--version"]


def test_autofetch_saves_the_certificate_at_startup(monkeypatch, tmp_path):
    binary = write_fake_kubeseal(
        tmp_path,
        'case "$1" in\n'
        '  --version) echo "kubeseal version: 0.27.1" ;;\n'
        '  --fetch-cert) echo "FAKE CERTIFICATE" ;;\n'
        "esac",
    )
    cert = tmp_path / "cert.pem"
    monkeypatch.setattr(app_config.settings, "mock_enabled", False)
    monkeypatch.setattr(app_config.settings, "kubeseal_autofetch", True)
    monkeypatch.setattr(app_config.settings, "kubeseal_binary", str(binary))
    monkeypatch.setattr(app_config.settings, "kubeseal_cert", str(cert))
    monkeypatch.setattr(app_config.settings, "kubeseal_controller_name", "seal")
    monkeypatch.setattr(app_config.settings, "kubeseal_controller_namespace", "ns")

    with TestClient(app):
        pass

    assert cert.read_text() == "FAKE CERTIFICATE\n"
    assert recorded_calls(tmp_path) == [
        "--version",
        "--fetch-cert --controller-name seal --controller-namespace ns",
    ]


def test_certificate_is_not_fetched_unless_enabled(monkeypatch, tmp_path):
    binary = write_fake_kubeseal(tmp_path, 'echo "kubeseal version: 0.27.1"')
    cert = tmp_path / "cert.pem"
    monkeypatch.setattr(app_config.settings, "mock_enabled", False)
    monkeypatch.setattr(app_config.settings, "kubeseal_autofetch", False)
    monkeypatch.setattr(app_config.settings, "kubeseal_binary", str(binary))
    monkeypatch.setattr(app_config.settings, "kubeseal_cert", str(cert))

    with TestClient(app):
        pass

    assert not cert.exists()
