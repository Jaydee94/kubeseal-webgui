"""Provides REST-API and kubeseal-cli specific functionality."""
import json
import logging
import subprocess

from flask import abort, current_app
from flask_restful import Resource

LOGGER = logging.getLogger("kubeseal-webgui")


class AppConfigEndpoint(Resource):
    """Provide REST-API for retrieving api config information."""

    @classmethod
    def get(cls):
        """Retrieve api configs."""
        try:
            return get_app_config()
        except RuntimeError:
            abort(500, "Can't get config from server")


def get_kubeseal_version() -> str:
    """Retrieve the kubeseal binary version."""
    LOGGER.debug("Retrieving kubeseal binary version.")
    binary = current_app.config.get("KUBESEAL_BINARY")
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


def get_app_config():
    """Return the app configs in json format."""
    config = {}
    config["kubeseal_version"] = get_kubeseal_version()

    return json.dumps(config)
