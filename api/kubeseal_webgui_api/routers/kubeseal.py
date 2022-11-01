import base64
import logging
import re
import subprocess
from enum import Enum
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from kubeseal_webgui_api.app_config import settings

router = APIRouter()
LOGGER = logging.getLogger(__name__)


class Data(BaseModel):
    secret: str
    namespace: str
    secrets: List[Dict[str, str]]


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
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(400, f"Invalid data for sealing secrets: {e}")
    except RuntimeError:
        raise HTTPException(500, "Server is dreaming...")


def is_blank(value: str) -> bool:
    return value is None or value.strip() == ""


def run_kubeseal(
    cleartext_secrets, secret_namespace, secret_name, scope=Scope.STRICT.value
) -> list:
    """Check input and initiate kubeseal-cli call."""
    if is_blank(scope):
        scope = Scope.STRICT
    else:
        try:
            scope = Scope(scope)
        except ValueError as error:
            error_message = "scope is not of allowed value"
            LOGGER.error(error_message)
            raise ValueError(error_message) from error

    if is_blank(secret_namespace) and scope.needs_namespace():
        error_message = "secret_namespace was not given"
        LOGGER.error(error_message)
        raise ValueError(error_message)

    if is_blank(secret_name) and scope.needs_name():
        error_message = "secret_name was not given"
        LOGGER.error(error_message)
        raise ValueError(error_message)

    if secret_namespace is None or secret_namespace == "":
        error_message = "secret_namespace was not given"
        raise ValueError(error_message)

    if secret_name is None or secret_name == "":
        error_message = "secret_name was not given"
        raise ValueError(error_message)

    list_of_non_dict_inputs = [
        element for element in cleartext_secrets if not isinstance(element, dict)
    ]
    if cleartext_secrets and list_of_non_dict_inputs:
        error_message = "Input of cleartext_secrets was not a list of dicts."
        raise ValueError(error_message)

    sealed_secrets = []
    for cleartext_secret_tuple in cleartext_secrets:
        sealed_secret = run_kubeseal_command(
            cleartext_secret_tuple, secret_namespace, secret_name, scope
        )
        sealed_secrets.append(sealed_secret)
    return sealed_secrets


def valid_k8s_name(value: str) -> str:
    if re.match(r"^[a-z0-9]([a-z0-9_.-]{,251}[a-z0-9])?$", value):
        return value
    raise ValueError(f"Invalid k8s name: {value}")


def run_kubeseal_command(
    cleartext_secret_tuple: Dict,
    secret_namespace,
    secret_name,
    scope: Scope = Scope.STRICT,
):
    LOGGER.info(
        "Sealing secret '%s.%s' for namespace '%s' with scope '%s'.",
        secret_name,
        cleartext_secret_tuple["key"],
        secret_namespace,
        scope,
    )
    cleartext_secret = decode_base64_string(cleartext_secret_tuple["value"])
    if "value" in cleartext_secret_tuple:
        cleartext_secret = decode_base64_string(cleartext_secret_tuple["value"])
    elif "file" in cleartext_secret_tuple:
        cleartext_secret = decode_base64_string(cleartext_secret_tuple["file"])
    else:
        raise ValueError("Missing 'value' or 'file' in request.")
    sealed_secret = encrypt_value_or_file(
        cleartext_secret_tuple,
        secret_namespace,
        secret_name,
        cleartext_secret,
        settings.kubeseal_binary,
        settings.kubeseal_cert,
        scope,
    )

    return {"key": cleartext_secret_tuple["key"], "value": sealed_secret}


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
    kubeseal_subprocess = subprocess.Popen(
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
