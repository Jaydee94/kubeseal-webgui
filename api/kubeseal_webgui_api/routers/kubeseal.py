import base64
import logging
import re
import subprocess  # noqa: S404 the binary has to be configured by an admin
from enum import Enum
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from kubeseal_webgui_api.app_config import settings

router = APIRouter()
LOGGER = logging.getLogger(__name__)


class Data(BaseModel):
    secret: Optional[str]
    namespace: Optional[str]
    secrets: List[Dict[str, str]]
    scope: str


class Scope(Enum):
    STRICT = "strict"
    CLUSTER_WIDE = "cluster-wide"
    NAMESPACE_WIDE = "namespace-wide"

    def needs_name(self):
        return self not in (Scope.CLUSTER_WIDE, Scope.NAMESPACE_WIDE)

    def needs_namespace(self):
        return self is not Scope.CLUSTER_WIDE


@router.post("/secrets")
def encrypt(data: Data) -> list:
    try:
        return run_kubeseal(
            data.secrets,
            data.namespace,
            data.secret,
            data.scope,
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(400, f"Invalid data for sealing secrets: {e}")
    except RuntimeError:
        raise HTTPException(500, "Server is dreaming...")


def is_blank(value: Optional[str]) -> bool:
    return value is None or value.strip() == ""


def verify(name: str, value: Optional[str], mandatory=True):
    if mandatory and is_blank(value):
        error_message = f"{name} was not given"
        LOGGER.error(error_message)
        raise ValueError(error_message)


def run_kubeseal(
    cleartext_secrets: List[Dict[str, str]],
    secret_namespace: Optional[str],
    secret_name: Optional[str],
    scope_value: str = Scope.STRICT.value,
) -> list:
    """Check input and initiate kubeseal-cli call."""
    try:
        scope = Scope(scope_value or Scope.STRICT.value)
    except ValueError as error:
        error_message = "scope is not of allowed value"
        LOGGER.error(error_message)
        raise ValueError(error_message) from error

    verify("secret_namespace", secret_namespace, scope.needs_namespace())
    verify("secret_name", secret_name, scope.needs_name())

    list_of_non_dict_inputs = [
        element for element in cleartext_secrets if not isinstance(element, dict)
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


def valid_k8s_name(value: str) -> str:
    if re.match(r"^[a-z0-9]([a-z0-9_.-]{,251}[a-z0-9])?$", value):
        return value
    raise ValueError(f"Invalid k8s name: {value}")


def run_kubeseal_command(
    cleartext_secret_tuple: Dict[str, str],
    secret_namespace: Optional[str],
    secret_name: Optional[str],
    scope: Scope = Scope.STRICT,
):
    LOGGER.info(
        "Sealing secret '%s.%s' for namespace '%s' with scope '%s'.",
        secret_name,
        cleartext_secret_tuple["key"],
        secret_namespace,
        scope,
    )
    if "value" in cleartext_secret_tuple:
        cleartext_secret = decode_base64_string(cleartext_secret_tuple["value"])
    elif "file" in cleartext_secret_tuple:
        cleartext_secret = decode_base64_string(cleartext_secret_tuple["file"])
    else:
        raise ValueError("Missing 'value' or 'file' in request.")
    return encrypt_value_or_file(
        cleartext_secret_tuple,
        secret_namespace,
        secret_name,
        cleartext_secret,
        settings.kubeseal_binary,
        settings.kubeseal_cert,
        scope,
    )


def encrypt_value_or_file(
    cleartext_secret_tuple,
    secret_namespace,
    secret_name,
    cleartext_secret,
    binary,
    cert,
    scope,
) -> Dict:
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
    kubeseal_subprocess = subprocess.Popen(  # noqa: S603 input has been checked above
        exec_kubeseal_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )

    output, error = kubeseal_subprocess.communicate(input=cleartext_secret)

    if error:
        error_message = f"Error in run_kubeseal: {error}"
        LOGGER.error(error_message)
        raise RuntimeError(error_message)

    sealed_secret = "".join(output.split("\n"))
    return {"key": cleartext_secret_tuple["key"], "value": sealed_secret}


def decode_base64_string(base64_string_message: str) -> str:
    """Decode base64 ascii-encoded input."""
    base64_bytes = base64_string_message.encode("ascii")
    message_bytes = base64.b64decode(base64_bytes)
    return message_bytes.decode("utf-8")
