"""Module containing the API for encoding sensitive data via kubeseal-cli."""
import logging
import sys
from os import environ
from os.path import exists

import json_log_formatter
from flask import Flask
from flask_cors import CORS
from flask_restful import Api

from .config import AppConfigEndpoint
from .kubernetes import KubernetesNamespacesEndpoint
from .kubeseal import KubesealEndpoint

# Setup JSON handler for logging
formatter = json_log_formatter.JSONFormatter()
json_handler = logging.StreamHandler(stream=sys.stdout)
json_handler.setFormatter(formatter)

# Configure logging settings
LOGGER = logging.getLogger("kubeseal-webgui")
LOGGER.addHandler(json_handler)
LOGGER.setLevel(logging.INFO)

# Set flask werkzeug logger to ERROR
flask_logger = logging.getLogger("werkzeug")
flask_logger.addHandler(json_handler)
flask_logger.setLevel(logging.INFO)


def create_app(test_config=None) -> Flask:
    """Initialize Flask application module."""
    app = Flask(__name__)

    init_config(app.config, test_config)

    err = validate_config(app.config)
    if err is not None:
        raise RuntimeError("Error: %s" % err)

    CORS(app, resources={r"/secrets/*": {"origins": app.config.get("ORIGIN_URL")}})
    CORS(app, resources={r"/namespaces/*": {"origins": app.config.get("ORIGIN_URL")}})
    CORS(app, resources={r"/config/*": {"origins": app.config.get("ORIGIN_URL")}})

    api = Api(app)
    api.add_resource(KubesealEndpoint, "/secrets")
    api.add_resource(KubernetesNamespacesEndpoint, "/namespaces")
    api.add_resource(AppConfigEndpoint, "/config")

    return app


def init_config(cfg, test_config=None):
    """Parse environment variables into the app config."""
    needles = [
        "ORIGIN_URL",
        "KUBESEAL_CERT",
        "KUBESEAL_BINARY",
    ]

    if test_config is None:
        # when not testing, load the instance config if it exists
        cfg.from_pyfile("config.py", silent=True)
    else:
        # when testing, load the test config
        cfg.from_mapping(test_config)

    for needle in needles:
        if needle in environ:
            cfg[needle] = environ[needle]


def validate_config(cfg):
    """Validate the configuration data."""
    binary = cfg.get("KUBESEAL_BINARY")
    cert = cfg.get("KUBESEAL_CERT")

    if cfg.get("ORIGIN_URL") is None:
        return "ORIGIN_URL is not set"

    if cert is None:
        return "KUBESEAL_CERT is not set"

    if binary is None:
        return "KUBESEAL_BINARY is not set"

    if not exists(cert):
        return "KUBESEAL_CERT '%s' does not exist" % cert

    if not exists(binary):
        return "KUBESEAL_BINARY '%s' does not exist" % binary

    return None
