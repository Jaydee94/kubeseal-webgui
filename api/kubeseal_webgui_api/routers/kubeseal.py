import base64
import logging
import re
import subprocess  # noqa: S404 the binary has to be configured by an admin
import time
from typing import List, Optional, Union, overload

from fastapi import APIRouter, HTTPException

from kubeseal_webgui_api.app_config import settings
from kubeseal_webgui_api.routers.models import Data, KeyValuePair, Scope, Secret

router = APIRouter()
LOGGER = logging.getLogger("kubeseal-webgui")


@router.post("/secrets", response_model=List[KeyValuePair])
def encrypt(data: Data) -> list[KeyValuePair]:
    scope = data.scope or Scope.STRICT
    started = time.perf_counter()
    # Only metadata is logged here. Never log `data.secrets` values: they are
    # the cleartext secrets. Name and namespace are logged with %r because they
    # are client input that may not have been validated (escapes line breaks).
    try:
        sealed_secrets = run_kubeseal(data.secrets, data.namespace, data.name, scope)
    except (KeyError, ValueError) as e:
        LOGGER.warning(
            "Rejected sealing request for secret %r in namespace %r: %s",
            data.name,
            data.namespace,
            loggable_reason(e),
        )
        raise HTTPException(400, f"Invalid data for sealing secrets: {e}") from None
    except RuntimeError:
        LOGGER.exception(
            "Failed to seal secret %r in namespace %r with scope '%s'.",
            data.name,
            data.namespace,
            scope.value,
        )
        raise HTTPException(
            500, "Failed to seal secrets. See the API logs for details."
        ) from None

    LOGGER.info(
        "Sealed %d key(s) %s of secret %r in namespace %r with scope '%s' "
        "in %.0f ms.",
        len(sealed_secrets),
        [sealed_secret.key for sealed_secret in sealed_secrets],
        data.name,
        data.namespace,
        scope.value,
        (time.perf_counter() - started) * 1000,
    )
    return sealed_secrets


def loggable_reason(error: Exception) -> str:
    """Describe a rejected request without quoting any part of a secret value."""
    # Encoding errors name the offending byte or character of the value.
    if isinstance(error, UnicodeError):
        return f"a secret value is not valid base64-encoded UTF-8 ({type(error).__name__})"
    # Validation messages can quote client input; escape line breaks and other
    # control characters so it cannot forge additional log lines.
    return str(error).encode("unicode_escape").decode("ascii")


def is_blank(value: Optional[str]) -> bool:
    return value is None or value.strip() == ""


def verify(name: str, value: Optional[str], mandatory: bool = True) -> None:
    if mandatory and is_blank(value):
        raise ValueError(f"{name} was not given")


def run_kubeseal(
    cleartext_secrets: List[Secret],
    secret_namespace: Optional[str],
    secret_name: Optional[str],
    scope: Scope = Scope.STRICT,
) -> list[KeyValuePair]:
    """Check input and initiate kubeseal-cli call."""

    verify("secret_namespace", secret_namespace, scope.needs_namespace())
    verify("secret_name", secret_name, scope.needs_name())

    list_of_non_dict_inputs = [
        element for element in cleartext_secrets if not isinstance(element, Secret)
    ]
    if cleartext_secrets and list_of_non_dict_inputs:
        error_message = "Input of cleartext_secrets was not a list of dicts."
        raise ValueError(error_message)

    return [
        run_kubeseal_command(
            cleartext_secret_tuple, secret_namespace, secret_name, scope
        )
        for cleartext_secret_tuple in cleartext_secrets
    ]


def valid_k8s_name(value: str | None) -> str:
    if not value:
        raise ValueError("Invalid k8s name: Must not be empty or None")
    if re.match(r"^[a-z0-9]([a-z0-9_.-]{,251}[a-z0-9])?$", value):
        return value
    raise ValueError(f"Invalid k8s name: {value}")


def run_kubeseal_command(
    cleartext_secret_tuple: Secret,
    secret_namespace: Optional[str],
    secret_name: Optional[str],
    scope: Scope = Scope.STRICT,
) -> KeyValuePair:
    LOGGER.debug(
        "Sealing secret '%s.%s' for namespace '%s' with scope '%s'.",
        secret_name,
        cleartext_secret_tuple.key,
        secret_namespace,
        scope.value,
    )

    if settings.mock_enabled:
        return KeyValuePair(
            key=cleartext_secret_tuple.key,
            value="AgBy3... (Mock Sealed Secret)"
        )

    if cleartext_secret_tuple.value is not None:
        cleartext_secret = decode_base64_string(cleartext_secret_tuple.value)
        return encrypt_value_or_file(
            cleartext_secret_tuple,
            secret_namespace,
            secret_name,
            cleartext_secret,
            settings.kubeseal_binary,
            settings.kubeseal_cert,
            scope,
        )
    if cleartext_secret_tuple.file is not None:
        file_secret = decode_base64_bytearray(cleartext_secret_tuple.file)
        return encrypt_value_or_file(
            cleartext_secret_tuple,
            secret_namespace,
            secret_name,
            file_secret,
            settings.kubeseal_binary,
            settings.kubeseal_cert,
            scope,
            encoding=None,
        )
    raise RuntimeError("Invalid parameters. Must have a file or a value")


@overload
def encrypt_value_or_file(
    cleartext_secret_tuple: Secret,
    secret_namespace: str | None,
    secret_name: str | None,
    cleartext_secret: str,
    binary: str,
    cert: str,
    scope: Scope,
    encoding: str = "utf-8",
) -> KeyValuePair: ...


@overload
def encrypt_value_or_file(
    cleartext_secret_tuple: Secret,
    secret_namespace: str | None,
    secret_name: str | None,
    cleartext_secret: bytearray,
    binary: str,
    cert: str,
    scope: Scope,
    encoding: None = None,
) -> KeyValuePair: ...


def encrypt_value_or_file(
    cleartext_secret_tuple: Secret,
    secret_namespace: str | None,
    secret_name: str | None,
    cleartext_secret: Union[str, bytearray],
    binary: str,
    cert: str,
    scope: Scope,
    encoding: Optional[str] = "utf-8",
) -> KeyValuePair:
    kubeseal_command_cmd = construct_kubeseal_cmd(
        secret_namespace, secret_name, binary, cert, scope
    )
    try:
        kubeseal_subprocess = subprocess.Popen(  # noqa: S603 input has been checked above
            kubeseal_command_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding=encoding,
        )
    except FileNotFoundError as file_error:
        raise RuntimeError("Could not find kubeseal binary") from file_error

    if encoding:
        output, error = kubeseal_subprocess.communicate(input=cleartext_secret)
    else:
        output_bytes, error_bytes = kubeseal_subprocess.communicate(
            input=cleartext_secret
        )
        output, error = output_bytes.decode("utf-8"), error_bytes.decode("utf-8")

    # Not logged here: the caller logs the failure once, with request context.
    if error or kubeseal_subprocess.returncode != 0:
        raise RuntimeError(
            f"Error in run_kubeseal (exit code {kubeseal_subprocess.returncode}): "
            f"{error.strip() or 'no error output'}"
        )

    sealed_secret = "".join(output.split("\n"))
    return KeyValuePair(key=cleartext_secret_tuple.key, value=sealed_secret)


def construct_kubeseal_cmd(
    secret_namespace: str | None,
    secret_name: str | None,
    binary: str,
    cert: str,
    scope: Scope,
) -> list[str]:
    exec_kubeseal_command = [
        binary,
        "--raw",
        "--from-file=/dev/stdin",
        "--cert",
        cert,
        "--scope",
        scope.value,
    ]
    if scope.needs_namespace():
        exec_kubeseal_command.extend(
            [
                "--namespace",
                valid_k8s_name(secret_namespace),
            ]
        )
    if scope.needs_name():
        exec_kubeseal_command.extend(
            [
                "--name",
                valid_k8s_name(secret_name),
            ]
        )

    return exec_kubeseal_command


def decode_base64_string(base64_string_message: str) -> str:
    """Decode base64 ascii-encoded input."""
    base64_bytes = base64_string_message.encode("ascii")
    message_bytes = base64.b64decode(base64_bytes)
    return message_bytes.decode("utf-8")


def decode_base64_bytearray(base64_string_message: str) -> bytearray:
    """Decode base64 ascii-encoded input."""
    base64_bytes = base64_string_message.encode("ascii")
    return bytearray(base64.b64decode(base64_bytes))
