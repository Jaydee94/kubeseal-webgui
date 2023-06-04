import subprocess
from typing import List
from unittest.mock import Mock, patch

import pytest

from kubeseal_webgui_api.internal.kubeseal_client import (
    KubesealClient,
    MockKubesealClient,
)


@patch("subprocess.Popen")
def test_kubeseal_client_get_version(mock_subproc_popen):
    process_mock = Mock()
    process_mock.communicate = Mock(return_value=("kubeseal: 1.22.333", ""))
    mock_subproc_popen.return_value = process_mock

    subject = KubesealClient()
    result = subject.get_version()

    assert result == "1.22.333"

    assert len(mock_subproc_popen.mock_calls) > 0
    mock_subproc_popen.assert_called_with(
        ["/bin/kubeseal", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )


@patch("subprocess.Popen")
def test_kubeseal_client_get_certificate(mock_subproc_popen):
    process_mock = Mock()
    process_mock.communicate = Mock(return_value=("-BEGIN-\nDATA\n-END-", ""))
    mock_subproc_popen.return_value = process_mock

    subject = KubesealClient()
    result = subject.get_certificate()

    assert result == "-BEGIN-\nDATA\n-END-"

    assert len(mock_subproc_popen.mock_calls) > 0
    mock_subproc_popen.assert_called_with(
        [
            "/bin/kubeseal",
            "--fetch-cert",
            "--controller-name",
            "sealed-secrets-controller",
            "--controller-namespace",
            "sealed-secrets",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )


@patch("subprocess.Popen")
@pytest.mark.parametrize(
    ("argv", "expected_argv"),
    [
        (["test", "minimal"], ["--scope", "minimal"]),
        (
            ["test", "with-name", "the-name"],
            ["--scope", "with-name", "--name", "the-name"],
        ),
        (
            ["test", "with-namespace", None, "the-namespace"],
            ["--scope", "with-namespace", "--namespace", "the-namespace"],
        ),
        (
            ["test", "with-both", "the-name", "the-namespace"],
            [
                "--scope",
                "with-both",
                "--namespace",
                "the-namespace",
                "--name",
                "the-name",
            ],
        ),
    ],
)
def test_kubeseal_client_seal_string(mock_subproc_popen, argv, expected_argv):
    process_mock = Mock()
    process_mock.communicate = Mock(return_value=("SEALED_DATA\nSEALED_DATA\n", ""))
    mock_subproc_popen.return_value = process_mock

    subject = KubesealClient()
    result = subject.seal_string(*argv)

    assert result == "SEALED_DATASEALED_DATA"

    assert len(mock_subproc_popen.mock_calls) > 0

    assert_argv = [
        "/bin/kubeseal",
        "--raw",
        "--from-file=/dev/stdin",
        "--cert",
        "/dev/null",
    ] + expected_argv
    mock_subproc_popen.assert_called_with(
        assert_argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )


@patch("subprocess.Popen")
@pytest.mark.parametrize(
    ("argv", "expected_argv"),
    [
        (["test", "minimal"], ["--scope", "minimal"]),
        (
            ["test", "with-name", "the-name"],
            ["--scope", "with-name", "--name", "the-name"],
        ),
        (
            ["test", "with-namespace", None, "the-namespace"],
            ["--scope", "with-namespace", "--namespace", "the-namespace"],
        ),
        (
            ["test", "with-both", "the-name", "the-namespace"],
            [
                "--scope",
                "with-both",
                "--namespace",
                "the-namespace",
                "--name",
                "the-name",
            ],
        ),
    ],
)
def test_kubeseal_client_seal_bytes(mock_subproc_popen, argv, expected_argv):
    process_mock = Mock()
    process_mock.communicate = Mock(
        return_value=("SEALED_BYTES\nSEALED_BYTES\n".encode("utf-8"), b"")
    )
    mock_subproc_popen.return_value = process_mock

    subject = KubesealClient()
    result = subject.seal_bytes(*argv)

    assert result == "SEALED_BYTESSEALED_BYTES"

    assert len(mock_subproc_popen.mock_calls) > 0

    assert_argv = [
        "/bin/kubeseal",
        "--raw",
        "--from-file=/dev/stdin",
        "--cert",
        "/dev/null",
    ] + expected_argv
    mock_subproc_popen.assert_called_with(
        assert_argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding=None,
    )


def test_kubeseal_client_run_not_found():
    subject = KubesealClient(binary="/mnt/bin/kubeseal.mock")
    with pytest.raises(RuntimeError, match="Could not find kubeseal binary"):
        subject.run("--help", encoding="utf-8")


@patch("subprocess.Popen")
def test_kubeseal_client_run_error(mock_subproc_popen):
    process_mock = Mock()
    process_mock.communicate = Mock(return_value=("", "mock error"))
    mock_subproc_popen.return_value = process_mock

    subject = KubesealClient()
    with pytest.raises(
        RuntimeError, match="Error while executing /bin/kubeseal: mock error"
    ):
        subject.run("--help", encoding="utf-8")
