const adjectives = [
    "altered", "angry", "big", "blinking", "boring", "broken", "bubbling", "calculating",
    "cute", "diffing", "expensive", "fresh", "fierce", "floating", "generous", "golden",
    "green", "growing", "hidden", "hideous", "interesting", "kubed", "mumbling", "rusty",
    "singing", "small", "sniffing", "squared", "talking", "trusty", "wise", "walking", "zooming"
];

const nouns = [
    "ant", "bike", "bird", "captain", "cheese", "clock", "digit", "gorilla", "kraken", "number",
    "maven", "monitor", "moose", "moon", "mouse", "news", "newt", "octopus", "opossum", "otter",
    "paper", "passenger", "potato", "ship", "spaceship", "spaghetti", "spoon", "store", "tomcat",
    "trombone", "unicorn", "vine", "whale"
];

export function mockNamespacesResolver(count) {
    const randomPairs = new Set();
    while (randomPairs.size < count) {
        const adjective = adjectives[Math.floor(Math.random() * adjectives.length)];
        const noun = nouns[Math.floor(Math.random() * nouns.length)];
        randomPairs.add(`${adjective}-${noun}`);
    }
    return Array.from(randomPairs).sort();
}
