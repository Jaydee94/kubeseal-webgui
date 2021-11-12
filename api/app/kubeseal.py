"""Provides REST-API and kubeseal-cli specific functionality."""
import base64
import logging
import re
import subprocess

from flask import request, abort
from flask_restful import Resource

LOGGER = logging.getLogger("kubeseal-webgui")


class KubesealEndpoint(Resource):
    """Provides REST-API for sealing sensitive data."""

    @classmethod
    def get(cls) -> str:
        """
        Return info message. Used for health checks.

        Refer to POST method for sealing a secret.
        """
        return "Use POST HTTP request to seal secret."

    @classmethod
    def post(cls) -> list:
        """
        Provide sealing functionality via kubeseal-cli.

        Requires input of secretName, namespaceName and sensitive data in
        key-value format.
        """
        if request.json is None:
            abort(400, "JSON Body was empty. Seal Request is required.")
        sealing_request = request.json
        LOGGER.debug("Got secrets")

        try:
            return run_kubeseal(
                sealing_request["secrets"],
                sealing_request["namespace"],
                sealing_request["secret"],
            )
        except (KeyError, ValueError) as e:
            LOGGER.error("Invalid data when sealing secrets with", exc_info=e)
            abort(400, "Invalid data for sealing secrets: " + str(e))
        except RuntimeError as e:
            LOGGER.error("Problem on server while sealing secrets", exc_info=e)
            abort(500, "Server is dreaming...")


def run_kubeseal(cleartext_secrets, secret_namespace, secret_name) -> list:
    """Check input and initiate kubeseal-cli call."""
    if secret_namespace is None or secret_namespace == "":
        error_message = "secret_namespace was not given"
        LOGGER.error(error_message)
        raise ValueError(error_message)

    if secret_name is None or secret_name == "":
        error_message = "secret_name was not given"
        LOGGER.error(error_message)
        raise ValueError(error_message)

    list_of_non_dict_inputs = [
        element for element in cleartext_secrets if not isinstance(element, dict)
    ]
    if cleartext_secrets and list_of_non_dict_inputs:
        error_message = "Input of cleartext_secrets was not a list of dicts."
        LOGGER.error(error_message)
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
    raise ValueError("Invalid k8s name: {value}")


def run_kubeseal_command(cleartext_secret_tuple, secret_namespace, secret_name):
    """Call kubeseal-cli in subprocess."""
    LOGGER.info(
        "Sealing secret '%s.%s' for namespace '%s'.",
        secret_name,
        cleartext_secret_tuple["key"],
        secret_namespace,
    )
    cleartext_secret = decode_base64_string(cleartext_secret_tuple["value"])
    exec_kubeseal_command = [
        "/kubeseal-webgui/kubeseal",
        "--raw",
        "--from-file=/dev/stdin",
        "--namespace",
        valid_k8s_name(secret_namespace),
        "--name",
        valid_k8s_name(secret_name),
        "--cert",
        "/kubeseal-webgui/cert/kubeseal-cert.pem",
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
        LOGGER.error(error_message)
        raise RuntimeError(error_message)

    sealed_secret = "".join(output.decode("utf-8").split("\n"))
    return {"key": cleartext_secret_tuple["key"], "value": sealed_secret}


def decode_base64_string(base64_string_message: str) -> str:
    """Decode base64 ascii-encoded input."""
    base64_bytes = base64_string_message.encode("ascii")
    message_bytes = base64.b64decode(base64_bytes)
    return message_bytes.decode("utf-8")
