import base64
import logging
import re
import subprocess  # noqa: S404 the binary has to be configured by an admin
from typing import List, Optional, Union, overload

from fastapi import APIRouter, HTTPException
from prometheus_client import Counter, Histogram

from kubeseal_webgui_api.app_config import settings
from kubeseal_webgui_api.routers.models import Data, KeyValuePair, Scope, Secret

router = APIRouter()
LOGGER = logging.getLogger("kubeseal-webgui")

SECRETS_ENCRYPTED = Counter("kubeseal_webgui_secrets_encrypted_total", "Total encrypted secrets")
ENCRYPTION_FAILURES = Counter("kubeseal_webgui_encryption_failures_total", "Total failed encryption attempts")
ENCRYPTION_LATENCY = Histogram("kubeseal_webgui_encryption_latency_seconds", "Latency for encryption operations")

@router.post("/secrets", response_model=List[KeyValuePair])
def encrypt(data: Data) -> list[KeyValuePair]:
    with ENCRYPTION_LATENCY.time():
        try:
            result = run_kubeseal(
                data.secrets,
                data.namespace,
                data.secret,
                data.scope or Scope.STRICT,
            )
            SECRETS_ENCRYPTED.inc()
            return result
        except (KeyError, ValueError) as e:
            ENCRYPTION_FAILURES.inc()  # Increment failure counter
            LOGGER.error("Encryption failed due to invalid input: %s", e)
            raise HTTPException(400, f"Invalid data for sealing secrets: {e}") from e
        except RuntimeError as e:
            ENCRYPTION_FAILURES.inc()  # Increment failure counter
            LOGGER.error("Encryption failed due to runtime error: %s", e)
            raise HTTPException(500, "Server is dreaming...") from e


def is_blank(value: Optional[str]) -> bool:
    return value is None or value.strip() == ""


def verify(name: str, value: Optional[str], mandatory: bool = True) -> None:
    if mandatory and is_blank(value):
        error_message = f"{name} was not given"
        LOGGER.error(error_message)
        raise ValueError(error_message)


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
    LOGGER.info(
        "Sealing secret '%s.%s' for namespace '%s' with scope '%s'.",
        secret_name,
        cleartext_secret_tuple.key,
        secret_namespace,
        scope,
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

    if error:
        error_message = f"Error in run_kubeseal: {error}"
        LOGGER.error(error_message)
        raise RuntimeError(error_message)

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
