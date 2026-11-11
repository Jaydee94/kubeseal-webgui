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


def _run_kubeseal(arguments: list[str], purpose: str) -> str:
    """Run the kubeseal binary and return its stdout, logging any failure."""
    command = [binary, *arguments]
    LOGGER.debug("Running %s", command)
    try:
        completed = subprocess.run(  # noqa: S603 the binary is configured by an admin
            command,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as os_error:
        error_message = f"Failed to {purpose}: cannot execute '{binary}': {os_error}"
        LOGGER.error(error_message)
        raise RuntimeError(error_message) from os_error

    if completed.stderr or completed.returncode != 0:
        error_message = (
            f"Failed to {purpose} (exit code {completed.returncode}): "
            f"{completed.stderr.strip() or 'no error output'}"
        )
        LOGGER.error(error_message)
        raise RuntimeError(error_message)
    return completed.stdout


def fetch_sealed_secrets_cert() -> None:
    if mock:
        LOGGER.info("Mock mode is enabled, not fetching a certificate.")
        return
    if autofetch == "false":
        LOGGER.info(
            "Certificate auto-fetch is disabled, using certificate at '%s'.",
            kubeseal_cert,
        )
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
    output = _run_kubeseal(
        [
            "--fetch-cert",
            "--controller-name",
            sealed_secrets_controller_name,
            "--controller-namespace",
            sealed_secrets_namespace,
        ],
        f"fetch the certificate from controller '{sealed_secrets_controller_name}' "
        f"in namespace '{sealed_secrets_namespace}'",
    )
    with open(kubeseal_cert, "w") as file:
        LOGGER.info("Saving certificate in '%s'", kubeseal_cert)
        file.write(output)


def get_kubeseal_version() -> str:
    """Retrieve the kubeseal binary version."""
    LOGGER.debug("Retrieving kubeseal binary version.")
    output = _run_kubeseal(["--version"], "determine the kubeseal version")

    try:
        version = "".join(output.split("\n")).split(":")[1].replace('"', "").lstrip()
    except IndexError:
        error_message = (
            f"Unexpected output of '{binary} --version': {output!r}. "
            "Check that KUBESEAL_BINARY points to a kubeseal binary."
        )
        LOGGER.error(error_message)
        raise RuntimeError(error_message) from None

    LOGGER.debug("Detected kubeseal version '%s'.", version)
    return version


settings = AppSettings(
    kubeseal_version=get_kubeseal_version(),
)
