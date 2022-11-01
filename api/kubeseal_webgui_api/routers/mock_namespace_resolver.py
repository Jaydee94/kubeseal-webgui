import itertools
import random
from typing import List

from kubeseal_webgui_api.app_config import settings

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


def mock_namespaces_resolver() -> List[str]:
    count = settings.mock_namespace_count
    return sorted(
        {
            "-".join(words)
            for words in random.choices(  # noqa: S311 no security needed here
                list(itertools.product(adjectives, nouns)), k=count
            )
        }
    )
