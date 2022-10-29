import logging
import subprocess
from os import environ

from pydantic import BaseSettings

binary = environ.get("KUBESEAL_BINARY")
mock = environ.get("MOCK_ENABLED", False)


class AppSettings(BaseSettings):
    kubeseal_version: str
    kubeseal_binary: str = binary
    kubeseal_cert: str = environ.get("KUBESEAL_CERT")
    mock_enabled: bool = mock
    mock_namespace_count: int = 20


LOGGER = logging.getLogger("kubeseal-webgui")


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
