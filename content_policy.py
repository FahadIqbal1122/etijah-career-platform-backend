"""
Cultural/religious content safety filter.

The platform serves an Arab/Muslim GCC audience. No career, job listing, or
company suggestion should point users toward roles that conflict with Islamic
or Arab cultural values — e.g. clergy/ministry roles in other religions, or
roles inherently tied to alcohol, gambling, or adult entertainment. Live job
listings come from an open internet search (JSearch/RapidAPI) and are the
main exposure point, since that content isn't curated by us.
"""

import re

DISALLOWED_KEYWORDS = [
    # Non-Islamic religious institutions / clergy
    "church", "cathedral", "parish", "pastor", "priest", "reverend",
    "minister of religion", "youth minister", "clergy", "clergyman",
    "rabbi", "synagogue", "temple priest", "monastery", "monk", "nun",
    "diocese", "congregation", "missionary", "evangelist", "chaplain",
    "worship leader", "choir director",
    # Alcohol
    "bartender", "brewery", "brewer", "winery", "wine maker", "sommelier",
    "distillery", "liquor", "off-licence", "off-license", "pub",
    # Gambling
    "casino", "betting shop", "gambling", "bookmaker", "lottery agent",
    "poker dealer", "croupier",
    # Adult entertainment
    "strip club", "adult entertainment", "escort service",
]

_PATTERN = re.compile(
    r"(?i)\b(" + "|".join(re.escape(k.strip()) for k in DISALLOWED_KEYWORDS) + r")\b"
)


def is_appropriate(*fields: str | None) -> bool:
    """True if none of the given text fields trip the disallowed-content filter."""
    text = " ".join(f for f in fields if f)
    return not _PATTERN.search(text)


CULTURAL_GUARDRAIL = (
    "Cultural guardrail: this platform serves an Arab/Muslim audience in the GCC. "
    "Never recommend or favorably reference careers, roles, or employers tied to "
    "non-Islamic religious institutions/clergy (e.g. church, pastor, priest, "
    "synagogue, temple), alcohol (bars, breweries, wineries), gambling (casinos, "
    "betting), or adult entertainment. If a matched career title could read that "
    "way, reframe it toward the closest culturally appropriate equivalent instead."
)
