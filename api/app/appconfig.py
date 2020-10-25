"""Provides REST-API for public app configuration."""
import logging
import os

from flask import jsonify
from flask_restful import Resource

LOGGER = logging.getLogger("kubeseal-webgui")


class AppConfigEndpoint(Resource):
    """Provide the app configuration"""

    @classmethod
    def get(cls):
        """Provides app configuration via env variables as json object."""
        settings = {}
        if 'INSTANCE_NAME' in os.environ:
            instance_name = os.environ.get('INSTANCE_NAME')
            settings["INSTANCE_NAME"] = instance_name
            return jsonify(settings)
        return jsonify(settings)
