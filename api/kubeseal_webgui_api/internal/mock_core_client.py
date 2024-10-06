import itertools
import random
from typing import List

from kubernetes import client

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


def generate_namespaces(count) -> List[str]:
    return sorted(
        {
            "-".join(words)
            for words in random.choices(  # noqa: S311 no security needed here
                list(itertools.product(adjectives, nouns)), k=count
            )
        }
    )


class MockCoreClient:
    def __init__(self, namespace_count: int = 200):
        self.__namespace_count = namespace_count

    @staticmethod
    def __str__() -> str:
        return "mock"

    @staticmethod
    def create_v1_namespace(name: str):
        """Simple V1Namespace object factory"""
        meta = client.V1ObjectMeta(name=name)

        return client.V1Namespace(
            api_version="v1",
            kind="Namespace",
            metadata=meta,
        )

    @staticmethod
    def create_v1_pod(name: str, namespace: str):
        """Simple V1Pod object factory"""
        meta = client.V1ObjectMeta(name=name, namespace=namespace)

        return client.V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=meta,
        )

    def list_pod_for_all_namespaces(self, *args, **kwargs) -> List:
        namespaces = generate_namespaces(self.__namespace_count)
        items = []
        for ns in namespaces:
            items.append(self.create_v1_pod("mock", ns))

        return client.V1PodList(
            api_version="v1",
            kind="PodList",
            items=items,
        )

    def list_namespace(self, *args, **kwargs) -> List:
        items = map(
            self.create_v1_namespace, generate_namespaces(self.__namespace_count)
        )
        return client.V1NamespaceList(
            api_version="v1",
            kind="NamespaceList",
            items=items,
        )
