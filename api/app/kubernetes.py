"""Provides REST-API and kubeseal-cli specific functionality."""
import logging
import json

from kubernetes import client, config
from flask_restful import Resource, abort

LOGGER = logging.getLogger("kubeseal-webgui")


class KubernetesNamespacesEndpoint(Resource):
    """Provides REST-API for sealing sensitive data."""

    @classmethod
    def get(cls):
        """References GET method. Used for retrieving cluster namespaces."""
        try:
            return get_incluster_namespaces()
        except RuntimeError:
            abort(500)


def get_incluster_namespaces():
    """
    Function for retrieving all namespaces from current kubernetes cluster as JSON-Array
    """
    config.load_incluster_config()
    namespaces_list = []

    v1 = client.CoreV1Api()
    LOGGER.info("Resolving in-cluster Namespaces")
    namespaces = v1.list_namespace()
    for ns in namespaces.items:
        namespaces_list.append(ns.metadata.name)

    LOGGER.debug("Namespaces list %s", namespaces_list)
    return json.dumps(namespaces_list)
