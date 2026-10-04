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
from datetime import datetime, timezone, timedelta

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


# ── Order of the report sections (results page and PDF share this list) ───────────────────────
# Logical section keys:
#   summary   who you are at a glance (quick cards / profile summary page)
#   majors    majors to compare (high school) or exposure ideas (university): the "student track"
#   careers   suggested careers
#   plan      choose your direction, first step, 7-day plan and the months roadmap
#   path      progression / transition write-up (working professionals)
#   jobs      live job postings or internships
#   certs     certifications
#   courses   recommended courses
#   companies employers worth researching
#   ai        AI impact per career (the skills and practice exercise now live in the plan section)
#   profile   the detailed personality, values, strengths and work-style pages
# Rule: the summary and the person's own profile (interests, values, strengths, work style) come first, then what
# decides and what to do next (careers, plan), then what to do about it in the order that
# matters for that stage (learn / build for students, apply for graduates, transition for working users). The AI impact page sits right after the careers it is about (the results
# page shows it inside each career card instead, so it ignores the "ai" entry). Related sections sit next to each other:
# courses with certifications, jobs with companies.
# "companies" (Companies to Target) was removed from every order on 1 Oct 2026 (the company lists are limited and could
# mislead people). The section code is kept, just never listed here.
SECTION_ORDER = {
    "choosing_studies": ["summary", "profile", "majors", "careers", "ai", "plan", "courses"],
    "student":          ["summary", "profile", "careers", "ai", "plan", "courses", "certs", "majors", "jobs"],
    "graduate":         ["summary", "profile", "careers", "ai", "plan", "jobs", "certs", "courses"],
    "next_move":        ["summary", "profile", "careers", "ai", "plan", "path", "jobs", "courses"],
    "default":          ["summary", "profile", "careers", "ai", "plan", "jobs", "courses"],
}

def section_order(current_stage: str | None) -> list[str]:
    if current_stage in MAJORS_STAGES:
        return SECTION_ORDER["choosing_studies"]
    if current_stage in STILL_ENROLLED_STAGES:
        return SECTION_ORDER["student"]
    if current_stage in ENTERING_MARKET_STAGES:
        return SECTION_ORDER["graduate"]
    if current_stage in PROFESSIONAL_STAGES:
        return SECTION_ORDER["next_move"]
    return SECTION_ORDER["default"]

def should_show_entrepreneurship(career_structure: str | None) -> bool:
    """The entrepreneurship section is only meaningful for someone open to starting a business. A person who said they
    see their career as an employee (QO7 = 'employee') is auto-filled with placeholder answers for those questions
    (see SKIP_RULES in the assessment form), so showing scores and a narrative for them would be made-up content."""
    return career_structure != "employee"


# A direction the user types themselves (results page "choose your direction") ends up inside an AI prompt, so
# it is kept short, limited to ordinary name characters (letters in any script incl. Arabic, digits, spaces and a
# few punctuation marks), and passed through the same cultural-content filter as everything else.
_DIRECTION_ALLOWED = re.compile(r"^[\w\s&/,.'()+#-]+$", re.UNICODE)

# Profanity / slurs, English and Arabic. Kept apart from is_appropriate() (which filters job topics) because this
# one is only for text a person types about themselves. English uses whole-word matching so ordinary words
# ("cocktail", "assessment") never match; Arabic is matched token by token after normalising letter variants and
# stripping diacritics, so words such as "كسب" (earning) are safe.
_PROFANE_EN = re.compile(
    r"(?i)\b(?:fuck\w*|shit\w*|bitch\w*|cunt\w*|asshole\w*|bastard\w*|whore\w*|slut\w*|nigg\w+|fagg?ot\w*|"
    r"dicks?|cocks?|pussy|pussies|motherfuck\w*|wank\w*|twat\w*)\b"
)
_PROFANE_AR = {
    "كس", "كسم", "كسمك", "كسمه", "كسمها", "كسك", "كسها", "كسه", "كسختك", "كسامك", "طيز", "زب", "زبي", "زبر",
    "نيك", "نيكه", "نيكها", "منيوك", "منيوكه", "متناك", "متناكه", "شرموط", "شرموطه", "عاهر", "عاهره", "قحبه",
    "خرا", "خره", "عرص", "عرصه", "ديوث", "ابن الكلب", "ابن الحرام", "ولد الحرام", "ياحمار", "لعنه",
}
_AR_MARKS = re.compile("[\u0610-\u061A\u064B-\u065F\u0670\u0640]")

def _norm_ar(text: str) -> str:
    t = _AR_MARKS.sub("", text)
    return (t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي").replace("ة", "ه"))

def is_clean_text(text: str | None) -> bool:
    """False if typed text contains English or Arabic profanity."""
    if not text:
        return True
    if _PROFANE_EN.search(text):
        return False
    norm = _norm_ar(text)
    tokens = re.findall(r"[\u0600-\u06FF]+", norm)
    if any(t in _PROFANE_AR for t in tokens):
        return False
    joined = " ".join(tokens)
    return not any(" " in bad and bad in joined for bad in _PROFANE_AR)

# Anything typed under an "Other (type your own)" option (answers['<QID>_other']) can end up inside an AI prompt. It is
# cleaned once at submit (clean_typed_text) and again wherever it is read. Unlike clean_direction_label it does not
# reject ordinary sentence punctuation; it strips everything outside letters (any script), digits, spaces and a few
# punctuation marks, so quotes, brackets and other prompt-shaping characters never survive.
_TYPED_STRIP = re.compile(r"[^\w\sً-ٰٟ̀-ͯ&/,.'()+#!?:;\-]", re.UNICODE)

def clean_typed_text(text, max_len: int = 100) -> str | None:
    """Sanitised free text, or None if empty, too short, or it fails the content filters."""
    if not isinstance(text, str):
        return None
    t = re.sub(r"\s+", " ", _TYPED_STRIP.sub(" ", text)).strip()[:max_len].strip()
    if len(t) < 2 or not is_appropriate(t) or not is_clean_text(t):
        return None
    return t

def typed_other(answers, qid: str) -> str | None:
    """What the person typed for question `qid`, but only if they actually chose "other" there."""
    if not isinstance(answers, dict):
        return None
    chosen = answers.get(qid)
    if chosen != 'other' and not (isinstance(chosen, list) and 'other' in chosen):
        return None
    return clean_typed_text(answers.get(f'{qid}_other'))

def _with_english(terms: list, answers, key: str) -> list:
    """Typed terms plus the English version stored at submit (see report_generator.translate_typed_labels), if any."""
    en = clean_typed_text(answers.get(key), 60) if isinstance(answers, dict) and terms else None
    return terms + [en] if en and en not in terms else terms

def typed_terms(user_data: dict) -> dict:
    """Everything the person typed under an "Other" option, cleaned, for career matching: fields / sectors (lists,
    empty unless they chose "other" there) and goal / structure / stage (str or None)."""
    a = user_data.get('answers')
    return {
        'fields': _with_english([t for t in with_typed_other(['other'] if 'other' in (user_data.get('education_field') or []) else [], a, 'QO5_other')], a, 'QO5_other_en'),
        'sectors': _with_english([t for t in with_typed_other(['other'] if 'other' in (user_data.get('sectors_of_interest') or []) else [], a, 'QO6_other')], a, 'QO6_other_en'),
        'goal': typed_goal(a),
        'structure': typed_other(a, 'QO7'),
        'stage': typed_other(a, 'QO4') if user_data.get('current_stage') == 'other' else None,
    }

def stage_text(user_data: dict) -> str:
    """current_stage for AI prompts; a typed "other" stage is shown with what the person wrote."""
    stage = user_data.get('current_stage') or 'N/A'
    if stage == 'other':
        typed = typed_other(user_data.get('answers'), 'QO4')
        return f"other ({typed})" if typed else 'other'
    return stage

def typed_goal(answers) -> str | None:
    """The goal (QO5C / QO5C_PRO / QO5C_HS) in the person's own words, when they chose "Other"."""
    for qid in ('QO5C', 'QO5C_PRO', 'QO5C_HS'):
        t = typed_other(answers, qid)
        if t:
            return t
    return None

def with_typed_other(values, answers, answer_key: str) -> list[str]:
    """Selected option values with a bare 'other' replaced by what the user typed for it (answers[answer_key]).
    The typed text goes into AI prompts, so it is whitespace-collapsed, capped and run through the content
    filters; if it fails them, the 'other' entry is dropped rather than passed on."""
    out: list[str] = []
    for v in (values or []):
        if v != 'other':
            out.append(v)
            continue
        typed = clean_typed_text((answers or {}).get(answer_key), 60)
        if typed:
            out.append(typed)
    return out


def clean_direction_label(text: str | None) -> str | None:
    """Sanitised direction label, or None if it should be rejected."""
    if not isinstance(text, str):
        return None
    label = re.sub(r"\s+", " ", text).strip()
    if not (2 <= len(label) <= 80):
        return None
    if not _DIRECTION_ALLOWED.match(label):
        return None
    if not is_appropriate(label) or not is_clean_text(label):
        return None
    return label

def direction_key(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip().casefold()


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
    if target_country_code and not job_country and _names_only_other_gcc_country(job_title, job_description, target_country_code):
        return False
    return True

_GCC_COUNTRY_WORDS = {
    "SA": ("saudi", "riyadh", "jeddah", "dammam", "khobar"),
    "BH": ("bahrain", "manama"),
    "AE": ("uae", "emirates", "dubai", "abu dhabi", "sharjah"),
    "KW": ("kuwait",),
    "QA": ("qatar", "doha"),
    "OM": ("oman", "muscat"),
}

def _names_only_other_gcc_country(job_title: str | None, job_description: str | None, target_code: str) -> bool:
    """For a posting with no country field: True when its text points at a different GCC country and never mentions the
    target one (a Saudi posting returned for a Bahrain search). Postings that mention both are kept."""
    text = f"{job_title or ''} {(job_description or '')[:1500]}".lower()
    own = _GCC_COUNTRY_WORDS.get(target_code.upper(), ())
    if any(re.search(rf"\b{re.escape(w)}\b", text) for w in own):
        return False
    return any(re.search(rf"\b{re.escape(w)}\b", text)
               for code, words in _GCC_COUNTRY_WORDS.items() if code != target_code.upper() for w in words)


# Job source APIs return company-authored titles with no standard seniority
# field, so early-career users were getting management/director-level
# postings alongside genuine entry-level roles. Companies also label entry-level
# programs inconsistently (e.g. "Management Trainee", "Graduate Scheme"), so a
# title-only block on "manager"/"management" would wrongly hide real trainee
# programs — check the description too before excluding.
#
# "Early career" here is a current_stage (QO4) signal, not experience_level
# (QO3B) — QO3B only asks actual years of experience for people who have
# some, so it can't tell you "no experience yet" on its own. See
# ENTERING_MARKET_STAGES below.

# current_stage values (QO4) for users still enrolled in school/university —
# distinct from ENTERING_MARKET_STAGES below: a fresh grad who has already
# graduated (current_stage == "recent_graduate") should still see real
# entry-level jobs, not internships. Only these two stages get internship
# listings instead of the jobs section.
STILL_ENROLLED_STAGES = {"high_school", "university"}

# current_stage values for the other two practical tracks from the beta-
# strategy doc: "entering the market" (entry roles/certifications/employers)
# and "working professionals" (progression/transition). Entry roles and
# employers already exist (job listings + companies, unchanged); certifications
# and the progression/transition write-up are the net-new content per track.
ENTERING_MARKET_STAGES = {"recent_graduate"}
# "other" (QO4, typed by the person) is routed like the working / exploring stages: it needs the same job, career-path
# and company sections, and none of the student-only ones.
PROFESSIONAL_STAGES = {"working_exploring", "career_changer", "returning", "between_roles", "other"}

# Which results sections each kind of user sees (decided 29 Sept 2026):
#   high_school   -> majors to compare (+ the careers they lead to), courses, exposure ideas.
#                    No jobs, internships or company list.
#   university    -> courses, certifications (they have time to build credentials), internships,
#                    exposure ideas. No jobs, no company list, no majors comparison.
#   recent_graduate -> entry-level jobs + internships, certifications, companies, courses.
#   professionals -> jobs, career path (progression/transition), companies, courses. No majors.
MAJORS_STAGES = {"high_school"}

# People at the start of their path: school, university, recently graduated. For them the report shows what they can
# realistically reach in the next 5 to 10 years, so careers that sit at the very top of a ladder are left out.
EARLY_STAGES = STILL_ENROLLED_STAGES | ENTERING_MARKET_STAGES

# Careers a 16-year-old (or a student / new graduate) cannot plausibly be aiming at in 5 to 10 years: top executive,
# political and judicial posts, and roles that normally come after a long career or a lot of capital. Anything whose
# title carries an executive word (chief, director, head of, executive, principal, president, ambassador, diplomat,
# judge) is also treated this way, except the exceptions below, which people can begin working towards young.
LONG_HORIZON_TITLES = {
    "ceo", "ambassador", "diplomat", "judge", "hedge fund manager", "venture capitalist", "executive coach",
    "creative director", "school principal", "athletic director", "university professor", "franchise owner",
    "real estate developer",
}
_LONG_HORIZON_WORDS = re.compile(r"\b(chief|director|head of|executive|principal|president|vice president|ambassador|diplomat|judge)\b", re.I)
LONG_HORIZON_EXCEPTIONS = {"film director"}

def is_long_horizon_career(title: str | None) -> bool:
    t = (title or "").strip().lower()
    if not t or t in LONG_HORIZON_EXCEPTIONS:
        return False
    return t in LONG_HORIZON_TITLES or bool(_LONG_HORIZON_WORDS.search(t))

def filter_careers_for_stage(careers: list, current_stage: str | None) -> list:
    """Drops far-ahead careers for people at the start of their path; everyone else keeps the full list.
    If that would leave too few careers to rank, the list is returned unchanged."""
    if current_stage not in EARLY_STAGES:
        return careers
    kept = [c for c in careers if not is_long_horizon_career(c.get('title'))]
    return kept if len(kept) >= 10 else careers

# experience_level values that mean little or no paid work so far. These people get the same "reachable in 5 to 10
# years" treatment as students (no top-of-ladder posts) and no management titles, whatever their age or stage.
LOW_EXPERIENCE_LEVELS = {"no_experience", "up_to_1yr", "internships_only", "student", "fresh_grad"}
_MANAGER_TITLE = re.compile(r"\bmanager\b", re.I)
JUNIOR_EXCLUDED_TITLES = {"cloud architect"}   # "architect" is a degree profession elsewhere (Architect, Naval Architect...)

def is_junior_inappropriate(title: str | None) -> bool:
    """Management and senior-technical titles, which nobody with little or no experience is hired into."""
    t = (title or "").strip().lower()
    return bool(t) and (bool(_MANAGER_TITLE.search(t)) or t in JUNIOR_EXCLUDED_TITLES)

# Posts you are appointed to, not hired for: not something a career list can send a person towards.
APPOINTED_TITLES = {"ambassador"}

# Careers that need a specific licensed degree: (education_field, specialism area or None for any area of the field).
# Pharmacist and Surgeon share the same education_fields in the careers table, so the chosen area (QO5D) decides.
LICENSED_CAREERS = {
    "surgeon": ("medicine", "general_medicine"), "doctor": ("medicine", "general_medicine"),
    "psychiatrist": ("medicine", "general_medicine"), "radiologist": ("medicine", "general_medicine"),
    "dentist": ("medicine", "dentistry"), "pharmacist": ("medicine", "pharmacy"),
    "judge": ("law", None),
}

def lacks_required_degree(title: str | None, education_fields: list | None, specialisms: list | None) -> bool:
    """True when the person has studied something that rules out a licensed career (a pharmacist is not shown Surgeon,
    an engineer is not shown Dentist). If we cannot tell (nothing studied yet, 'other', no area chosen) it is kept."""
    req = LICENSED_CAREERS.get((title or "").strip().lower())
    if not req:
        return False
    field, area = req
    fields = {f for f in (education_fields or []) if f and f not in ("not_applicable", "other")}
    if not fields:
        return False
    if field not in fields:
        return True
    mine = [s for s in (specialisms or []) if s.startswith(field + ":")]
    return bool(area and mine and f"{field}: {area.replace('_', ' ')}" not in mine)
CERTIFICATION_STAGES = {"university", "recent_graduate"}
NO_LISTINGS_STAGES = {"high_school"}            # neither jobs nor internships
NO_COMPANIES_STAGES = STILL_ENROLLED_STAGES     # employer target list is for graduates and up

def resolve_route(current_stage: str | None) -> str:
    """Entry route (from the 28 Sept meeting guide) for a QO4 stage. Used by the results
    endpoint so the frontend/admin can label what a user is seeing."""
    if current_stage in MAJORS_STAGES:
        return "choosing_studies"
    if current_stage in STILL_ENROLLED_STAGES or current_stage in ENTERING_MARKET_STAGES:
        return "degree_to_career"
    if current_stage in PROFESSIONAL_STAGES:
        return "next_move"
    return "default"

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


def is_seniority_appropriate(job_title: str | None, job_description: str | None, is_early_career: bool) -> bool:
    """For early-career users (recent grads with no experience yet), exclude
    management/senior-level roles unless the listing's own text signals it's
    actually an entry-level program (e.g. a "management trainee" scheme) —
    company terminology for entry-level roles varies too much to filter on
    title alone."""
    if not is_early_career:
        return True
    text = f"{job_title or ''} {job_description or ''}".lower()
    if any(kw in text for kw in ENTRY_LEVEL_SIGNALS):
        return True
    return not any(kw in text for kw in SENIOR_LEVEL_KEYWORDS)


# ── Freshness and requirements of a live listing (JSearch fields) ─────────────
# Every field used here is optional in the API response: a listing that does not carry a date or
# requirement data is kept (unknown is not a reason to hide a job), only listings that clearly do
# not fit are dropped.

MAX_JOB_AGE_DAYS = 60
EDUCATION_RANK = {"high_school": 1, "associates": 2, "bachelors": 3, "postgraduate": 4}
# Highest experience (months) we still show to someone at the start of their career / to an intern.
MAX_EXPERIENCE_MONTHS_EARLY_CAREER = 36
MAX_EXPERIENCE_MONTHS_INTERNSHIP = 12


def _parse_dt(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def job_posted_date(job: dict) -> str | None:
    """YYYY-MM-DD the listing was posted, or None if the API gave no usable date."""
    dt = _parse_dt(job.get("job_posted_at_datetime_utc"))
    return dt.date().isoformat() if dt else None


def is_job_fresh(job: dict, now: datetime | None = None) -> bool:
    """False for a listing posted more than MAX_JOB_AGE_DAYS ago or whose offer has already expired."""
    now = now or datetime.now(timezone.utc)
    posted = _parse_dt(job.get("job_posted_at_datetime_utc"))
    if posted and now - posted > timedelta(days=MAX_JOB_AGE_DAYS):
        return False
    expires = _parse_dt(job.get("job_offer_expiration_datetime_utc"))
    if expires and expires < now:
        return False
    return True


def job_requirements(job: dict) -> dict:
    """{'education': 'high_school'|'associates'|'bachelors'|'postgraduate'|None, 'experience_months': int|None}
    read from the listing's own structured fields. A postgraduate degree only counts as a requirement when the
    listing does not merely prefer it."""
    edu = job.get("job_required_education") if isinstance(job.get("job_required_education"), dict) else {}
    exp = job.get("job_required_experience") if isinstance(job.get("job_required_experience"), dict) else {}
    education = None
    if edu.get("postgraduate_degree") and not edu.get("degree_preferred"):
        education = "postgraduate"
    elif edu.get("bachelors_degree"):
        education = "bachelors"
    elif edu.get("associates_degree"):
        education = "associates"
    elif edu.get("high_school"):
        education = "high_school"
    months = None
    if exp.get("no_experience_required"):
        months = 0
    elif isinstance(exp.get("required_experience_in_months"), (int, float)):
        months = int(exp["required_experience_in_months"])
    return {"education": education, "experience_months": months}


def meets_requirements(req: dict, user_education_rank: int | None, max_experience_months: int | None) -> bool:
    """Drop a listing that asks for a higher education level than the user has (only when we know their level)
    or for more experience than a beginner can have (only when a cap applies)."""
    if user_education_rank is not None and req.get("education"):
        if EDUCATION_RANK[req["education"]] > user_education_rank:
            return False
    if max_experience_months is not None and req.get("experience_months") is not None:
        if req["experience_months"] > max_experience_months:
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


# ── Links for the "Majors & Exposure" ideas ─────────────────────────────────────────────────────────────────────
# The AI writes the names of activities and programmes but is never asked for web addresses (it would invent them).
# A name that matches a well-known programme below opens that programme's official site; everything else opens a web
# search for the name, which always works and never sends the user to a wrong page. Only http(s) URLs built here are
# ever returned.
OPPORTUNITY_SITES = [
    (r"aws educate|awseducate", "https://aws.amazon.com/education/awseducate/"),
    (r"google cloud skills boost|cloud skills boost", "https://www.cloudskillsboost.google/"),
    (r"microsoft learn", "https://learn.microsoft.com/training/"),
    (r"\bcoursera\b", "https://www.coursera.org/"),
    (r"\bedx\b", "https://www.edx.org/"),
    (r"khan academy", "https://www.khanacademy.org/"),
    (r"google career certificates?|grow with google", "https://grow.google/certificates/"),
    (r"cisco networking academy|netacad", "https://www.netacad.com/"),
    (r"hubspot academy", "https://academy.hubspot.com/"),
    (r"\bkaggle\b", "https://www.kaggle.com/"),
    (r"mit opencourseware", "https://ocw.mit.edu/"),
]

def _search_url(query: str) -> str:
    from urllib.parse import quote_plus
    return "https://www.google.com/search?q=" + quote_plus(re.sub(r"\s+", " ", query).strip()[:200])

def opportunity_link(title: str | None) -> dict | None:
    """{'url', 'kind'} for an exposure idea: 'site' for a known programme, otherwise 'search'."""
    if not isinstance(title, str) or not title.strip():
        return None
    low = title.lower()
    for pattern, url in OPPORTUNITY_SITES:
        if re.search(pattern, low):
            return {"url": url, "kind": "site"}
    return {"url": _search_url(title), "kind": "search"}

def major_link(name: str | None) -> dict | None:
    """A web search for degree programmes in a major (the AI names general fields, never specific programmes)."""
    if not isinstance(name, str) or not name.strip():
        return None
    return {"url": _search_url(f"{name} degree programs universities"), "kind": "search"}

def add_student_track_links(track: dict | None) -> dict | None:
    """Copy of a student track with a `link` on each exposure idea and major. Added on the way out, never cached, so
    changes to the known-programme list apply to existing reports."""
    if not isinstance(track, dict) or not track:
        return track
    out = dict(track)
    if isinstance(track.get("exposure_ideas"), list):
        out["exposure_ideas"] = [
            {**i, "link": opportunity_link(i.get("title"))} if isinstance(i, dict) else i for i in track["exposure_ideas"]
        ]
    if isinstance(track.get("majors"), list):
        out["majors"] = [
            {**m, "link": major_link(m.get("name"))} if isinstance(m, dict) else m for m in track["majors"]
        ]
    return out


# Careers that match below this are not worth a card: a weak match on the page only makes the report longer and the
# list less believable. At least MIN_CAREERS_SHOWN are always kept (best first, in the order given) so a person with
# unusual answers never ends up with an empty list.
MIN_MATCH_SHOWN = 60
MIN_CAREERS_SHOWN = 3

def drop_weak_matches(recs: list) -> list:
    recs = list(recs or [])
    def score(r):
        try:
            return float(r.get("match_score")) if isinstance(r, dict) and r.get("match_score") is not None else None
        except (TypeError, ValueError):
            return None
    strong = [r for r in recs if (score(r) is None or score(r) >= MIN_MATCH_SHOWN)]
    return strong if len(strong) >= MIN_CAREERS_SHOWN else recs[:max(MIN_CAREERS_SHOWN, len(strong))]
