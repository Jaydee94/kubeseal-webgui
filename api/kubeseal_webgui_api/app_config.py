"""Application settings and the start-up tasks that depend on them.

Importing this module has no side effects: the kubeseal binary is only run
when the application starts (see ``lifespan`` in ``app.py``) or when a value
that needs it is requested.
"""

import functools
import logging
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from pydantic_settings import BaseSettings

from kubeseal_webgui_api.logging_utils import LOGGER_NAME

LOGGER = logging.getLogger(LOGGER_NAME)

MOCK_KUBESEAL_VERSION = "0.1.0"


class AppSettings(BaseSettings):
    """All configuration, read from the environment (``KUBESEAL_BINARY`` ...)."""

    kubeseal_binary: str = "/bin/false"
    kubeseal_cert: str = "/kubeseal-webgui/cert/kubeseal-cert.pem"
    kubeseal_autofetch: bool = False
    kubeseal_controller_namespace: str = "sealed-secrets"
    kubeseal_controller_name: str = "sealed-secrets-controller"
    mock_enabled: bool = False
    mock_namespace_count: int = 120
    # Where the UI is served from, if that is not where the API is served
    # from: the one origin that may call the API across origins (CORS).
    origin_url: str = "http://localhost:8080"


settings = AppSettings()


def cors_origins(url: str) -> list[str]:
    """Return the origins that may call the API from another origin.

    Browsers send an origin without path or trailing slash, so a configured
    URL such as ``https://example.com/kubeseal/`` is reduced to scheme, host
    and port. Anything that is not an absolute URL (the chart passes its
    ``api.url``, which may be empty or a path) allows no other origin; a UI
    served from the same origin as the API does not need one.
    """
    parts = urlsplit(url.strip())
    if not parts.scheme or not parts.netloc:
        return []
    return [f"{parts.scheme}://{parts.netloc}"]


def _run_kubeseal(arguments: list[str], purpose: str) -> str:
    """Run the kubeseal binary and return its stdout, logging any failure."""
    binary = settings.kubeseal_binary
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
    if settings.mock_enabled:
        LOGGER.info("Mock mode is enabled, not fetching a certificate.")
        return
    if not settings.kubeseal_autofetch:
        LOGGER.info(
            "Certificate auto-fetch is disabled, using certificate at '%s'.",
            settings.kubeseal_cert,
        )
        return

    # Named without "secret": these identify the controller and are not
    # sensitive, but static analysis flags any "*secret*" variable in a log call.
    controller_namespace = settings.kubeseal_controller_namespace
    controller_name = settings.kubeseal_controller_name

    LOGGER.info(
        "Fetch certificate from sealed secrets controller '%s' in namespace '%s'",
        controller_name,
        controller_namespace,
    )
    output = _run_kubeseal(
        [
            "--fetch-cert",
            "--controller-name",
            controller_name,
            "--controller-namespace",
            controller_namespace,
        ],
        f"fetch the certificate from controller '{controller_name}' "
        f"in namespace '{controller_namespace}'",
    )
    LOGGER.info("Saving certificate in '%s'", settings.kubeseal_cert)
    Path(settings.kubeseal_cert).write_text(output)


@functools.cache
def _detect_kubeseal_version(binary: str) -> str:
    """Ask the binary for its version. Successful results are cached."""
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


def get_kubeseal_version() -> str:
    """Return the kubeseal version; the binary is run at most once.

    Mock mode never runs the binary. Called during application start-up, so
    an unusable binary stops a real deployment before it serves any request.
    """
    if settings.mock_enabled:
        return MOCK_KUBESEAL_VERSION
    return _detect_kubeseal_version(settings.kubeseal_binary)
