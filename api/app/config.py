"""Provides REST-API and kubeseal-cli specific functionality."""
import json
import logging
import subprocess

from flask_restful import Resource, abort

LOGGER = logging.getLogger("kubeseal-webgui")


class AppConfigEndpoint(Resource):
    """Provide REST-API for retrieving api config information."""

    @classmethod
    def get(cls):
        """Retrieve api configs."""
        try:
            return get_app_config()
        except RuntimeError:
            abort(500)


def get_kubeseal_version() -> str:
    """Retrieve the kubeseal binary version."""
    kubeseal_subprocess = subprocess.Popen(
        ["/kubeseal-webgui/kubeseal --version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output, error = kubeseal_subprocess.communicate()
    if error:
        error_message = f"Error in run_kubeseal: {error}"
        LOGGER.error(error_message)
        raise RuntimeError(error_message)

    version = "".join(output.decode("utf-8").split("\n"))

    result = str(version).split(":")[1].replace('"', "").lstrip()
    LOGGER.debug("Retrieving kubeseal binary version.")
    return result


def get_app_config():
    """Return the app configs in json format."""
    config = {}
    config["kubeseal_version"] = get_kubeseal_version()

    return json.dumps(config)
