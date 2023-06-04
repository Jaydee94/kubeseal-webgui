import itertools
import logging
import random
from typing import List, Optional

from kubernetes import config
from kubernetes.client import ApiClient, CoreV1Api, V1NamespaceList

LOGGER = logging.getLogger("kubeseal-webgui")


class KubernetesClient:
    def __init__(self, api_client: Optional[ApiClient] = None):
        self._api_client = api_client

    def get_namespaces(self) -> List[str]:
        """Retrieve a list of namespaces from current kubernetes cluster."""
        namespaces_list = []

        LOGGER.info("Resolving in-cluster Namespaces")
        v1 = CoreV1Api(api_client=self.api_client())
        namespaces = v1.list_namespace()
        if isinstance(namespaces, V1NamespaceList) and namespaces.items:
            for ns in namespaces.items:
                namespaces_list.append(ns.metadata.name)
        else:
            LOGGER.warning("No valid namespace list available via %s", namespaces)

        LOGGER.debug("Namespaces list %s", namespaces_list)
        return namespaces_list

    def api_client(self) -> ApiClient:
        if self._api_client is not None:
            return self._api_client

        config.load_incluster_config()
        return ApiClient()


adjectives = [
    "altered",
    "angry",
    "big",
    "blinking",
    "boring",
    "broken",
    "bubbling",
    "calculating",
    "cute",
    "diffing",
    "expensive",
    "fresh",
    "fierce",
    "floating",
    "generous",
    "golden",
    "green",
    "growing",
    "hidden",
    "hideous",
    "interesting",
    "kubed",
    "mumbling",
    "rusty",
    "singing",
    "small",
    "sniffing",
    "squared",
    "talking",
    "trusty",
    "wise",
    "walking",
    "zooming",
]
nouns = [
    "ant",
    "bike",
    "bird",
    "captain",
    "cheese",
    "clock",
    "digit",
    "gorilla",
    "kraken",
    "number",
    "maven",
    "monitor",
    "moose",
    "moon",
    "mouse",
    "news",
    "newt",
    "octopus",
    "opossum",
    "otter",
    "paper",
    "passenger",
    "potato",
    "ship",
    "spaceship",
    "spaghetti",
    "spoon",
    "store",
    "tomcat",
    "trombone",
    "unicorn",
    "vine",
    "whale",
]


class MockKubernetesClient(KubernetesClient):
    def __init__(self, namespace_count: int = 50):
        super().__init__()

        self.namespace_count = namespace_count

    def get_namespaces(self) -> List[str]:
        """Generate a list of namespaces."""
        LOGGER.debug("Generating %d namespaces", self.namespace_count)

        return sorted(
            {
                "-".join(words)
                for words in random.choices(  # noqa: S311 no security needed here
                    list(itertools.product(adjectives, nouns)), k=self.namespace_count
                )
            }
        )
