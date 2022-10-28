import itertools
import random
from typing import List

import fastapi

router = fastapi.APIRouter()

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
    "golden",
    "green",
    "growing",
    "interesting",
    "kubed",
    "mumbling",
    "singing",
    "small",
    "sniffing",
    "squared",
    "talking",
    "walking",
    "zooming",
]
nouns = [
    "ant",
    "bike",
    "captain",
    "cheese",
    "clock",
    "gorilla",
    "kraken",
    "number",
    "maven",
    "monitor",
    "moose",
    "moon",
    "news",
    "paper",
    "passenger",
    "potato",
    "ship",
    "spaceship",
    "spoon",
    "store",
    "tomcat",
    "trombone",
]


@router.get("/namespaces")
def get_namespaces() -> List[str]:
    return sorted(
        {
            "-".join(words)
            for words in random.choices(  # noqa: S311 no security needed here
                list(itertools.product(adjectives, nouns)), k=120
            )
        }
    )
