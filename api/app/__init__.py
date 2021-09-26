"""Module containing the API for encoding sensitive data via kubeseal-cli."""
from os import environ
import sys
import logging
from flask import Flask
from flask_restful import Api
from flask_cors import CORS
import json_log_formatter
from .kubeseal import KubesealEndpoint
from .kubernetes import KubernetesNamespacesEndpoint

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


def create_app(test_config=None):
    """Initialize Flask application module."""
    app = Flask(__name__)

    if test_config is None:
        # when not testing, load the instance config if it exists
        app.config.from_pyfile("config.py", silent=True)
    else:
        # when testing, load the test config
        app.config.from_mapping(test_config)

    if "ORIGIN_URL" not in environ:
        raise RuntimeError("Error: Environment variable ORIGIN_URL empty.")

    CORS(app, resources={r"/secrets/*": {"origins": environ["ORIGIN_URL"]}})
    CORS(app, resources={r"/namespaces/*": {"origins": environ["ORIGIN_URL"]}})

    api = Api(app)
    api.add_resource(KubesealEndpoint, "/secrets")
    api.add_resource(KubernetesNamespacesEndpoint, "/namespaces")

    return app
