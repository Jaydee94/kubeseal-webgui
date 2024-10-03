import logging
import subprocess
from os import environ

from pydantic_settings import BaseSettings

binary = environ.get("KUBESEAL_BINARY", "/bin/false")
mock = environ.get("MOCK_ENABLED", "False").lower() == "true"
autofetch = environ.get("KUBESEAL_AUTOFETCH", "false")
kubeseal_cert = environ.get("KUBESEAL_CERT", "/kubeseal-webgui/cert/kubeseal-cert.pem")


class AppSettings(BaseSettings):
    kubeseal_version: str
    kubeseal_binary: str = binary
    kubeseal_cert: str = environ.get("KUBESEAL_CERT", "/dev/null")
    mock_enabled: bool = mock
    mock_namespace_count: int = 120


LOGGER = logging.getLogger("kubeseal-webgui")


def fetch_sealed_secrets_cert() -> None:
    if mock or autofetch == "false":
        return

    sealed_secrets_namespace = environ.get(
        "KUBESEAL_CONTROLLER_NAMESPACE", "sealed-secrets"
    )
    sealed_secrets_controller_name = environ.get(
        "KUBESEAL_CONTROLLER_NAME", "sealed-secrets-controller"
    )

    LOGGER.info(
        "Fetch certificate from sealed secrets controller '%s' in namespace '%s'",
        sealed_secrets_controller_name,
        sealed_secrets_namespace,
    )
    kubeseal_subprocess = subprocess.Popen(
        [
            binary,
            "--fetch-cert",
            "--controller-name",
            sealed_secrets_controller_name,
            "--controller-namespace",
            sealed_secrets_namespace,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    output, error = kubeseal_subprocess.communicate()
    if error:
        error_message = f"Error in run_kubeseal: {error}"
        LOGGER.error(error_message)
        raise RuntimeError(error_message)
    with open(kubeseal_cert, "w") as file:
        LOGGER.info("Saving certificate in '%s'", kubeseal_cert)
        file.write(output)


def get_kubeseal_version() -> str:
    """Retrieve the kubeseal binary version."""
    LOGGER.debug("Retrieving kubeseal binary version.")
    kubeseal_subprocess = subprocess.Popen(
        [binary, "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    output, error = kubeseal_subprocess.communicate()
    if error:
        error_message = f"Error in run_kubeseal: {error}"
        LOGGER.error(error_message)
        raise RuntimeError(error_message)

    version = "".join(output.split("\n"))

    return str(version).split(":")[1].replace('"', "").lstrip()


settings = AppSettings(
    kubeseal_version=get_kubeseal_version(),
)
