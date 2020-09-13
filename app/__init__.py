from flask import Flask
from flask_restful import Api
from os import urandom
import sys
import logging
import json_log_formatter
from .kubeseal import KubesealEndpoint

# Setup JSON handler for logging
formatter = json_log_formatter.JSONFormatter()
json_handler = logging.StreamHandler(stream=sys.stdout)
json_handler.setFormatter(formatter)

# Configure logging settings
kubeseal_logger = logging.getLogger("kubeseal-webgui")
kubeseal_logger.addHandler(json_handler)
kubeseal_logger.setLevel(logging.INFO)

# Set flask werkzeug logger to ERROR
flask_logger = logging.getLogger('werkzeug')
flask_logger.addHandler(json_handler)
flask_logger.setLevel(logging.INFO)

def create_app(test_config=None):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = urandom(24)

    api = Api(app)
    api.add_resource(KubesealEndpoint, '/secrets')

    return app