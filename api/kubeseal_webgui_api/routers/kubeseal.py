import base64
import logging
import re
import subprocess
import time

from fastapi import APIRouter, HTTPException

from kubeseal_webgui_api.app_config import settings
from kubeseal_webgui_api.logging_utils import LOGGER_NAME
from kubeseal_webgui_api.routers.models import Data, KeyValuePair, Scope, Secret

router = APIRouter()
LOGGER = logging.getLogger(LOGGER_NAME)


@router.post("/secrets", response_model=list[KeyValuePair])
def encrypt(data: Data) -> list[KeyValuePair]:
    scope = data.scope or Scope.STRICT
    started = time.perf_counter()
    # Only metadata is logged here. Never log `data.secrets` values: they are
    # the cleartext secrets. Name and namespace are logged with %r because they
    # are client input that may not have been validated (escapes line breaks).
    try:
        sealed_secrets = seal_secrets(data.secrets, data.namespace, data.name, scope)
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
        error_type = type(error).__name__
        return f"a secret value is not valid base64-encoded UTF-8 ({error_type})"
    # Validation messages can quote client input; escape line breaks and other
    # control characters so it cannot forge additional log lines.
    return str(error).encode("unicode_escape").decode("ascii")


def is_blank(value: str | None) -> bool:
    return value is None or value.strip() == ""


def require_given(field_name: str, value: str | None) -> None:
    if is_blank(value):
        raise ValueError(f"{field_name} was not given")


def seal_secrets(
    entries: list[Secret],
    secret_namespace: str | None,
    secret_name: str | None,
    scope: Scope = Scope.STRICT,
) -> list[KeyValuePair]:
    """Seal every entry for the given namespace, name and scope."""
    if scope.needs_namespace():
        require_given("secret_namespace", secret_namespace)
    if scope.needs_name():
        require_given("secret_name", secret_name)

    return [
        seal_entry(entry, secret_namespace, secret_name, scope) for entry in entries
    ]


# Names as Kubernetes defines them (RFC 1123); the UI applies the same rules.
# A label: lower case alphanumerics and '-', starting and ending with an
# alphanumeric, at most 63 characters. A subdomain: labels joined by dots, at
# most 253 characters in total.
MAX_DNS_SUBDOMAIN_LENGTH = 253
DNS_LABEL = re.compile(r"[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?")
DNS_SUBDOMAIN = re.compile(
    r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*"
)


def valid_namespace_name(value: str | None) -> str:
    """Return the name if it can be the name of a namespace (a DNS label)."""
    if not value:
        raise ValueError("Invalid k8s namespace name: Must not be empty or None")
    if DNS_LABEL.fullmatch(value):
        return value
    raise ValueError(f"Invalid k8s namespace name: {value}")


def valid_secret_name(value: str | None) -> str:
    """Return the name if it can be the name of a secret (a DNS subdomain)."""
    if not value:
        raise ValueError("Invalid k8s secret name: Must not be empty or None")
    if len(value) <= MAX_DNS_SUBDOMAIN_LENGTH and DNS_SUBDOMAIN.fullmatch(value):
        return value
    raise ValueError(f"Invalid k8s secret name: {value}")


def seal_entry(
    entry: Secret,
    secret_namespace: str | None,
    secret_name: str | None,
    scope: Scope = Scope.STRICT,
) -> KeyValuePair:
    """Seal the value or file of one entry with the kubeseal binary."""
    LOGGER.debug(
        "Sealing secret '%s.%s' for namespace '%s' with scope '%s'.",
        secret_name,
        entry.key,
        secret_namespace,
        scope.value,
    )

    if settings.mock_enabled:
        return KeyValuePair(key=entry.key, value="AgBy3... (Mock Sealed Secret)")

    cleartext = decode_cleartext(entry)
    command = build_kubeseal_command(secret_namespace, secret_name, scope)
    return KeyValuePair(key=entry.key, value=pipe_through_kubeseal(command, cleartext))


def decode_cleartext(entry: Secret) -> bytes:
    """Return the bytes to seal. A `value` has to be UTF-8 text, a `file` not."""
    if entry.value is not None:
        return decode_base64_string(entry.value).encode("utf-8")
    if entry.file is not None:
        return bytes(decode_base64_bytearray(entry.file))
    raise RuntimeError("Invalid parameters. Must have a file or a value")


def pipe_through_kubeseal(command: list[str], cleartext: bytes) -> str:
    """Pipe the cleartext through kubeseal and return the sealed value."""
    try:
        completed = subprocess.run(  # noqa: S603 built from checked input
            command,
            input=cleartext,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as file_error:
        raise RuntimeError("Could not find kubeseal binary") from file_error

    error_output = completed.stderr.decode("utf-8")
    # Not logged here: the caller logs the failure once, with request context.
    if error_output or completed.returncode != 0:
        raise RuntimeError(
            f"Error in run_kubeseal (exit code {completed.returncode}): "
            f"{error_output.strip() or 'no error output'}"
        )

    return "".join(completed.stdout.decode("utf-8").split("\n"))


def build_kubeseal_command(
    secret_namespace: str | None,
    secret_name: str | None,
    scope: Scope,
) -> list[str]:
    command = [
        settings.kubeseal_binary,
        "--raw",
        "--from-file=/dev/stdin",
        "--cert",
        settings.kubeseal_cert,
        "--scope",
        scope.value,
    ]
    if scope.needs_namespace():
        command.extend(["--namespace", valid_namespace_name(secret_namespace)])
    if scope.needs_name():
        command.extend(["--name", valid_secret_name(secret_name)])
    return command


def decode_base64_string(base64_string_message: str) -> str:
    """Decode base64 ascii-encoded input."""
    base64_bytes = base64_string_message.encode("ascii")
    message_bytes = base64.b64decode(base64_bytes)
    return message_bytes.decode("utf-8")


def decode_base64_bytearray(base64_string_message: str) -> bytearray:
    """Decode base64 ascii-encoded input."""
    base64_bytes = base64_string_message.encode("ascii")
    return bytearray(base64.b64decode(base64_bytes))
