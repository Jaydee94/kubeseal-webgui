from fastapi import APIRouter
import json
import re
import subprocess
import tempfile
import os
import base64
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter()


class Data(BaseModel):
    secret: str
    namespace: str
    secrets: List[Dict[str, str]]


@router.post("/secrets")
def encrypt(data: Data) -> list:
    # try:
    return json.dumps(
        run_kubeseal(
            data.secrets,
            data.namespace,
            data.secret,
        )
    )


# except (KeyError, ValueError) as e:
#     raise HTTPException(400, f"Invalid data for sealing secrets: {e}")
# except RuntimeError:
#     raise HTTPException(500, "Server is dreaming...")


def run_kubeseal(cleartext_secrets, secret_namespace, secret_name) -> list:
    """Check input and initiate kubeseal-cli call."""
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
            cleartext_secret_tuple, secret_namespace, secret_name
        )
        sealed_secrets.append(sealed_secret)
    return sealed_secrets


def valid_k8s_name(value: str) -> str:
    if re.match(r"^[a-z0-9]([a-z0-9_.-]{,251}[a-z0-9])?$", value):
        return value
    raise ValueError(f"Invalid k8s name: {value}")


def run_kubeseal_command(cleartext_secret_tuple: Dict, secret_namespace, secret_name):
    cleartext_secret = ""
    cleartext_file = ""
    if "value" in cleartext_secret_tuple:
        cleartext_secret = decode_base64_string(cleartext_secret_tuple["value"])
        type = "text"
    elif "file" in cleartext_secret_tuple:
        cleartext_file = decode_base64_string(cleartext_secret_tuple["file"])
        type = "file"
    else:
        raise ValueError("Missing 'value' or 'file' in request.")

    binary = "/tmp/kubeseal"
    cert = "/tmp/cert.pem"
    if cleartext_secret:
        sealed_secret = encrypt_value_or_file(
            secret_namespace, secret_name, cleartext_secret, binary, cert, type
        )
    if cleartext_file:
        sealed_secret = encrypt_value_or_file(
            secret_namespace, secret_name, cleartext_secret, binary, cert, type
        )

    return {"key": cleartext_secret_tuple["key"], "value": sealed_secret}


def encrypt_value_or_file(
    secret_namespace, secret_name, cleartext_secret, binary, cert, type
) -> str:
    if type == "text":
        temp_secret_file = "/dev/stdin"
    if type == "file":
        temp = tempfile.NamedTemporaryFile("w")
        temp.write(cleartext_secret)
        temp_secret_file = temp.name

    exec_kubeseal_command = [
        binary,
        "--raw",
        f"--from-file={temp_secret_file}",
        "--namespace",
        valid_k8s_name(secret_namespace),
        "--name",
        valid_k8s_name(secret_name),
        "--cert",
        cert,
    ]
    kubeseal_subprocess = subprocess.Popen(
        exec_kubeseal_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output, error = kubeseal_subprocess.communicate(
        input=cleartext_secret.encode("utf-8")
    )

    if error:
        error_message = f"Error in run_kubeseal: {error}"
        raise RuntimeError(error_message)
    sealed_secret = "".join(output.decode("utf-8").split("\n"))
    os.remove(temp_secret_file)
    return sealed_secret


def decode_base64_string(base64_string_message: str) -> str:
    """Decode base64 ascii-encoded input."""
    base64_bytes = base64_string_message.encode("ascii")
    message_bytes = base64.b64decode(base64_bytes)
    return message_bytes.decode("utf-8")
