"""Provides REST-API and kubeseal-cli specific functionality."""
import json
import logging
from typing import Optional

from flask_restful import Resource, abort
from kubernetes import client, config

LOGGER = logging.getLogger("kubeseal-webgui")


class KubernetesNamespacesEndpoint(Resource):
    """Provide REST-API for sealing sensitive data."""

    @classmethod
    def get(cls) -> Optional[str]:
        """Retrieve cluster namespaces."""
        try:
            namespaces = get_incluster_namespaces()
        except RuntimeError:
            abort(500)
        return namespaces


def get_incluster_namespaces() -> str:
    """Retrieve all namespaces from current kubernetes cluster as JSON-Array."""
    config.load_incluster_config()
    namespaces_list = []

    LOGGER.info("Resolving in-cluster Namespaces")
    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace()
    if isinstance(namespaces, client.V1NamespaceList) and namespaces.items:
        for ns in namespaces.items:
            namespaces_list.append(ns.metadata.name)
    else:
        LOGGER.warn("No valid namespace list available via %s", namespaces)

    LOGGER.debug("Namespaces list %s", namespaces_list)
    return json.dumps(namespaces_list)
