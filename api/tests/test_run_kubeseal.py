from base64 import b64encode
from unittest.mock import MagicMock, patch

import pytest

from kubeseal_webgui_api.routers.kubeseal import (
    Scope,
    build_kubeseal_command,
    decode_base64_bytearray,
    decode_base64_string,
    seal_secrets,
    valid_namespace_name,
    valid_secret_name,
)
from kubeseal_webgui_api.routers.models import Secret

VALID_EVERYWHERE = [
    "abc",
    "a",
    "1",
    "l" + "o" * 60 + "ng",
    "some-1-too-check",
    "ends-on-digit-1",
    "1starts-with-it",
]

INVALID_EVERYWHERE = [
    "",
    None,
    "-something",
    "ähm",
    "_not-valid",
    "some_underscore",
    "with spaces",
    " not-trimmed ",
    "trailing-newline\n",
    "no-special-chars-like/,#+%",
    "ends-on-dash-",
    "Uppercase",
    "U",
    "uPPer",
]


@pytest.mark.parametrize("value", VALID_EVERYWHERE)
def test_valid_namespace_name(value):
    assert valid_namespace_name(value) == value


@pytest.mark.parametrize(
    "value",
    [
        *INVALID_EVERYWHERE,
        # a namespace is a DNS label: no dots, at most 63 characters
        "some.dots",
        "l" + "o" * 61 + "ng",
    ],
)
def test_invalid_namespace_name(value):
    with pytest.raises(ValueError, match="Invalid k8s namespace name"):
        valid_namespace_name(value)


@pytest.mark.parametrize(
    "value",
    [
        *VALID_EVERYWHERE,
        # a secret name is a DNS subdomain: dots, up to 253 characters
        "some.dots.in-it",
        "long-" + "a" * 248,
    ],
)
def test_valid_secret_name(value):
    assert valid_secret_name(value) == value


@pytest.mark.parametrize(
    "value",
    [
        *INVALID_EVERYWHERE,
        "too-l" + "o" * 247 + "ng",
        "double..dot",
        ".starts-with-dot",
        "ends-with-dot.",
        "label-ends-on-dash-.next",
    ],
)
def test_invalid_secret_name(value):
    with pytest.raises(ValueError, match="Invalid k8s secret name"):
        valid_secret_name(value)


def test_run_kubeseal_with_with_empty_string_namespace():
    # given an empty string secretNamespace
    # when seal_secrets is called
    # then raise ValueError
    with pytest.raises(ValueError, match="secret_namespace was not given"):
        seal_secrets([Secret(key="foo", value="YmFy")], "", "secretName")


def test_run_kubeseal_with_with_none_namespace():
    # given a None secretNamespace
    # when seal_secrets is called
    # then raise ValueError
    with pytest.raises(ValueError, match="secret_namespace was not given"):
        seal_secrets([Secret(key="foo", value="YmFy")], None, "secretName")


def test_run_kubeseal_with_with_empty_string_secret_name():
    # given an empty string secretName
    # when seal_secrets is called
    # then raise ValueError
    with pytest.raises(ValueError, match="secret_name was not given"):
        seal_secrets([Secret(key="foo", value="YmFy")], "secretNamespace", "")


def test_run_kubeseal_with_with_none_secret_name():
    # given a None secretName
    # when seal_secrets is called
    # then raise ValueError
    with pytest.raises(ValueError, match="secret_name was not given"):
        seal_secrets([Secret(key="foo", value="YmFy")], "secretNamespace", None)


def test_run_kubeseal_with_with_empty_secrets_list_but_otherwise_valid_inputs():
    # given an empty list
    # when seal_secrets is called
    sealed_secrets = seal_secrets([], "secretNamespace", "secretName")
    # then return empty list
    assert sealed_secrets == []


@patch("kubeseal_webgui_api.routers.kubeseal.seal_entry")
@pytest.mark.parametrize("scope", list(Scope))
def test_run_kubeseal_with_scope(mock_run_command: MagicMock, scope: Scope):
    encoded_value = b64encode(b"something").decode("ascii")
    secrets = [Secret(key="foo", value=encoded_value)]
    seal_secrets(
        secrets,
        "namespace",
        "name",
        scope,
    )
    mock_run_command.assert_called_with(secrets[0], "namespace", "name", scope)


@patch("kubeseal_webgui_api.routers.kubeseal.seal_entry")
@pytest.mark.parametrize("scope", list(Scope))
def test_run_kubeseal_with_scope_needed_params_only(
    mock_run_command: MagicMock, scope: Scope
):
    encoded_value = b64encode(b"something").decode("ascii")
    secrets = [
        Secret(
            key="foo",
            value=encoded_value,
        )
    ]
    if scope.needs_namespace():
        namespace = "namespace"
    else:
        namespace = None
    if scope.needs_name():
        name = "name"
    else:
        name = None
    seal_secrets(
        secrets,
        namespace,
        name,
        scope,
    )
    mock_run_command.assert_called_with(secrets[0], namespace, name, scope)


@pytest.mark.container()
@pytest.mark.cluster()
def test_run_kubeseal_with_cli():
    # given run test against cli with test cluster
    # when seal_secrets is called
    # then return valid encrypted secret
    pass


@pytest.mark.cluster()
@patch(
    "kubeseal_webgui_api.app_config.settings.kubeseal_binary", "/bin/no-such-thing-here"
)
def test_run_kubeseal_without_cli():
    # given k8s cluster but no kubeseal cli
    # when seal_secrets is called
    # then raise RuntimeError
    with pytest.raises(RuntimeError):
        seal_secrets(
            [Secret(key="foo", value="YmFy")], "secret-namespace", "secret-name"
        )


@pytest.mark.container()
def test_run_kubeseal_without_k8s_cluster():
    # given kubeseal cli but no k8s cluster
    # when seal_secrets is called
    # then raise RuntimeError
    with pytest.raises(RuntimeError) as error_cert_missing:
        seal_secrets(
            [Secret(key="foo", value="YmFy")], "secret-namespace", "secret-name"
        )
    assert "/kubeseal-webgui/cert/kubeseal-cert.pem: no such file or directory" in str(
        error_cert_missing
    )


@pytest.mark.parametrize(
    ("base64_input", "expected_output"),
    [("YWJjZGVm", "abcdef"), ("w6TDtsO8", "äöü"), ("LV8jIT8kwqc=", "-_#!?$§")],
)
def test_decode_base64_string(base64_input, expected_output):
    """
    Test decode_base64_string.

    Given a tuple with a Base64 input string and the corresponding output string.
    When calling decode_base64_string on input string.
    Then return the corresponding output string.
    """
    base64_encoded_string = decode_base64_string(base64_input)
    assert base64_encoded_string == expected_output


@pytest.mark.parametrize(
    ("base64_input", "expected_output"),
    [
        ("YWJjZGVm", b"abcdef"),
        ("w6TDtsO8", "äöü".encode()),
        ("LV8jIT8kwqc=", "-_#!?$§".encode()),
    ],
)
def test_decode_base64_bytearray(base64_input, expected_output):
    """
    Test decode_base64_bytearray.

    Given a tuple with a Base64 input string and the corresponding output bytearray.
    When calling decode_base64_bytearray on input string.
    Then return the corresponding output bytearray.
    """
    decoded = decode_base64_bytearray(base64_input)
    assert decoded == bytearray(expected_output)


def test_build_kubeseal_command_needs_no_existing_namespace(monkeypatch):
    # given a namespace that does not exist in any cluster
    monkeypatch.setattr(
        "kubeseal_webgui_api.app_config.settings.kubeseal_binary", "kubeseal"
    )
    monkeypatch.setattr(
        "kubeseal_webgui_api.app_config.settings.kubeseal_cert", "/cert.pem"
    )
    # when the kubeseal command is constructed
    # then it only uses the offline certificate and the given names
    cmd = build_kubeseal_command("not-created-yet", "my-secret", Scope.STRICT)
    assert cmd[0] == "kubeseal"
    assert cmd[cmd.index("--cert") + 1] == "/cert.pem"
    assert cmd[cmd.index("--namespace") + 1] == "not-created-yet"
    assert cmd[cmd.index("--name") + 1] == "my-secret"
    assert "--controller-name" not in cmd
    assert "--fetch-cert" not in cmd
