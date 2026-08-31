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


# JSearch's `country` param only biases results toward a region; it can still
# return jobs that require a citizenship/clearance the user won't have, or
# that land outside the requested country entirely. This is a second-pass
# filter over the job's own returned fields.
CITIZENSHIP_KEYWORDS = [
    'us citizenship', 'u.s. citizenship', 'must be a us citizen', 'must be a u.s. citizen',
    'security clearance', 'secret clearance', 'top secret clearance',
    'citizenship required', 'authorized to work in the united states',
    'green card', 'permanent resident of the united states',
]


def is_region_eligible(job_title: str | None, job_description: str | None, job_country: str | None, target_country_code: str | None) -> bool:
    """Rejects jobs that require citizenship/clearance the user won't have,
    or whose location is outside the user's target country when known."""
    text = f"{job_title or ''} {job_description or ''}".lower()
    if any(kw in text for kw in CITIZENSHIP_KEYWORDS):
        return False
    if target_country_code and job_country and job_country.upper() != target_country_code.upper():
        return False
    return True


CULTURAL_GUARDRAIL = (
    "Cultural guardrail: this platform serves an Arab/Muslim audience in the GCC. "
    "Never recommend or favorably reference careers, roles, or employers tied to "
    "non-Islamic religious institutions/clergy (e.g. church, pastor, priest, "
    "synagogue, temple), alcohol (bars, breweries, wineries), gambling (casinos, "
    "betting), or adult entertainment. If a matched career title could read that "
    "way, reframe it toward the closest culturally appropriate equivalent instead."
)
