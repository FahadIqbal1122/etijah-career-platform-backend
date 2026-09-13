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


# Job source APIs return company-authored titles with no standard seniority
# field, so "student"/"fresh_grad" users were getting management/director-level
# postings alongside genuine entry-level roles. Companies also label entry-level
# programs inconsistently (e.g. "Management Trainee", "Graduate Scheme"), so a
# title-only block on "manager"/"management" would wrongly hide real trainee
# programs — check the description too before excluding.
STUDENT_EXPERIENCE_LEVELS = {"student", "fresh_grad"}

# current_stage values (QO4) for users still enrolled in school/university —
# distinct from experience_level: a fresh_grad who has already graduated
# (current_stage == "recent_graduate") should still see real entry-level jobs,
# not internships. Only these two stages get internship listings instead of
# the jobs section.
STILL_ENROLLED_STAGES = {"high_school", "university"}

SENIOR_LEVEL_KEYWORDS = [
    "senior", "sr.", "manager", "director", "head of", "chief", "vp ",
    "vice president", "principal", "executive", "president",
    "general manager", "department head", "supervisor", "team lead",
]

ENTRY_LEVEL_SIGNALS = [
    "entry level", "entry-level", "intern", "internship", "trainee",
    "apprentice", "apprenticeship", "graduate program", "graduate scheme",
    "graduate trainee", "new grad", "fresh graduate", "no experience",
    "0-1 year", "junior", "management trainee",
]


def is_seniority_appropriate(job_title: str | None, job_description: str | None, experience_level: str | None) -> bool:
    """For students/fresh grads, exclude management/senior-level roles unless
    the listing's own text signals it's actually an entry-level program (e.g.
    a "management trainee" scheme) — company terminology for entry-level roles
    varies too much to filter on title alone."""
    if experience_level not in STUDENT_EXPERIENCE_LEVELS:
        return True
    text = f"{job_title or ''} {job_description or ''}".lower()
    if any(kw in text for kw in ENTRY_LEVEL_SIGNALS):
        return True
    return not any(kw in text for kw in SENIOR_LEVEL_KEYWORDS)


CULTURAL_GUARDRAIL = (
    "Cultural guardrail: this platform serves an Arab/Muslim audience in the GCC. "
    "Never recommend or favorably reference careers, roles, or employers tied to "
    "non-Islamic religious institutions/clergy (e.g. church, pastor, priest, "
    "synagogue, temple), alcohol (bars, breweries, wineries), gambling (casinos, "
    "betting), or adult entertainment. If a matched career title could read that "
    "way, reframe it toward the closest culturally appropriate equivalent instead."
)
