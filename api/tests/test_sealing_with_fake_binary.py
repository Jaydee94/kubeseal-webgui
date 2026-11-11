"""Run the sealing pipeline against a stand-in for the kubeseal binary."""

import logging
from base64 import b64encode
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kubeseal_webgui_api.app import app
from kubeseal_webgui_api.app_config import settings
from kubeseal_webgui_api.routers.models import Secret

client = TestClient(app)

TEXT_VALUE = "pässwörd with\ttabs,\r\nline breaks\nand a trailing newline\n"
# Not valid UTF-8, with NUL bytes and both kinds of line endings.
BINARY_FILE = bytes(range(256)) + b"\r\n\x00\xff\n"
# Behaviour of a fake binary that "seals" by printing its stdin as base64.
ECHO_STDIN_AS_BASE64 = 'base64 < "$(dirname "$0")/stdin.bin"'


def b64(data: bytes) -> str:
    return b64encode(data).decode("ascii")


@pytest.fixture
def fake_kubeseal(tmp_path: Path, monkeypatch):
    """Install a fake binary; returns a function that writes its script.

    The script stores stdin and the arguments of its last call next to itself,
    so that tests can compare them byte by byte.
    """

    def install(behaviour: str) -> Path:
        binary = tmp_path / "fake-kubeseal"
        binary.write_text(
            "#!/bin/sh\n"
            f'cat > "{tmp_path}/stdin.bin"\n'
            f'for argument in "$@"; do echo "$argument"; done > "{tmp_path}/args"\n'
            f"{behaviour}\n"
        )
        binary.chmod(0o755)
        monkeypatch.setattr(settings, "mock_enabled", False)
        monkeypatch.setattr(settings, "kubeseal_binary", str(binary))
        monkeypatch.setattr(settings, "kubeseal_cert", "/certs/cert.pem")
        return tmp_path

    return install


def post_secret(entry: dict, **overrides: str):
    return client.post(
        "/secrets",
        json={
            "secret": "my-secret",
            "namespace": "my-namespace",
            "scope": "strict",
            "secrets": [entry],
            **overrides,
        },
    )


def test_value_reaches_stdin_byte_exact(fake_kubeseal):
    work_dir = fake_kubeseal(ECHO_STDIN_AS_BASE64)
    payload = TEXT_VALUE.encode("utf-8")

    response = post_secret({"key": "password", "value": b64(payload)})

    assert response.status_code == 200
    # line breaks in the output of the binary are removed
    assert response.json() == [{"key": "password", "value": b64(payload)}]
    assert (work_dir / "stdin.bin").read_bytes() == payload


def test_file_reaches_stdin_byte_exact(fake_kubeseal):
    work_dir = fake_kubeseal(ECHO_STDIN_AS_BASE64)

    response = post_secret({"key": "keystore", "file": b64(BINARY_FILE)})

    assert response.status_code == 200
    assert response.json() == [{"key": "keystore", "value": b64(BINARY_FILE)}]
    assert (work_dir / "stdin.bin").read_bytes() == BINARY_FILE


def test_kubeseal_is_called_with_cert_scope_namespace_and_name(fake_kubeseal):
    work_dir = fake_kubeseal("echo AgSealed")

    response = post_secret({"key": "password", "value": b64(b"x")})

    assert response.status_code == 200
    assert response.json() == [{"key": "password", "value": "AgSealed"}]
    assert (work_dir / "args").read_text().splitlines() == [
        "--raw",
        "--from-file=/dev/stdin",
        "--cert",
        "/certs/cert.pem",
        "--scope",
        "strict",
        "--namespace",
        "my-namespace",
        "--name",
        "my-secret",
    ]


@pytest.mark.parametrize(
    ("scope", "expected_arguments"),
    [
        ("namespace-wide", ["--scope", "namespace-wide", "--namespace", "ns"]),
        ("cluster-wide", ["--scope", "cluster-wide"]),
    ],
)
def test_wider_scopes_omit_name_and_namespace(fake_kubeseal, scope, expected_arguments):
    work_dir = fake_kubeseal("echo AgSealed")

    response = post_secret(
        {"key": "password", "value": b64(b"x")}, scope=scope, namespace="ns"
    )

    assert response.status_code == 200
    arguments = (work_dir / "args").read_text().splitlines()
    assert arguments[4:] == expected_arguments


def test_every_entry_is_sealed_in_order(fake_kubeseal):
    fake_kubeseal(ECHO_STDIN_AS_BASE64)

    response = client.post(
        "/secrets",
        json={
            "secret": "my-secret",
            "namespace": "my-namespace",
            "secrets": [
                {"key": "first", "value": b64(b"one")},
                {"key": "second", "file": b64(b"\x00two")},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == [
        {"key": "first", "value": b64(b"one")},
        {"key": "second", "value": b64(b"\x00two")},
    ]


@pytest.mark.parametrize(
    ("behaviour", "logged_reason"),
    [
        ("exit 3", "(exit code 3): no error output"),
        ('echo "cannot seal" >&2; exit 1', "(exit code 1): cannot seal"),
        # kubeseal warnings on stderr have always been treated as failures
        ('echo "warning" >&2; echo AgSealed', "(exit code 0): warning"),
    ],
)
def test_failing_binary_becomes_a_500(fake_kubeseal, caplog, behaviour, logged_reason):
    fake_kubeseal(behaviour)
    cleartext = b64(b"super-secret-value")

    with caplog.at_level(logging.ERROR, logger="kubeseal-webgui"):
        response = post_secret({"key": "password", "value": cleartext})

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Failed to seal secrets. See the API logs for details."
    }
    assert f"Error in run_kubeseal {logged_reason}" in caplog.text
    assert "super-secret-value" not in caplog.text
    assert cleartext not in caplog.text


def test_missing_binary_becomes_a_500(monkeypatch, caplog):
    monkeypatch.setattr(settings, "mock_enabled", False)
    monkeypatch.setattr(settings, "kubeseal_binary", "/bin/no-such-thing-here")

    with caplog.at_level(logging.ERROR, logger="kubeseal-webgui"):
        response = post_secret({"key": "password", "value": b64(b"x")})

    assert response.status_code == 500
    assert "Could not find kubeseal binary" in caplog.text


def test_value_that_is_not_utf8_is_rejected_but_a_file_is_not(fake_kubeseal):
    fake_kubeseal("echo AgSealed")
    not_utf8 = b64(b"\xff\xfe")

    assert post_secret({"key": "k", "value": not_utf8}).status_code == 400
    assert post_secret({"key": "k", "file": not_utf8}).status_code == 200


def test_invalid_names_are_rejected_before_the_binary_runs(fake_kubeseal):
    work_dir = fake_kubeseal("echo AgSealed")

    response = post_secret({"key": "k", "value": b64(b"x")}, namespace="Not_Valid")

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid data for sealing secrets: Invalid k8s name: Not_Valid"
    }
    assert not (work_dir / "args").exists()


@pytest.mark.parametrize(
    "entry",
    [
        {"key": "k"},
        {"key": "k", "value": None, "file": None},
        {"key": "k", "value": "eA==", "file": "eA=="},
        # used to be accepted and sealed the empty value, ignoring the file
        {"key": "k", "value": "", "file": "eA=="},
        {"key": "k", "value": "eA==", "file": ""},
    ],
)
def test_entry_needs_exactly_one_of_value_and_file(entry):
    response = post_secret(entry)
    assert response.status_code == 422
    (error,) = response.json()["detail"]
    assert error["type"] == "value_error"
    assert error["loc"] == ["body", "secrets", 0]
    assert "'value' or 'file'" in error["msg"]


@pytest.mark.parametrize(
    "entry",
    [{"key": "k", "value": ""}, {"key": "k", "file": ""}],
)
def test_empty_value_or_file_alone_is_accepted(entry):
    assert Secret(**entry).key == "k"
