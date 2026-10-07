from http import HTTPStatus
import os
import re
from threading import _profile_hook
from fastapi import FastAPI, HTTPException, Depends, Security, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from scoring_engine import compute_scores, build_framework_output, score_careers, get_career_semantic_scores, extract_specialisms, enrich_profile, recommend_courses, COUNTRY_CODE_MAP, COUNTRY_NAMES
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Any, Literal
import io
from datetime import datetime, timezone, timedelta
from collections import Counter
from fastapi.responses import StreamingResponse
from report_generator import create_report, _execute_with_retry, WRITING_RULES
from db_client import disable_http2
from google.api_core.exceptions import GoogleAPICallError
from requests.exceptions import RequestException
from smtp_service import send_report_email, send_feedback_email, send_results_ready_email, send_beta_feedback_email, invalidate_smtp_cache, send_failure_alert, render_template, send_email, ADMIN_ALERT_EMAIL
import httpx, hmac, hashlib, json, secrets, time
from coaching_methodology import METHODOLOGY_DOC
from coaching_pipeline import chunk_transcript, embed_and_store_chunks, client, embed_country_profile, sync_country_profile_embedding, sync_career_embedding, _gemini_embed
from content_policy import drop_weak_matches, add_student_track_links, section_order, job_posted_date, is_job_fresh, job_requirements as parse_job_requirements, meets_requirements, MAX_EXPERIENCE_MONTHS_EARLY_CAREER, MAX_EXPERIENCE_MONTHS_INTERNSHIP, EDUCATION_RANK, clean_typed_text, clean_direction_label, direction_key, resolve_route, MAJORS_STAGES, CERTIFICATION_STAGES, NO_LISTINGS_STAGES, NO_COMPANIES_STAGES, is_appropriate, is_region_eligible, is_seniority_appropriate, STILL_ENROLLED_STAGES, ENTERING_MARKET_STAGES, PROFESSIONAL_STAGES, CULTURAL_GUARDRAIL
import coach_chat as coach_chat_mod
from ai_provider import get_ai_provider, invalidate_ai_provider_cache, AI_PROVIDER_KEY, VALID_PROVIDERS

load_dotenv()

app = FastAPI()

import traceback
from fastapi.responses import JSONResponse
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class CatchAllMiddleware(BaseHTTPMiddleware):
    """Catches unhandled exceptions from inside the CORS layer (registered before
    CORSMiddleware below, so it wraps closer to the router). A handler registered
    via @app.exception_handler(Exception) instead gets promoted by Starlette into
    ServerErrorMiddleware, which sits *outside* CORSMiddleware — its 500 responses
    never get an Access-Control-Allow-Origin header, so the browser can't read them
    and reports a generic "Failed to fetch" instead of the actual error."""
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            # A lookup of an id that does not exist (0 rows, PGRST116) or is not a valid UUID (22P02) is the
            # caller's mistake (an old link, a typo, a probe), not a server fault: answer 404 and keep it out of
            # the admin Bugs tab, which is for real faults.
            if getattr(e, "code", None) in ("PGRST116", "22P02"):
                return JSONResponse(status_code=404, content={"detail": "No results found for this response"})
            traceback.print_exc()
            # Best-effort: these are uncaught 500s that bypass send_failure_alert
            # entirely (no @app-level try/except reported them), so without this
            # they'd only ever show up in server logs, never in the admin Bugs tab.
            try:
                supabase.table("bug_reports").insert({
                    "source": "system",
                    "feature": "unhandled_exception",
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:2000],
                    "stack_trace": traceback.format_exc()[:8000],
                    "page": request.url.path,
                    "description": f"{request.method} {request.url.path}",
                }).execute()
            except Exception:
                pass
            return JSONResponse(status_code=500, content={"error": "Internal server error"})


app.add_middleware(CatchAllMiddleware)
from request_guard import RequestGuardMiddleware, client_ip as _client_ip
app.add_middleware(RequestGuardMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://myetijahi.com",
        "https://www.myetijahi.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase: Client = disable_http2(create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
))

HUB_API_KEY = os.getenv("HUB_API_KEY")
SHOP_BASE_URL = os.getenv("SHOP_BASE_URL", "https://shop.etijahcoaching.com")
ACADEMY_BASE_URL = os.getenv("ACADEMY_BASE_URL", "https://academy.etijahcoaching.com")
BILLING_RETURN_URL = "https://myetijahi.com/account/billing"

META_PIXEL_ID = os.getenv("META_PIXEL_ID")          # "dataset ID" — same as your Pixel ID
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_TEST_EVENT_CODE = os.getenv("META_TEST_EVENT_CODE")  # optional, only while testing in Events Manager

INTERNAL_JOBS_KEY = os.getenv("INTERNAL_JOBS_KEY")
DASHBOARD_SHARE_TOKEN = os.getenv("DASHBOARD_SHARE_TOKEN")

PLAN_CATALOG = {
    "pathfinder":        {"name": "Pathfinder",        "amount": 59,  "currency": "SAR", "interval": "lifetime", "extension_days": None, "available": True},
    # One-time payment: Pathfinder plus a 1:1 coaching session (enabled 4 Oct 2026); 365 days of Launchpad status (no renewal). Code kept as launchpad_monthly so the
    # landing page, api.ts PlanCode type and dashboard ?buy= handling keep working.
    "launchpad_monthly": {"name": "Launchpad",          "amount": 330, "currency": "SAR", "interval": "one_time", "extension_days": 365,  "available": True},
    # "launchpad_yearly":  {"name": "Launchpad Yearly",   "amount": 799, "currency": "SAR", "interval": "year",     "extension_days": 365,  "available": False},
}

# Payment testing: set PATHFINDER_TEST_AMOUNT (for example 0.1) and PATHFINDER_TEST_CURRENCY (for example BHD) in the
# server environment to charge that for Pathfinder AND Launchpad instead of the real prices, and remove both when done.
# Nothing in the code changes, so the real prices can never ship by accident. Everyone checking out while these are
# set pays the test price.
_test_amount = os.getenv("PATHFINDER_TEST_AMOUNT")
if _test_amount:
    try:
        for _code in ("pathfinder", "launchpad_monthly"):
            PLAN_CATALOG[_code] = {**PLAN_CATALOG[_code], "amount": float(_test_amount),
                                   "currency": (os.getenv("PATHFINDER_TEST_CURRENCY") or "BHD").upper()}
        print(f"WARNING: TEST price active for Pathfinder and Launchpad: {_test_amount} {(os.getenv('PATHFINDER_TEST_CURRENCY') or 'BHD').upper()}")
    except ValueError:
        print(f"Ignoring PATHFINDER_TEST_AMOUNT={_test_amount!r}: not a number")

# Local-currency prices for checkout, used only when the admin 'Multi-currency' switch is on (app_settings.multi_currency_enabled).
# The amount always comes from this table, never from the browser. Keep it in step with PRICES in the frontend's src/lib/pricing.ts.
# SAR is the base price in PLAN_CATALOG; anything not listed here is charged in SAR.
LOCAL_PRICES = {
    "pathfinder":        {"BHD": 6,  "QAR": 58,  "KWD": 5,  "OMR": 6,  "AED": 58,  "USD": 16},
    # "launchpad_monthly": {"BHD": 44, "QAR": 428, "KWD": 36, "OMR": 45, "AED": 431, "USD": 117},  # standard 440 SAR
    # launch offer 330 SAR
    "launchpad_monthly": {"BHD": 33, "QAR": 321, "KWD": 27, "OMR": 34, "AED": 323, "USD": 88},
}

# Launchpad for someone who already owns Pathfinder. The 330 SAR launch price is the package price (report + coaching bought
# together), so a Pathfinder owner who adds coaching later pays this instead. Keep in step with launchpad_upgrade in the
# frontend's src/lib/pricing.ts.
LAUNCHPAD_UPGRADE_SAR = 400
LAUNCHPAD_UPGRADE_LOCAL = {"BHD": 40, "QAR": 388, "KWD": 33, "OMR": 41, "AED": 392, "USD": 107}


def _owns_pathfinder(user_id: str) -> bool:
    """True when this user already bought Pathfinder (or Launchpad, which includes it) -- read from user_plans, not from
    get_effective_tier, so the admin test mode can't change what a buyer is charged."""
    try:
        row = supabase.table('user_plans').select('pathfinder_unlocked').eq('user_id', user_id).execute()
        return bool(row.data and row.data[0].get('pathfinder_unlocked'))
    except Exception as e:
        print("Pathfinder ownership check failed:", repr(e))
        return False


_bearer = HTTPBearer()
_bearer_optional = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(_bearer)):
    try:
        response = supabase.auth.get_user(credentials.credentials)
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or Expired token")

def get_optional_user(credentials: HTTPAuthorizationCredentials | None = Security(_bearer_optional)):
    if not credentials:
        return None
    # A present token means the caller believes they're logged in — treating
    # any failure as "anonymous" (the original behavior here) let a transient
    # network blip to Supabase Auth silently drop a real session, e.g. an
    # authenticated /assessment/submit quietly saving with no user_id and no
    # error shown. One retry filters that out; an actually invalid/expired
    # token still fails both times and correctly falls back to anonymous.
    for attempt in range(2):
        try:
            response = supabase.auth.get_user(credentials.credentials)
            return response.user if response.user else None
        except Exception:
            if attempt == 0:
                continue
            return None

def require_admin(user=Depends(get_current_user)):
    role = (user.app_metadata or {}).get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def _assert_can_view(owner_user_id: str | None, user):
    if not owner_user_id:
        return
    if not user:
        # No credentials at all — most commonly the frontend firing this call
        # before Supabase has finished hydrating a fresh session (right after
        # a redirect from submit/login). 401 lets the frontend's existing
        # retry-on-401 logic recover once the token is attached, unlike 404
        # which it treats as a genuine "doesn't exist" and never retries.
        raise HTTPException(status_code=401, detail="Sign in to view this response")
    if user.id != owner_user_id and (user.app_metadata or {}).get("role") != "admin":
        raise HTTPException(status_code=404, detail="No results found for this response")

def _assert_can_view_shared(owner_user_id: str | None, user):
    """Read-only report views open for anyone holding the link, so people can share their report.
    Safe because the response id is a random UUID (unguessable) and the owner's email is hidden
    from other viewers (see get_results). Anything that writes, emails or spends the owner's
    quota (feedback, building plans, emailing the report, force refresh) still uses
    _assert_can_view / _assert_can_force_refresh."""
    return

def _is_owner_or_admin(owner_user_id: str | None, user) -> bool:
    return bool(user) and (user.id == owner_user_id or (user.app_metadata or {}).get("role") == "admin")

def _is_admin(user) -> bool:
    return bool(user) and (user.app_metadata or {}).get("role") == "admin"

def _assert_can_force_refresh(owner_user_id: str | None, user):
    """force=true bypasses the cache and pays for a live LLM/API call — unlike a plain view,
    this must require the caller to be authenticated as the assessment's owner (or an admin),
    otherwise anyone who knows a public response_id could loop it to run up API costs. An
    unclaimed response (owner_user_id is None) has no legitimate owner to defer to, so only
    an admin — not just "any logged-in user" — may force-refresh it."""
    is_owner = bool(owner_user_id) and bool(user) and user.id == owner_user_id
    is_admin = bool(user) and (user.app_metadata or {}).get("role") == "admin"
    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Sign in as the report owner to refresh this data")

def _get_semantic_scores(response_id: str, summary: dict, profile_data: dict) -> dict:
    """get_career_semantic_scores() is a live Gemini embedding call — its input (the
    scored answers) never changes once a response is submitted, but career-suggestions,
    courses, and companies each called it fresh on every single request, so every
    "View report" click paid for 3 separate embedding calls with nothing to show for it
    on repeat views. Cached per response_id; never invalidated since the input is fixed."""
    cached = _execute_with_retry(supabase.table('assessment_responses')
        .select('career_semantic_scores_cache').eq('id', response_id).single())
    if cached.data and cached.data.get('career_semantic_scores_cache') is not None:
        return cached.data['career_semantic_scores_cache']

    # The embedding text includes the user's specific area of study (QO5D answers), which only lives
    # in the answers jsonb — fetch it here (cache miss only) rather than in every caller's select.
    embed_profile = dict(profile_data)
    if 'education_specialisms' not in embed_profile or 'answers' not in embed_profile:
        try:
            ans = _execute_with_retry(supabase.table('assessment_responses')
                .select('answers').eq('id', response_id).single())
            embed_profile['answers'] = (ans.data or {}).get('answers')
            embed_profile['education_specialisms'] = extract_specialisms((ans.data or {}).get('answers'), profile_data.get('education_field'))
        except Exception as e:
            print("Could not load specialisms for embedding (continuing without):", e)
    scores = get_career_semantic_scores(supabase, summary, embed_profile)
    if scores:
        _execute_with_retry(supabase.table('assessment_responses')
            .update({'career_semantic_scores_cache': scores}).eq('id', response_id))
    return scores

TEST_MODE_KEY = "test_mode_all_plans_unlocked"
_test_mode_cache: dict[str, Any] = {"value": False, "checked_at": None}
_TEST_MODE_CACHE_TTL = timedelta(seconds=10)

def _is_test_mode_enabled() -> bool:
    """Admin-togglable flag (app_settings.test_mode_all_plans_unlocked) that
    makes every user's effective tier resolve to 'launchpad', for QA/demo
    walkthroughs without a real purchase. Cached briefly so the per-request
    tier check in get_effective_tier doesn't add a DB round trip to every
    gated endpoint."""
    now = datetime.now(timezone.utc)
    if _test_mode_cache["checked_at"] and now - _test_mode_cache["checked_at"] < _TEST_MODE_CACHE_TTL:
        return _test_mode_cache["value"]
    try:
        row = supabase.table('app_settings').select('value').eq('key', TEST_MODE_KEY).execute()
        enabled = bool(row.data[0]['value']) if row.data else False
    except Exception as e:
        # app_settings may not exist yet (migration not applied) — fail safe to
        # "disabled" rather than taking down every gated endpoint that calls
        # get_effective_tier.
        print("Test mode lookup failed, defaulting to disabled:", e)
        enabled = False
    _test_mode_cache["value"] = enabled
    _test_mode_cache["checked_at"] = now
    return enabled

HOMEPAGE_MODE_KEY = "homepage_mode"
_homepage_mode_cache: dict[str, Any] = {"value": "landing", "checked_at": None}
_HOMEPAGE_MODE_CACHE_TTL = timedelta(seconds=10)

def _get_homepage_mode() -> str:
    """Admin-togglable flag (app_settings.homepage_mode) deciding which page
    serves as the site root: the marketing landing page or the pre-launch
    waitlist page. Cached briefly since it's read on every homepage request."""
    now = datetime.now(timezone.utc)
    if _homepage_mode_cache["checked_at"] and now - _homepage_mode_cache["checked_at"] < _HOMEPAGE_MODE_CACHE_TTL:
        return _homepage_mode_cache["value"]
    try:
        row = supabase.table('app_settings').select('value').eq('key', HOMEPAGE_MODE_KEY).execute()
        mode = row.data[0]['value'] if row.data and row.data[0]['value'] in ('landing', 'waitlist') else 'landing'
    except Exception as e:
        print("Homepage mode lookup failed, defaulting to landing:", e)
        mode = 'landing'
    _homepage_mode_cache["value"] = mode
    _homepage_mode_cache["checked_at"] = now
    return mode

MULTI_CURRENCY_KEY = "multi_currency_enabled"
_multi_currency_cache: dict[str, Any] = {"value": False, "checked_at": None}
_MULTI_CURRENCY_CACHE_TTL = timedelta(seconds=10)

def _is_multi_currency_enabled() -> bool:
    """Admin switch (app_settings.multi_currency_enabled). Off = prices shown and charged in SAR only; on = local
    currencies by visitor country. Defaults to off, including when the setting is missing or unreadable."""
    now = datetime.now(timezone.utc)
    if _multi_currency_cache["checked_at"] and now - _multi_currency_cache["checked_at"] < _MULTI_CURRENCY_CACHE_TTL:
        return _multi_currency_cache["value"]
    try:
        row = supabase.table('app_settings').select('value').eq('key', MULTI_CURRENCY_KEY).execute()
        enabled = row.data[0]['value'] is True if row.data else False
    except Exception as e:
        print("Multi-currency lookup failed, defaulting to off:", e)
        enabled = False
    _multi_currency_cache["value"] = enabled
    _multi_currency_cache["checked_at"] = now
    return enabled

DASHBOARD_SHARE_TOKEN_KEY = "dashboard_share_token"
_share_token_cache: dict[str, Any] = {"value": None, "checked_at": None}
_SHARE_TOKEN_CACHE_TTL = timedelta(seconds=10)

def _get_share_token() -> str | None:
    """Admin-regeneratable share token (app_settings.dashboard_share_token)
    gating the public read-only /public/dashboard-stats link. Falls back to
    the DASHBOARD_SHARE_TOKEN env var only when no DB value has been
    generated yet, so an already-deployed env-configured link keeps working
    until an admin explicitly regenerates it from the UI (which is also how
    a leaked link gets revoked — regenerating invalidates the old one)."""
    now = datetime.now(timezone.utc)
    if _share_token_cache["checked_at"] and now - _share_token_cache["checked_at"] < _SHARE_TOKEN_CACHE_TTL:
        return _share_token_cache["value"]
    token = DASHBOARD_SHARE_TOKEN
    try:
        row = supabase.table('app_settings').select('value').eq('key', DASHBOARD_SHARE_TOKEN_KEY).execute()
        if row.data and row.data[0]['value']:
            token = row.data[0]['value']
    except Exception as e:
        print("Share token lookup failed, using env fallback:", e)
    _share_token_cache["value"] = token
    _share_token_cache["checked_at"] = now
    return token

BETA_CLOSED_KEY = "beta_closed"
BETA_PREVIEW_SECRET_KEY = "beta_preview_secret"
_beta_cache: dict[str, Any] = {"closed": False, "secret": None, "checked_at": None}
_BETA_CACHE_TTL = timedelta(seconds=10)

def _beta_settings() -> tuple[bool, str | None]:
    """(closed, preview_secret) from app_settings, cached briefly. Fails open
    (not closed) if the lookup errors so a DB hiccup never blocks real users."""
    now = datetime.now(timezone.utc)
    if _beta_cache["checked_at"] and now - _beta_cache["checked_at"] < _BETA_CACHE_TTL:
        return _beta_cache["closed"], _beta_cache["secret"]
    closed, secret = False, None
    try:
        rows = supabase.table('app_settings').select('key,value').in_('key', [BETA_CLOSED_KEY, BETA_PREVIEW_SECRET_KEY]).execute()
        for r in rows.data or []:
            if r['key'] == BETA_CLOSED_KEY:
                closed = bool(r['value'])
            elif r['key'] == BETA_PREVIEW_SECRET_KEY:
                secret = r['value'] or None
    except Exception as e:
        print("Beta closed lookup failed, defaulting to open:", e)
    _beta_cache.update({"closed": closed, "secret": secret, "checked_at": now})
    return closed, secret

def _beta_preview_allowed(provided: str | None) -> bool:
    _, secret = _beta_settings()
    return bool(provided and secret and hmac.compare_digest(provided, secret))

def require_beta_open(request: Request):
    """Dependency for the endpoints that start a new assessment. While the beta is
    closed only requests carrying the tester preview secret get through."""
    closed, _ = _beta_settings()
    if closed and not _beta_preview_allowed(request.headers.get('x-beta-preview')):
        raise HTTPException(status_code=403, detail="beta_closed")

def get_effective_tier(user_id: str | None) -> str:
    """free | pathfinder | launchpad, computed from user_plans (not stored directly)."""
    if _is_test_mode_enabled():
        return "launchpad"
    if not user_id:
        return "free"
    row = supabase.table('user_plans').select('*').eq('user_id', user_id).execute()
    if not row.data:
        return "free"
    plan = row.data[0]
    sub_end = plan.get('subscription_current_period_end')
    subscription_active = bool(sub_end) and datetime.fromisoformat(sub_end) > datetime.now(timezone.utc)
    if subscription_active:
        return "launchpad"
    if plan.get('pathfinder_unlocked'):
        return "pathfinder"
    return "free"


class OnetLinkRequest(BaseModel):
    email: str
    onet_url: str
    label: str | None = None

class CheckExistingRequest(BaseModel):
    email: str
    phone: str

# Values the assessment can send as why_here (QO10 options, the goal-question options, and the fallbacks).
WHY_HERE_VALUES = {"choosing_study", "first_job", "career_change", "curious", "recommended", "other", "not_asked",
    "stay_in_field", "unsure_subject", "change_field", "not_sure", "choosing_major", "explore_careers"}

class SubmitRequest(BaseModel):
    full_name: str = Field(max_length=200)
    email: EmailStr
    phone: str = Field(max_length=40)
    country: str = Field(max_length=100)
    nationality: str = Field(max_length=100)
    age: int = Field(ge=10, le=100)
    experience_level: str = Field(max_length=50)
    # Constrained to QO4's exact option set: content_policy.py's stage-set
    # gating (STILL_ENROLLED_STAGES/ENTERING_MARKET_STAGES/PROFESSIONAL_STAGES)
    # and the AI prompts that interpolate this value both assume one of these
    # 7 known values — an arbitrary string would silently fail every stage
    # check (no track ever generated) rather than erroring loudly.
    current_stage: Literal["high_school", "university", "recent_graduate",
        "working_exploring", "career_changer", "returning", "between_roles", "other"]
    # Matches QO5's exact option set — also interpolated raw into LLM prompts
    # (student-track/certifications/ai-impact/ai-content), so constraining it
    # here closes that off as a prompt-injection surface, not just a length cap.
    education_field: list[Literal["business", "engineering", "computer_science", "medicine",
        "sciences", "humanities", "arts", "education", "law", "other", "not_applicable"]] = Field(max_length=2)
    # Whether the user's field of study (education_field) was their own choice —
    # relevant especially for Saudi users, where university placement is often
    # not a free choice. major_choice_reason is only meaningful when this is 'no'.
    major_was_own_choice: str | None = Field(default=None, max_length=10)
    major_choice_reason: str | None = Field(default=None, max_length=500)
    # Whether the user wants to stay close to education_field/current work, or
    # move into something different — used to weight the field-overlap scoring
    # in scoring_engine.score_careers() (see career_direction there).
    career_direction: Literal["stay_in_field", "change_field", "not_sure", "unsure_subject", "choosing_major", "explore_careers"] | None = None
    sectors_of_interest: list[str] = Field(max_length=50)
    career_structure: str = Field(max_length=200)
    languages: list[str] = Field(max_length=50)
    geographic_openness: str = Field(max_length=200)
    why_here: str = Field(max_length=2000)
    answers: dict[str, Any]
    completed: bool
    locale: str | None = 'en'
    # correlates this submission with any telemetry events sent while the
    # assessment was in progress (see /assessment/telemetry) — never a real
    # column on assessment_responses, so it's excluded before the RPC call.
    telemetry_session_id: str | None = Field(default=None, max_length=100)

APPLICATION_STATUSES = {"saved", "applied", "interview", "offer", "rejected"}

class ApplicationCreate(BaseModel):
    response_id: str | None = None
    job_title: str
    company: str | None = None
    location: str | None = None
    source: str | None = None
    url: str | None = None
    matched_career: str | None = None

class ApplicationUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None

class FeedbackRequest(BaseModel):
    fname: str
    email: EmailStr
    age: str
    country: str | None = None
    source: str | None = None
    accurate: str | None = None
    rating_careers: int | None = None
    rating_personality: int | None = None
    rating_clarity: int | None = None
    rating_length: int | None = None
    rating_overall: int | None = None
    surprised: str | None = None
    careers_relevant: str | None = None
    ai_outlook: str | None = None
    recommend: str | None = None
    other: str | None = None

class BugReportRequest(BaseModel):
    description: str = Field(min_length=1, max_length=3000)
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=200)
    response_id: str | None = Field(default=None, max_length=100)
    locale: str | None = Field(default=None, max_length=10)
    device_type: str | None = Field(default=None, max_length=20)
    page: str | None = Field(default=None, max_length=100)

class BugReportStatusUpdate(BaseModel):
    status: str

class BetaFeedbackStage1Request(BaseModel):
    response_id: str
    # Launch form (7 Oct 2026): Q1 understood, Q2 intent, Q3 confidence, Q4 length.
    # s1_clarity / s1_feeling were dropped from the form; the columns stay for the beta rows.
    # s1_clarity: int | None = Field(default=None, ge=1, le=5)
    # s1_feeling: int | None = Field(default=None, ge=1, le=5)
    s1_understood: int | None = Field(default=None, ge=1, le=5)
    # What the person wants from their results (confirm path / discover options /
    # choose a major / plan a change / get a job faster / understand AI impact) —
    # analytics-only, not wired into report generation since the report is already
    # being built by the time this loading-screen pulse fires.
    s1_intent: str | None = Field(default=None, max_length=100)
    s1_confidence: int | None = Field(default=None, ge=1, le=5)
    s1_length: str | None = Field(default=None, max_length=100)
    locale: str | None = Field(default=None, max_length=100)
    stage1_form_version: str | None = Field(default=None, max_length=100)

class BetaFeedbackStage2Request(BaseModel):
    """The follow-up form (launch doc stage 3A for free users, 3B for paid users; stored in the
    stage2_* columns the beta used). language_used/device are filled in silently by the frontend.
    Fields the beta form asked and the launch form does not (understood_after, career_explained,
    careers_seriously_considered, would_pay_at_price, pay_blockers, pay_blocker_priority,
    first_action_text, had_issues, issue_detail, worth_paying_for) are no longer accepted; their
    columns stay for the beta rows."""
    response_id: str
    language_used: str | None = Field(default=None, max_length=100)
    device: str | None = Field(default=None, max_length=100)
    felt_like_mentor: str | None = Field(default=None, max_length=100)          # Q9
    most_useful_part: str | None = Field(default=None, max_length=100)          # Q10
    ai_impact_changed_thinking: str | None = Field(default=None, max_length=100)  # Q11
    first_step: list[str] | None = Field(default=None, max_length=12)         # Q12 (free)
    wants_coach_session: str | None = Field(default=None, max_length=100)       # Q13
    would_recommend: str | None = Field(default=None, max_length=100)           # Q14
    arabic_natural: str | None = Field(default=None, max_length=100)            # Q15 (Arabic reports)
    purchase_blocker: str | None = Field(default=None, max_length=100)          # Q16 (free)
    pay_blocker_other_text: str | None = Field(default=None, max_length=2000)  # Q17 (free)
    overall_value: int | None = Field(default=None, ge=1, le=5)   # Q18 (paid)
    jobs_relevant: int | None = Field(default=None, ge=1, le=5)   # Q19 (paid)
    courses_useful: int | None = Field(default=None, ge=1, le=5)  # Q20 (paid)
    plan_would_follow: str | None = Field(default=None, max_length=100)         # Q21 (paid)
    least_useful_part: str | None = Field(default=None, max_length=100)         # Q22 (paid)
    missing_text: str | None = Field(default=None, max_length=2000)  # Q23 (paid)
    stage2_form_version: str | None = Field(default=None, max_length=100)

class BetaFeedbackResultStageRequest(BaseModel):
    response_id: str
    # Launch form: Q5 accuracy, Q6 understood why, Q7 careers they'd consider, Q8 optional note.
    result_accuracy: str | None = Field(default=None, max_length=100)
    career_explained: str | None = Field(default=None, max_length=100)
    careers_seriously_considered: str | None = Field(default=None, max_length=100)
    # would_recommend: str | None = None   # moved to the follow-up form (Q14)
    # would_pay: str | None = None         # dropped from the launch form
    other_text: str | None = Field(default=None, max_length=2000)
    result_stage_form_version: str | None = Field(default=None, max_length=100)
    locale: str | None = Field(default=None, max_length=100)

class WaitlistRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    country: str | None = None
    nationality: str | None = None
    phone: str | None = None
    status: str | None = None
    age: str | None = None
    locale: str | None = None
    source: str | None = None

class PartnerRequest(BaseModel):
    company_name: str
    contact_name: str
    email: EmailStr
    phone: str | None = None
    message: str | None = None
    locale: str | None = None
    source: str | None = None

WAITLIST_EVENT_TYPES = {"page_view", "click"}

class WaitlistEventRequest(BaseModel):
    event_type: str
    label: str | None = None
    locale: str | None = None
    source: str | None = None

class FeaturedCourseEventRequest(BaseModel):
    event_type: str            # 'view' | 'click'
    course_key: str
    response_id: str | None = None
    tier: str | None = None
    locale: str | None = None

TELEMETRY_EVENT_TYPES = {"session_start", "question_view", "break_open", "break_activity"}
# Generous but bounded — these are always short, code-generated values (a
# question id, an activity name), never free user input. Caps exist purely so
# an unauthenticated caller can't stuff arbitrarily large strings/JSON into
# the table (this endpoint takes no auth, matching /waitlist/events).
TELEMETRY_MAX_FIELD_LEN = 100
TELEMETRY_MAX_PAYLOAD_JSON_LEN = 2000

class TelemetryEventIn(BaseModel):
    event_type: str = Field(max_length=TELEMETRY_MAX_FIELD_LEN)
    question_id: str | None = Field(default=None, max_length=TELEMETRY_MAX_FIELD_LEN)
    activity_kind: str | None = Field(default=None, max_length=TELEMETRY_MAX_FIELD_LEN)
    duration_ms: int | None = Field(default=None, ge=0, le=24 * 60 * 60 * 1000)
    payload: dict[str, Any] | None = None

    @field_validator('payload')
    @classmethod
    def _bound_payload_size(cls, v):
        if v is not None and len(json.dumps(v)) > TELEMETRY_MAX_PAYLOAD_JSON_LEN:
            raise ValueError('payload too large')
        return v

class TelemetryBatchRequest(BaseModel):
    session_id: str = Field(max_length=TELEMETRY_MAX_FIELD_LEN)
    device_type: str | None = Field(default=None, max_length=TELEMETRY_MAX_FIELD_LEN)
    locale: str | None = Field(default=None, max_length=TELEMETRY_MAX_FIELD_LEN)
    events: list[TelemetryEventIn] = Field(max_length=50)

class coachingSessionRequest(BaseModel):
    client_label: str | None = None
    topic: str | None = None
    session_date: str | None = None #YYYY-MM-DD
    raw_transcript: str

class CoachRequest(BaseModel):
    message: str = Field(max_length=4000)
    conversation_history: list[dict] = Field(default_factory=list, max_length=50)

class CheckoutRequest(BaseModel):
    plan_code: str
    # Meta browser identifiers (the _fbp / _fbc cookies), passed through to the
    # server-side Purchase event to improve match quality.
    fbp: str | None = Field(default=None, max_length=200)
    fbc: str | None = Field(default=None, max_length=300)
    locale: str | None = Field(default=None, max_length=5)  # 'en' | 'ar': the page language the buyer paid from
    currency: str | None = Field(default=None, max_length=3)  # display currency the buyer saw; only used while multi-currency is on

class HubTransactionBody(BaseModel):
    external_user_id: str
    order_ref: str
    plan_code: str
    amount: float
    currency: str
    status: str
    tap_charge_id: str | None = None
    paid_at: str | None = None

@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/admin/submissions")
def get_submissions(_=Depends(require_admin)):
    data = supabase.table('assessment_responses') \
        .select('id, full_name, email, phone, country, nationality, age, age_bracket, experience_level, education_field, major_was_own_choice, major_choice_reason, career_direction, current_stage, completed, created_at, cohort_override') \
        .order('created_at', desc=True) \
        .execute()
    return data.data or []


@app.get("/admin/career-recommendations")
def get_all_career_recommendations(_=Depends(require_admin)):
    """One page listing every submission's AI-generated career_recommendations
    (title/match_score/fit_summary/growth_note), so an admin can review everything
    that's been generated without opening each submission individually. Reads
    whatever's already cached (paid or free-tier column) rather than generating on
    demand for rows that haven't been viewed/downloaded yet — bulk-generating for
    every submission here would be slow and costly just to render a list."""
    rows = supabase.table('assessment_responses') \
        .select('id, full_name, email, created_at, ai_content_cache, ai_content_cache_free') \
        .order('created_at', desc=True).execute()
    return [
        {
            "id": r["id"],
            "full_name": r.get("full_name"),
            "email": r.get("email"),
            "created_at": r.get("created_at"),
            "career_recommendations": ((r.get("ai_content_cache") or r.get("ai_content_cache_free")) or {}).get("career_recommendations") or [],
        }
        for r in (rows.data or [])
    ]


@app.post("/assessment/check-existing")
def check_existing(body: CheckExistingRequest, user=Depends(get_optional_user), _beta=Depends(require_beta_open)):
    result = supabase.rpc('check_existing_response', {
        'p_email': body.email,
        'p_phone': body.phone,
    }).execute()

    if not result.data:
        return None

    row = supabase.table('assessment_responses').select('user_id').eq('id', result.data).single().execute()
    owner_id = row.data.get('user_id') if row.data else None
    # Only tell the caller "this email already has an account, log in" when
    # it's actually someone else's account — otherwise a logged-in user
    # retaking their own assessment (QD2 pre-filled with their own email)
    # gets told to sign in while already signed in as that exact account.
    if owner_id and not (user and user.id == owner_id):
        return {"id": None, "claimed": True}

    return {"id": result.data}


@app.post("/assessment/submit")
def submit_assessment(body: SubmitRequest, background_tasks: BackgroundTasks, user=Depends(get_optional_user), _beta=Depends(require_beta_open)):
    # Score it first, before writing anything — a payload with no recognizable
    # question answers can't be scored, so reject cleanly instead of leaving
    # an orphaned response row with no results.
    # Optional "field you have in mind" (QOFIELD): keep only a cleaned label, drop it if it fails the checks. It
    # is never scored; it later feeds an AI prompt, so what is stored is the whitelisted, length-limited text.
    field_in_mind = clean_direction_label(body.answers.get('QOFIELD'))
    if field_in_mind:
        body.answers['QOFIELD'] = field_in_mind
    else:
        body.answers.pop('QOFIELD', None)
    # Text typed under any "Other (type your own)" option is cleaned once here, before it is stored, because it later
    # feeds AI prompts: unusable text (empty, profane, off-topic) is dropped rather than kept.
    for key in [k for k in body.answers if isinstance(k, str) and k.endswith('_other')]:
        cleaned = clean_typed_text(body.answers.get(key))
        if cleaned:
            body.answers[key] = cleaned
        else:
            body.answers.pop(key, None)
    # English twins of the typed texts that are in Arabic (QOFIELD_en, QO5_other_en, QO6_other_en): career matching compares
    # English words, so without them an Arabic "الطاقة" can never match "Energy Engineer". Anything the client sent under
    # these names is discarded first; the translation is best-effort and never blocks the submit.
    from report_generator import translate_typed_labels, TYPED_LABEL_KEYS
    for key in TYPED_LABEL_KEYS:
        body.answers.pop(f"{key}_en", None)
    try:
        for key, english in translate_typed_labels({k: body.answers.get(k) for k in TYPED_LABEL_KEYS}).items():
            body.answers[f"{key}_en"] = english
    except Exception as e:
        print("Typed-label translation failed (continuing without):", e)
    # why_here is printed in the report prompt; it only ever holds an option value, so anything else becomes 'other'.
    if body.why_here not in WHY_HERE_VALUES:
        body.why_here = 'other'
    results = compute_scores(body.answers)
    if not results:
        raise HTTPException(status_code=422, detail="No scoreable answers found in payload")
    summary = build_framework_output(results)

    # Save to DB — telemetry_session_id isn't a real column on
    # assessment_responses, it's only used below to link telemetry rows.
    result = supabase.rpc('insert_assessment_response', {
        'payload': body.model_dump(exclude={'telemetry_session_id'})
    }).execute()

    response_id = result.data
    if not response_id:
        raise HTTPException(status_code=500, detail="Failed to insert assessment response")

    if user:
        supabase.table('assessment_responses') \
            .update({'user_id': user.id}) \
            .eq('id', response_id).execute()

    # Best-effort: link any telemetry events sent during the assessment (device
    # type, break-panel plays, per-question pacing) to this submission. Never
    # allowed to fail the actual submit.
    if body.telemetry_session_id:
        try:
            supabase.table('assessment_telemetry_events') \
                .update({'response_id': response_id}) \
                .eq('session_id', body.telemetry_session_id).execute()
        except Exception as e:
            print("Failed to link telemetry events:", e)

    rows = [{**r, "response_id": response_id} for r in results]
    # Insert results
    supabase.table('assessment_results').upsert(rows, on_conflict='response_id,framework,dimension').execute()

    # requestWithRetry on the frontend (src/lib/api.ts) resubmits this exact request on a
    # dropped connection or a stray 401 — the RPC above has no idempotency key, so a retry
    # creates a second assessment_responses row. Without this guard that would queue both
    # post-submit emails a second time; skip them if an earlier row for the same email
    # already landed in the last few minutes (a genuine retake days later still gets emailed).
    recent_duplicate = supabase.table('assessment_responses') \
        .select('id') \
        .eq('email', body.email) \
        .neq('id', response_id) \
        .gte('created_at', (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()) \
        .limit(1).execute()

    if not recent_duplicate.data:
        # locale is free-text from the client (SubmitRequest.locale) — clamp it before it
        # becomes part of a URL embedded in an email, rather than trusting it verbatim.
        locale = body.locale if body.locale in ('en', 'ar') else 'en'
        frontend_base = os.getenv('FRONTEND_URL', '').rstrip('/')

        # ONE email per assessment: the results link plus the feedback form link (the stage-2 form, for everyone,
        # whether or not beta mode is on). The separate feedback emails below are disabled on purpose.
        results_template = supabase.table('email_templates').select('*').eq('key', 'results_ready').limit(1).execute()
        results_tmpl = results_template.data[0] if results_template.data else None
        if results_tmpl and results_tmpl.get('is_active'):
            results_url = f"{frontend_base}/{locale}/results/{response_id}"
            feedback_url = f"{frontend_base}/{locale}/beta-feedback/{response_id}"
            background_tasks.add_task(send_results_ready_email, body.email, body.full_name, results_url, locale, results_tmpl, supabase, feedback_url)

        # --- previous behaviour (two emails), kept for reference ---
        # results_template = supabase.table('email_templates').select('*').eq('key', 'results_ready').limit(1).execute()
        # results_tmpl = results_template.data[0] if results_template.data else None
        # if results_tmpl and results_tmpl.get('is_active'):
        #     results_url = f"{frontend_base}/{locale}/results/{response_id}"
        #     background_tasks.add_task(send_results_ready_email, body.email, body.full_name, results_url, locale, results_tmpl, supabase)

        # # Beta cohort gets the dedicated stage-2 feedback link instead of the
        # # generic feedback form — same email slot, different template/target.
        # if _is_test_mode_enabled():
        #     beta_feedback_template = supabase.table('email_templates').select('*').eq('key', 'beta_feedback_stage2').limit(1).execute()
        #     beta_feedback_tmpl = beta_feedback_template.data[0] if beta_feedback_template.data else None
        #     if beta_feedback_tmpl and beta_feedback_tmpl.get('is_active'):
        #         beta_feedback_url = f"{frontend_base}/{locale}/beta-feedback/{response_id}"
        #         beta_results_url = f"{frontend_base}/{locale}/results/{response_id}"
        #         beta_first_name = (body.full_name or '').strip().split(' ')[0]
        #         background_tasks.add_task(send_beta_feedback_email, body.email, beta_first_name, beta_feedback_url, locale, beta_feedback_tmpl, supabase, beta_results_url)
        # else:
        #     feedback_template = supabase.table('email_templates').select('*').eq('key', 'feedback_request').limit(1).execute()
        #     feedback_tmpl = feedback_template.data[0] if feedback_template.data else None
        #     if feedback_tmpl and feedback_tmpl.get('is_active'):
        #         feedback_url = f"{frontend_base}/{locale}/feedback"
        #         background_tasks.add_task(send_feedback_email, body.email, body.full_name, feedback_url, locale, feedback_tmpl, supabase)


    # Return summary
    return {"response_id": response_id, "summary": summary, "claim_token": _claim_token(str(response_id))}


@app.get("/assessment/{response_id}/answers")
def get_assessment_answers(response_id: str, _=Depends(require_admin)):
    """Raw per-question answers as submitted, keyed by question id (Q1, QO1, ...).
    Admin-only — lets staff compare a submission's actual answers against its
    scored results/AI content, which the question labels/options to render them
    against (src/data/questions.ts) already live on the frontend."""
    row = supabase.table('assessment_responses') \
        .select('answers') \
        .eq('id', response_id) \
        .single() \
        .execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Response not found")
    return {"answers": row.data.get('answers') or {}}


@app.post("/assessment/{response_id}/score")
def score_assessment(response_id:str, _=Depends(require_admin)):
    row = supabase.table('assessment_responses') \
        .select('answers') \
        .eq('id', response_id) \
        .single() \
        .execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Response not found")

    answers = row.data['answers']
    results = compute_scores(answers)
    summary = build_framework_output(results)

    rows_to_insert = [
        {**r, 'response_id': response_id}
        for r in results
    ]
    supabase.table('assessment_results').upsert(rows_to_insert, on_conflict='response_id,framework,dimension').execute()

    return {'scored': len(rows_to_insert), 'results': results, 'summary': summary}


@app.delete("/assessment/{response_id}")
def delete_assessment(response_id: str, _=Depends(require_admin)):
    # 1. Get the email first
    row = supabase.table('assessment_responses').select('email').eq('id', response_id).single().execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Not Found")

    email = row.data['email']

    # 2. Delete results
    supabase.table('assessment_results').delete().eq('response_id',response_id).execute()

    # 3. Delete onet link if exists
    if email:
        supabase.table('onet_links').delete().eq('email', email).execute()

    # Delete the response
    supabase.table('assessment_responses').delete().eq('id', response_id).execute()

    return {"deleted": response_id}
    

@app.get("/onet")
def get_onet_links(_=Depends(require_admin)):
    links = supabase.table('onet_links').select('*').order('created_at', desc=True).execute()
    emails = [l['email'] for l in links.data] if links.data else []
    assessment_emails = []
    name_map = {}
    if emails:
        responses = supabase.table('assessment_responses').select('email, full_name').in_('email', emails).eq('completed', True).execute()
        assessment_emails = [r['email'] for r in responses.data] if responses.data else []
        name_map = {r['email']: r['full_name'] for r in responses.data} if responses.data else {}
    result = [{**l, 'has_assessment': l['email'] in assessment_emails, 'name': name_map.get(l['email'])} for l in (links.data or [])]
    return result


@app.post("/onet")
def add_onet_link(body: OnetLinkRequest, _=Depends(require_admin)):
    data = supabase.table('onet_links').insert({
        'email': body.email.lower().strip(),
        'onet_url': body.onet_url,
        'label': body.label,
    }).execute()
    if not data.data:
        raise HTTPException(status_code=500, detail="Failed to insert onet link")
    return data.data[0]


@app.delete("/onet/{onet_id}")
def delete_onet_link(onet_id: str, _=Depends(require_admin)):
    supabase.table('onet_links').delete().eq('id', onet_id).execute()
    return {"deleted": onet_id}


@app.get("/stats/recent-completions")
def get_recent_completions():
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    result = supabase.table('assessment_responses') \
        .select('id', count='exact') \
        .eq('completed', True) \
        .gte('created_at', one_hour_ago) \
        .execute()
    return {"count": result.count or 0}


@app.get("/assessment/{response_id}/results")
def get_results(response_id: str, user=Depends(get_optional_user)):
    profile = _execute_with_retry(supabase.table('assessment_responses')
        .select('email, user_id, locale, current_stage')
        .eq('id', response_id).single())
    if not profile.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    _assert_can_view_shared(profile.data.get('user_id'), user)

    rows = _execute_with_retry(supabase.table('assessment_results')
        .select('*')
        .eq('response_id', response_id))
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found for this response")

    summary = build_framework_output(rows.data)
    tier = get_effective_tier(profile.data.get('user_id'))
    return {
        'results': rows.data, 'summary': summary,
        'email': profile.data.get('email') if (not profile.data.get('user_id') or _is_owner_or_admin(profile.data.get('user_id'), user)) else None,
        'tier': tier, 'locale': profile.data.get('locale') or 'en',
        'is_still_enrolled': profile.data.get('current_stage') in STILL_ENROLLED_STAGES,
        'route': resolve_route(profile.data.get('current_stage')),
        # Order of the report sections for this person (shared with the PDF; see content_policy.SECTION_ORDER).
        'section_order': section_order(profile.data.get('current_stage')),
        # Drives the beta feedback form on the frontend — only shown during the
        # beta window, distinct from a genuine paying launchpad tier.
        'beta_mode': _is_test_mode_enabled(),
    }

@app.get("/beta-feedback/{response_id}/riasec-summary")
def get_beta_feedback_riasec_summary(response_id: str):
    """Public, no-auth lookup of just the top RIASEC type — used to label the
    stage-2 beta feedback form ('you're an Investigator...'). The full
    /assessment/{id}/results endpoint requires the caller to be signed in as
    the response's owner (protecting the actual report), but the feedback
    link is sent to people who aren't expected to be logged in, so this
    endpoint intentionally skips that ownership check and returns nothing
    beyond the one label the page needs."""
    profile = _execute_with_retry(supabase.table('assessment_responses')
        .select('id')
        .eq('id', response_id).single())
    if not profile.data:
        raise HTTPException(status_code=404, detail="No results found for this response")

    rows = _execute_with_retry(supabase.table('assessment_results')
        .select('*')
        .eq('response_id', response_id))
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found for this response")

    summary = build_framework_output(rows.data)
    return {'top_type': (summary.get('riasec') or {}).get('top_types', [None])[0]}

@app.post("/feedback")
def submit_feedback(body: FeedbackRequest):
    result = supabase.table('feedback_responses').insert(body.model_dump()).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to insert feedback")
    return {"id": result.data[0]["id"]}

@app.get("/admin/feedback")
def get_feedback(_=Depends(require_admin)):
    data = supabase.table('feedback_responses') \
        .select('*') \
        .order('created_at', desc=True) \
        .execute()
    return data.data or []

@app.post("/bug-report")
def submit_bug_report(body: BugReportRequest, request: Request):
    row = body.model_dump()
    row['source'] = 'user'
    row['user_agent'] = request.headers.get('user-agent', '')[:500] or None
    result = supabase.table('bug_reports').insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to insert bug report")
    return {"id": result.data[0]["id"]}

@app.get("/admin/bug-reports")
def get_bug_reports(_=Depends(require_admin)):
    data = supabase.table('bug_reports') \
        .select('*') \
        .order('created_at', desc=True) \
        .execute()
    return data.data or []

@app.patch("/admin/bug-reports/{bug_id}")
def update_bug_report_status(bug_id: str, body: BugReportStatusUpdate, _=Depends(require_admin)):
    if body.status not in ('open', 'resolved'):
        raise HTTPException(status_code=400, detail="status must be 'open' or 'resolved'")
    result = supabase.table('bug_reports').update({'status': body.status}).eq('id', bug_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Bug report not found")
    return {"ok": True}

@app.post("/beta-feedback/stage1")
def submit_beta_feedback_stage1(body: BetaFeedbackStage1Request, user=Depends(get_optional_user)):
    row = body.model_dump(exclude={'response_id'}, exclude_none=True)
    row['response_id'] = body.response_id
    if user:   # a later anonymous save (link opened signed out) must not unlink the account
        row['user_id'] = user.id
    row['plan_tier'] = _feedback_plan_tier(body.response_id)
    if all(row.get(k) is not None for k in ('s1_understood', 's1_intent', 's1_confidence', 's1_length')):
        row['stage1_completed_at'] = datetime.now(timezone.utc).isoformat()
    result = supabase.table('beta_feedback').upsert(row, on_conflict='response_id').execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    return {"ok": True}

@app.post("/beta-feedback/result-stage")
def submit_beta_feedback_result_stage(body: BetaFeedbackResultStageRequest, user=Depends(get_optional_user)):
    """Shown on the results page itself (never gating): accuracy, whether each career's
    reason was understood, how many careers they'd consider, and an optional note —
    asked right after someone has seen their report."""
    row = body.model_dump(exclude={'response_id'}, exclude_none=True)
    row['response_id'] = body.response_id
    if user:   # a later anonymous save (link opened signed out) must not unlink the account
        row['user_id'] = user.id
    row['plan_tier'] = _feedback_plan_tier(body.response_id)
    if all(row.get(k) is not None for k in ('result_accuracy', 'career_explained', 'careers_seriously_considered')):
        row['result_stage_completed_at'] = datetime.now(timezone.utc).isoformat()
    result = supabase.table('beta_feedback').upsert(row, on_conflict='response_id').execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    return {"ok": True}

def _feedback_plan_tier(response_id: str) -> str:
    """'paid' when the person who took this assessment has bought Pathfinder or Launchpad, else
    'free'. Reads user_plans (real purchases) rather than get_effective_tier, which admin test
    mode inflates to launchpad. Stamped on every feedback save; the last save wins, so a free
    user who buys later is tagged paid on their next answer."""
    try:
        row = supabase.table('assessment_responses').select('user_id').eq('id', response_id).limit(1).execute()
        user_id = row.data[0].get('user_id') if row.data else None
        return 'paid' if user_id and _owns_pathfinder(user_id) else 'free'
    except Exception as e:
        print("Feedback plan tier lookup failed:", repr(e))
        return 'free'

@app.get("/beta-feedback/{response_id}/context")
def get_beta_feedback_context(response_id: str):
    """Public (the follow-up link is opened from email, often signed out). Tells the follow-up
    form which variant to show and which conditional questions apply: free vs paid, the language
    of the report (Q15 is Arabic-only), and whether a free user opened the AI Impact preview (Q11)."""
    profile = supabase.table('assessment_responses').select('locale').eq('id', response_id).limit(1).execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    fb = supabase.table('beta_feedback').select('opened_ai_impact').eq('response_id', response_id).limit(1).execute()
    return {
        'plan_tier': _feedback_plan_tier(response_id),
        'report_locale': 'ar' if profile.data[0].get('locale') == 'ar' else 'en',
        'opened_ai_impact': bool(fb.data and fb.data[0].get('opened_ai_impact')),
    }

@app.post("/beta-feedback/{response_id}/ai-impact-opened")
def mark_ai_impact_opened(response_id: str):
    """The results page calls this the first time a reader expands an AI Impact row; it decides
    whether the free follow-up asks Q11. Only ever sets a flag."""
    known = supabase.table('assessment_responses').select('id').eq('id', response_id).limit(1).execute()
    if not known.data:   # no stray rows for ids that are not real responses
        raise HTTPException(status_code=404, detail="No results found for this response")
    supabase.table('beta_feedback').upsert(
        {'response_id': response_id, 'opened_ai_impact': True}, on_conflict='response_id').execute()
    return {"ok": True}

@app.get("/beta-feedback/{response_id}/status")
def get_beta_feedback_status(response_id: str, user=Depends(get_optional_user)):
    existing = supabase.table('beta_feedback') \
        .select('stage1_completed_at, result_stage_completed_at, stage2_completed_at') \
        .eq('response_id', response_id) \
        .limit(1).execute()
    row = existing.data[0] if existing.data else None
    return {
        "stage1_completed": bool(row and row.get('stage1_completed_at')),
        "result_stage_completed": bool(row and row.get('result_stage_completed_at')),
        "stage2_completed": bool(row and row.get('stage2_completed_at')),
    }

@app.get("/beta-feedback/{response_id}/stage2")
def get_beta_feedback_stage2(response_id: str, user=Depends(get_optional_user)):
    """Existing stage2 answers, if any, so the form can be re-opened pre-filled
    for editing rather than starting blank every time."""
    fields = list(BetaFeedbackStage2Request.model_fields.keys())
    fields.remove('response_id')
    existing = supabase.table('beta_feedback') \
        .select(','.join(fields)) \
        .eq('response_id', response_id) \
        .limit(1).execute()
    if not existing.data:
        return {}
    return {k: v for k, v in existing.data[0].items() if v is not None}

@app.post("/beta-feedback/stage2")
def submit_beta_feedback_stage2(body: BetaFeedbackStage2Request, user=Depends(get_optional_user)):
    row = body.model_dump(exclude={'response_id'}, exclude_none=True)
    row['response_id'] = body.response_id
    if user:   # a later anonymous save (link opened signed out) must not unlink the account
        row['user_id'] = user.id
    row['plan_tier'] = _feedback_plan_tier(body.response_id)
    row['stage2_completed_at'] = datetime.now(timezone.utc).isoformat()
    result = supabase.table('beta_feedback').upsert(row, on_conflict='response_id').execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    return {"ok": True}

@app.get("/admin/beta-feedback")
def get_beta_feedback(_=Depends(require_admin)):
    # beta_feedback has no name/email of its own — embed the owning
    # assessment_responses row (FK on response_id) so the admin list doesn't
    # need a second round-trip per row.
    data = _execute_with_retry(supabase.table('beta_feedback')
        .select('*, assessment_responses(full_name, email, locale, country, nationality, age, age_bracket, experience_level, current_stage, cohort_override)')
        .order('created_at', desc=True))
    return data.data or []

@app.post("/waitlist")
def join_waitlist(body: WaitlistRequest):
    try:
        result = supabase.table('waitlist_signups').insert(body.model_dump()).execute()
    except Exception as e:
        if 'duplicate key' in str(e).lower():
            return {"status": "already_joined"}
        raise HTTPException(status_code=500, detail="Failed to join waitlist")
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to join waitlist")
    return {"status": "joined", "id": result.data[0]["id"]}

@app.get("/admin/waitlist")
def get_waitlist(_=Depends(require_admin)):
    data = supabase.table('waitlist_signups') \
        .select('*') \
        .order('created_at', desc=True) \
        .execute()
    return data.data or []

@app.post("/partners")
def submit_partner_inquiry(body: PartnerRequest):
    result = supabase.table('partner_inquiries').insert(body.model_dump()).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to submit partner inquiry")
    return {"status": "submitted", "id": result.data[0]["id"]}

@app.get("/admin/partners")
def get_partner_inquiries(_=Depends(require_admin)):
    data = supabase.table('partner_inquiries') \
        .select('*') \
        .order('created_at', desc=True) \
        .execute()
    return data.data or []

@app.post("/waitlist/events")
def track_waitlist_event(body: WaitlistEventRequest):
    """Best-effort page-view/click tracking for the waitlist page — never
    fails the caller, since a dropped analytics event shouldn't break the page."""
    if body.event_type not in WAITLIST_EVENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid event_type")
    try:
        supabase.table('waitlist_events').insert(body.model_dump()).execute()
    except Exception as e:
        print("Failed to record waitlist event:", e)
    return {"status": "ok"}

@app.post("/featured-course/events")
def track_featured_course_event(body: FeaturedCourseEventRequest):
    """Best-effort view/click tracking for the featured course card on the results page — never fails the caller."""
    if body.event_type not in ("view", "click"):
        raise HTTPException(status_code=400, detail="Invalid event_type")
    try:
        supabase.table('featured_course_events').insert({
            "event_type": body.event_type,
            "course_key": body.course_key[:80],
            "response_id": (body.response_id or None) and body.response_id[:64],
            "tier": (body.tier or None) and body.tier[:20],
            "locale": (body.locale or None) and body.locale[:5],
        }).execute()
    except Exception as e:
        print("Failed to record featured course event:", e)
    return {"status": "ok"}

@app.get("/admin/featured-course-events")
def get_featured_course_events(_=Depends(require_admin)):
    data = supabase.table('featured_course_events') \
        .select('*') \
        .order('created_at', desc=True) \
        .limit(20000) \
        .execute()
    return data.data or []

@app.post("/assessment/telemetry")
def track_assessment_telemetry(body: TelemetryBatchRequest):
    """Best-effort behavioral telemetry for the assessment flow (device type,
    break-panel plays, per-question pacing) — batched client-side, so one call
    can carry several events. A malformed batch still gets a 422 (FastAPI/
    Pydantic validate the request before this body runs), but the frontend
    queue (src/lib/telemetry.ts) swallows any error from this call, so a
    dropped or rejected analytics batch never surfaces to, or interrupts,
    someone mid-assessment. Unknown event_type values are dropped rather than
    rejecting the whole batch, so one bad event can't sink the rest."""
    rows = [
        {
            'session_id': body.session_id,
            'device_type': body.device_type,
            'locale': body.locale,
            'event_type': e.event_type,
            'question_id': e.question_id,
            'activity_kind': e.activity_kind,
            'duration_ms': e.duration_ms,
            'payload': e.payload,
        }
        for e in body.events
        if e.event_type in TELEMETRY_EVENT_TYPES
    ]
    if rows:
        try:
            supabase.table('assessment_telemetry_events').insert(rows).execute()
        except Exception as e:
            print("Failed to record assessment telemetry:", e)
    return {"status": "ok"}

@app.get("/admin/telemetry-events")
def get_telemetry_events(_=Depends(require_admin)):
    data = supabase.table('assessment_telemetry_events') \
        .select('*, assessment_responses(full_name, email)') \
        .order('created_at', desc=True) \
        .limit(20000) \
        .execute()
    return data.data or []

def _count(table: str, **filters) -> int:
    query = supabase.table(table).select('id', count='exact')
    for field, value in filters.items():
        query = query.eq(field, value)
    return query.execute().count or 0

def _count_since(table: str, since: str) -> int:
    return supabase.table(table).select('id', count='exact').gte('created_at', since).execute().count or 0

def _safe_stat(label: str, fn, default):
    try:
        return fn()
    except Exception as e:
        print(f"dashboard stat '{label}' failed: {type(e).__name__}: {e}")
        return default

_dashboard_stats_cache: dict[str, Any] = {"value": None, "computed_at": None}
_DASHBOARD_STATS_CACHE_TTL = timedelta(seconds=60)

def _build_dashboard_stats() -> dict:
    """Cached wrapper — the underlying query runs 10+ sequential Supabase
    round-trips (two of which page through the *entire* waitlist_signups
    table), which can take long enough to blow past the public share page's
    15s fetch timeout on a cold hit. A dashboard of aggregate counts doesn't
    need per-second freshness, so serve a 60s-stale copy instead of
    recomputing on every request."""
    now = datetime.now(timezone.utc)
    if _dashboard_stats_cache["computed_at"] and now - _dashboard_stats_cache["computed_at"] < _DASHBOARD_STATS_CACHE_TTL:
        return _dashboard_stats_cache["value"]
    value = _compute_dashboard_stats()
    _dashboard_stats_cache["value"] = value
    _dashboard_stats_cache["computed_at"] = now
    return value

def _compute_dashboard_stats() -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_start = (now - timedelta(days=7)).isoformat()

    return {
        "waitlist_signups": {
            "total": _safe_stat("waitlist_signups.total", lambda: _count('waitlist_signups'), 0),
            "today": _safe_stat("waitlist_signups.today", lambda: _count_since('waitlist_signups', today_start), 0),
            "this_week": _safe_stat("waitlist_signups.this_week", lambda: _count_since('waitlist_signups', week_start), 0),
        },
        "assessment_responses": {
            "total": _safe_stat("assessment_responses.total", lambda: _count('assessment_responses'), 0),
            "completed": _safe_stat("assessment_responses.completed", lambda: _count('assessment_responses', completed=True), 0),
        },
        "feedback_responses": _safe_stat("feedback_responses", lambda: _count('feedback_responses'), 0),
        "applications": _safe_stat("applications", lambda: _count('applications'), 0),
        "paid_plans": _safe_stat("paid_plans", lambda: supabase.table('user_plans').select('user_id', count='exact').execute().count or 0, 0),
        "courses": _safe_stat("courses", lambda: _count('courses'), 0),
        "country_profiles": _safe_stat("country_profiles", lambda: supabase.table('country_profiles').select('country_code', count='exact').execute().count or 0, 0),
        "waitlist_page": _safe_stat("waitlist_page", _get_waitlist_page_stats, {"page_views": 0, "clicks": 0, "top_clicks": []}),
        "waitlist_age_breakdown": _safe_stat("waitlist_age_breakdown", lambda: _get_waitlist_breakdown('age'), []),
        "waitlist_country_breakdown": _safe_stat("waitlist_country_breakdown", lambda: _get_waitlist_breakdown('country'), []),
    }

@app.get("/admin/dashboard-stats")
def get_dashboard_stats(_=Depends(require_admin)):
    return _build_dashboard_stats()

@app.get("/admin/dashboard-share-link")
def get_dashboard_share_link(_=Depends(require_admin)):
    token = _get_share_token()
    if not token:
        raise HTTPException(status_code=404, detail="Share link not configured")
    return {"token": token}

@app.post("/admin/dashboard-share-link/regenerate")
def regenerate_dashboard_share_link(_=Depends(require_admin)):
    """Issues a fresh share token and persists it, invalidating every link built
    from the old one — this is how a leaked/no-longer-wanted share link is revoked,
    since there was previously no way to invalidate one short of an env var change
    + redeploy."""
    new_token = secrets.token_urlsafe(32)
    supabase.table('app_settings').upsert({
        'key': DASHBOARD_SHARE_TOKEN_KEY,
        'value': new_token,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }, on_conflict='key').execute()
    _share_token_cache["checked_at"] = None
    return {"token": new_token}

@app.get("/public/dashboard-stats")
def get_public_dashboard_stats(token: str):
    """Unauthenticated read-only dashboard for sharing via a long, unguessable
    link — no login, gated only by the share token matching the URL token.
    404s (not 401/403) on a bad token so a wrong guess doesn't confirm the
    endpoint exists."""
    share_token = _get_share_token()
    if not share_token or not hmac.compare_digest(token, share_token):
        raise HTTPException(status_code=404, detail="Not found")
    return _build_dashboard_stats()

def _get_waitlist_breakdown(column: str) -> list[dict]:
    rows = _select_all(lambda: supabase.table('waitlist_signups').select(column))
    total = len(rows)
    if total == 0:
        return []
    counts = Counter((r.get(column) or 'Unknown') for r in rows)
    return [
        {"label": label, "count": count, "pct": round(count / total * 100, 1)}
        for label, count in counts.most_common()
    ]

def _get_waitlist_page_stats() -> dict:
    try:
        page_views = _count('waitlist_events', event_type='page_view')
        click_rows = supabase.table('waitlist_events').select('label').eq('event_type', 'click').execute().data or []
    except Exception as e:
        # waitlist_events migration may not be applied yet — don't take down the
        # whole dashboard over one optional widget.
        print("waitlist_events lookup failed:", e)
        return {"page_views": 0, "clicks": 0, "top_clicks": []}
    click_counts = Counter((r.get('label') or 'unknown') for r in click_rows)
    return {
        "page_views": page_views,
        "clicks": len(click_rows),
        "top_clicks": [{"label": label, "count": count} for label, count in click_counts.most_common(10)],
    }

def _report_order(response_id: str, ranked: list, tier: str, generate: bool = True) -> list:
    """Careers in the order the report lists them (the report is the single source of truth for what the user sees).
    generate=False only reads the saved report content (used by the dashboard card); generate=True makes sure it exists.
    Falls back to the raw ranking if the report content is not available."""
    try:
        from report_generator import get_or_generate_ai_content, order_by_report
        if generate:
            content = get_or_generate_ai_content(response_id, supabase, tier=tier, locale='en')
        else:
            row = _execute_with_retry(supabase.table('assessment_responses')
                .select('ai_content_cache,ai_content_cache_free').eq('id', response_id).single()).data or {}
            content = (row.get('ai_content_cache_free') if tier == 'free' else row.get('ai_content_cache')) or {}
        content = {**content, 'career_recommendations': drop_weak_matches(content.get('career_recommendations') or [])}
        return order_by_report(ranked, content)
    except Exception as e:
        print(f"[report order] falling back to ranked careers for {response_id}: {e}")
        return ranked

@app.get("/assessment/{response_id}/career-suggestions")
def get_career_suggestions(response_id: str, user=Depends(get_optional_user)):
    rows = supabase.table('assessment_results') \
        .select('*').eq('response_id', response_id).execute()
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found for this response")

    profile = supabase.table('assessment_responses') \
        .select('education_field, career_direction, sectors_of_interest, experience_level, user_id, current_stage, answers') \
        .eq('id', response_id).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    _assert_can_view_shared(profile.data.get('user_id'), user)

    summary = build_framework_output(rows.data)
    careers = supabase.table('careers').select('*').eq('is_approved', True).execute().data or []
    semantic_scores = _get_semantic_scores(response_id, summary, profile.data or {})
    top10   = score_careers(summary, profile.data or {}, careers, semantic_scores)
    _tier = get_effective_tier(profile.data.get('user_id'))
    top10 = _report_order(response_id, top10, _tier, generate=False)
    if _tier == "free" and not _is_admin(user):
        top10 = top10[:3]

    user_riasec = summary.get('riasec', {}).get('top_types', [])
    return {
        "riasec_code": ''.join(t[0].upper() for t in user_riasec),
        "suggestions": [                                                                                                                                                                                               {
                "title": c['title'],
                "sector": c['sector'],
                "entrepreneurship_friendly": c['entrepreneurship_friendly'],
            }
            for c in top10
        ]
    }

@app.get("/assessment/{response_id}/career-recommendations")
def get_career_recommendations(response_id: str, locale: str | None = None, user=Depends(get_optional_user)):
    owner_row = supabase.table('assessment_responses').select('user_id,career_direction').eq('id', response_id).single().execute()
    if not owner_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    owner_user_id = owner_row.data.get('user_id')
    _assert_can_view_shared(owner_user_id, user)
    tier = get_effective_tier(owner_user_id)

    from report_generator import get_or_generate_ai_content
    try:
        ai_content = get_or_generate_ai_content(response_id, supabase, tier=tier, locale=locale or 'en')
    except Exception as e:
        send_failure_alert("Career recommendations generation", e, response_id=response_id, supabase=supabase)
        raise HTTPException(status_code=500, detail="Career recommendations generation failed, please try again")

    # action_plan is generated in the same call as career_recommendations (see
    # generate_ai_content). Now rendered on the live results page's Action Plan
    # card, in addition to admin review and the downloaded PDF.
    action_plan = dict(ai_content.get("action_plan") or {})
    recs = drop_weak_matches(ai_content.get("career_recommendations") or [])
    if tier == "free" and not _is_admin(user):
        # Free tier: no plan at all (not even the first step) and 3 suggested careers; both are part of the paid report.
        action_plan = {}
        recs = [{k: v for k, v in r.items() if k != "next_steps"} if isinstance(r, dict) else r for r in recs[:3]]
    # Short takeaways for the profile cards (paid only), the same words the PDF uses
    profile_details = None
    if tier != "free" or _is_admin(user):
        try:
            from report_generator import profile_notes
            _rows = supabase.table('assessment_results').select('*').eq('response_id', response_id).execute()
            profile_details = profile_notes(ai_content, build_framework_output(_rows.data), locale or 'en') if _rows.data else None
        except Exception as e:
            print(f"[career-recommendations] profile notes skipped for {response_id}: {e}")
    return {
        "career_recommendations": recs,
        "profile_details": profile_details,
        "action_plan": action_plan,
        # Lets the results page order the "Build on what you have" / "Paths you may not have considered" groups.
        "career_direction": owner_row.data.get('career_direction'),
    }

@app.get("/assessment/{response_id}/full-report-status")
def get_full_report_status(response_id: str, locale: str | None = None, user=Depends(get_optional_user)):
    """Whether the paid report's main parts are saved (used by the dashboard's "building your full report" notice)."""
    row = supabase.table('assessment_responses').select(
        'user_id,ai_content_cache,ai_content_cache_ar,ai_impact_cache,ai_impact_cache_ar').eq('id', response_id).single().execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    _assert_can_view(row.data.get('user_id'), user)
    ar = locale == 'ar'
    content = row.data.get('ai_content_cache_ar' if ar else 'ai_content_cache')
    impact = row.data.get('ai_impact_cache_ar' if ar else 'ai_impact_cache')
    return {"ready": bool(content and impact), "building": response_id in _prewarm_inflight}

def _trim_ai_impact_free(out: dict) -> dict:
    """Free plan shows only the first point of each AI-impact list and the first sentence of the 'what this means for you'
    paragraph (the page blurs a placeholder for the rest), so the full text is not sent to free viewers at all."""
    import re as _re
    careers = []
    for c in out.get("careers") or []:
        c = dict(c)
        for k in ("at_risk_tasks", "protected_skills"):
            if isinstance(c.get(k), list):
                c[k + "_total"] = len(c[k])  # real count, so the page can say "N more" without sending the text
                c[k] = c[k][:1]
        txt = c.get("what_this_means_for_you")
        if isinstance(txt, str) and txt:
            c["what_this_means_for_you"] = _re.split(r'(?<=[.!?؟])\s+', txt.strip(), maxsplit=1)[0]
        careers.append(c)
    return {**out, "careers": careers}

@app.get("/assessment/{response_id}/ai-impact")
def get_ai_impact(response_id: str, force: bool = False, locale: str | None = None, user=Depends(get_optional_user)):
    profile_row = _execute_with_retry(supabase.table('assessment_responses')
        .select('full_name,current_stage,country,experience_level,education_field,career_direction,sectors_of_interest,'
                'ai_impact_cache,ai_impact_cache_free,ai_impact_cache_ar,ai_impact_cache_ar_free,user_id,answers')
        .eq('id', response_id).single())
    if not profile_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    enrich_profile(profile_row.data)
    owner_user_id = profile_row.data.get('user_id')
    _assert_can_view_shared(owner_user_id, user)
    if force:
        _assert_can_force_refresh(owner_user_id, user)
    tier = get_effective_tier(owner_user_id)
    # Free tier generates (and caches) only the 2 careers it's entitled to see, instead
    # of paying for a 5-career Gemini call and discarding 3 — see create_report()'s
    # matching *_free cache columns for why paid tiers share a single "full" cache.
    is_free = tier == "free"
    # careers_cap = 2 if is_free else 8  # paid
    careers_cap = 3 if is_free else 8  # free: 3 (matches the 3 career cards); paid: one AI-impact row for every career card shown (8)
    cache_col = 'ai_impact_cache_free' if is_free else 'ai_impact_cache'
    cache_col_ar = 'ai_impact_cache_ar_free' if is_free else 'ai_impact_cache_ar'
    locale = locale or 'en'

    cache_col_active = cache_col_ar if locale == 'ar' else cache_col
    cached = profile_row.data.get(cache_col_active)
    if cached and not force:
        out = {**cached, "careers": (cached.get("careers") or [])[:careers_cap]}
        if is_free:
            out.pop("focus", None)  # skills-to-build / practice exercise are part of the paid plan
            out = _trim_ai_impact_free(out)
        return out

    rows = _execute_with_retry(supabase.table('assessment_results')
        .select('*').eq('response_id', response_id))
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found for this response")

    summary = build_framework_output(rows.data)
    careers = _execute_with_retry(supabase.table('careers').select('*').eq('is_approved', True)).data or []
    semantic_scores = _get_semantic_scores(response_id, summary, profile_row.data or {})
    ranked_all = score_careers(summary, profile_row.data or {}, careers, semantic_scores)
    top_careers = _report_order(response_id, ranked_all, tier)[:careers_cap]
    # Cover exactly the career cards the report shows, not just the top of the raw ranking
    try:
        from report_generator import impact_targets, get_or_generate_ai_content
        _content = get_or_generate_ai_content(response_id, supabase, tier=tier, locale='en')
        top_careers = impact_targets(ranked_all, _content, careers_cap)
    except Exception as e:
        print(f"[ai-impact] using ranked careers for {response_id}: {e}")

    from report_generator import get_or_generate_ai_impact
    try:
        result = get_or_generate_ai_impact(response_id, summary, profile_row.data or {}, top_careers,
            careers_cap, supabase, cache_col, cache_col_ar, locale=locale, force=force)
    except Exception as e:
        send_failure_alert("AI Impact generation", e, response_id=response_id, supabase=supabase)
        # Converted from a bare `raise` to HTTPException: a re-raised plain exception
        # bypasses FastAPI's HTTPException handling and falls through to
        # CatchAllMiddleware, which would log a second, generically-labeled
        # bug_reports row for the same failure already recorded above.
        raise HTTPException(status_code=500, detail="AI Impact generation failed, please try again")

    out = {**result, "careers": (result.get("careers") or [])[:careers_cap]}
    if is_free:
        out.pop("focus", None)
        out = _trim_ai_impact_free(out)
    return out

def _trim_student_track(track: dict, tier: str) -> dict:
    """High-school majors comparison: free tier keeps just each major's name and one-line reason;
    the careers it leads to and the 'try it' step are part of the paid plan."""
    if track and tier == "free" and track.get("majors"):
        track = {**track, "majors": [{"name": m.get("name"), "why_fit": m.get("why_fit")} for m in track["majors"]]}
    return add_student_track_links(track)

@app.get("/assessment/{response_id}/student-track")
def get_student_track(response_id: str, force: bool = False, locale: str | None = None, user=Depends(get_optional_user)):
    """Majors guidance + exposure ideas for still-enrolled students — the
    doc's replacement for job listings in that track. Returns {} for anyone
    else (mirrors _search_matching_jobs's is_still_enrolled gate) rather than
    404ing, so the frontend can just check for an empty response."""
    profile_row = _execute_with_retry(supabase.table('assessment_responses')
        .select('current_stage,country,experience_level,education_field,career_direction,sectors_of_interest,'
                'student_track_cache,student_track_cache_ar,user_id,answers')
        .eq('id', response_id).single())
    if not profile_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    enrich_profile(profile_row.data)
    owner_user_id = profile_row.data.get('user_id')
    _assert_can_view_shared(owner_user_id, user)
    if force:
        _assert_can_force_refresh(owner_user_id, user)

    if profile_row.data.get('current_stage') not in STILL_ENROLLED_STAGES:
        return {}

    locale = locale or 'en'
    tier = "launchpad" if _is_admin(user) else get_effective_tier(owner_user_id)
    if tier == "free":
        # "Ways to explore" is part of the paid report: free viewers get a marker (the page blurs a placeholder) and
        # no AI call is spent on them.
        return {"locked": True}
    cache_col_active = 'student_track_cache_ar' if locale == 'ar' else 'student_track_cache'
    cached = profile_row.data.get(cache_col_active)
    if cached and not force:
        return _trim_student_track(cached, tier)

    rows = _execute_with_retry(supabase.table('assessment_results').select('*').eq('response_id', response_id))
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found for this response")

    summary = build_framework_output(rows.data)
    careers = _execute_with_retry(supabase.table('careers').select('*').eq('is_approved', True)).data or []
    semantic_scores = _get_semantic_scores(response_id, summary, profile_row.data or {})
    top_careers = _report_order(response_id, score_careers(summary, profile_row.data or {}, careers, semantic_scores), get_effective_tier(profile_row.data.get('user_id')))[:5]

    from report_generator import get_or_generate_student_track
    try:
        result = get_or_generate_student_track(response_id, summary, profile_row.data or {}, top_careers,
            supabase, locale=locale, force=force)
    except Exception as e:
        send_failure_alert("Student track generation", e, response_id=response_id, supabase=supabase)
        raise HTTPException(status_code=500, detail="Student track generation failed, please try again")
    return _trim_student_track(result, tier)

@app.get("/assessment/{response_id}/certifications")
def get_certifications(response_id: str, force: bool = False, locale: str | None = None, user=Depends(get_optional_user)):
    """Certifications to pursue for recent grads entering the market — entry
    roles/employers are already covered by job-listings/companies, unchanged.
    Returns {} for anyone else, same pattern as /student-track."""
    profile_row = _execute_with_retry(supabase.table('assessment_responses')
        .select('current_stage,country,experience_level,education_field,career_direction,sectors_of_interest,'
                'certifications_cache,certifications_cache_ar,user_id,answers')
        .eq('id', response_id).single())
    if not profile_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    enrich_profile(profile_row.data)
    owner_user_id = profile_row.data.get('user_id')
    _assert_can_view_shared(owner_user_id, user)
    if force:
        _assert_can_force_refresh(owner_user_id, user)

    if profile_row.data.get('current_stage') not in CERTIFICATION_STAGES:
        return {}
    # Certifications are part of the paid plan (Pathfinder or Launchpad). Free users get {} and the
    # results page shows an unlock card, so no AI call is spent on them. Admins always see them.
    if get_effective_tier(owner_user_id) == "free" and not _is_admin(user):
        return {}

    locale = locale or 'en'
    cache_col_active = 'certifications_cache_ar' if locale == 'ar' else 'certifications_cache'
    cached = profile_row.data.get(cache_col_active)
    if cached and not force:
        return cached

    rows = _execute_with_retry(supabase.table('assessment_results').select('*').eq('response_id', response_id))
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found for this response")

    summary = build_framework_output(rows.data)
    careers = _execute_with_retry(supabase.table('careers').select('*').eq('is_approved', True)).data or []
    semantic_scores = _get_semantic_scores(response_id, summary, profile_row.data or {})
    top_careers = _report_order(response_id, score_careers(summary, profile_row.data or {}, careers, semantic_scores), get_effective_tier(profile_row.data.get('user_id')))[:5]

    from report_generator import get_or_generate_certifications
    try:
        result = get_or_generate_certifications(response_id, summary, profile_row.data or {}, top_careers,
            supabase, locale=locale, force=force)
    except Exception as e:
        send_failure_alert("Certifications generation", e, response_id=response_id, supabase=supabase)
        raise HTTPException(status_code=500, detail="Certifications generation failed, please try again")
    return result

@app.get("/assessment/{response_id}/career-path")
def get_career_path(response_id: str, force: bool = False, locale: str | None = None, user=Depends(get_optional_user)):
    """Progression (stay_in_field) or transition (change_field) write-up for
    working professionals. Returns {} for anyone else, same pattern as
    /student-track."""
    profile_row = _execute_with_retry(supabase.table('assessment_responses')
        .select('current_stage,country,experience_level,education_field,career_direction,sectors_of_interest,'
                'career_path_cache,career_path_cache_ar,user_id,answers')
        .eq('id', response_id).single())
    if not profile_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    enrich_profile(profile_row.data)  # country to work in (QOTC)
    owner_user_id = profile_row.data.get('user_id')
    _assert_can_view_shared(owner_user_id, user)
    if force:
        _assert_can_force_refresh(owner_user_id, user)

    if profile_row.data.get('current_stage') not in PROFESSIONAL_STAGES:
        return {}

    locale = locale or 'en'
    cache_col_active = 'career_path_cache_ar' if locale == 'ar' else 'career_path_cache'
    cached = profile_row.data.get(cache_col_active)
    if cached and not force:
        return cached

    rows = _execute_with_retry(supabase.table('assessment_results').select('*').eq('response_id', response_id))
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found for this response")

    summary = build_framework_output(rows.data)
    careers = _execute_with_retry(supabase.table('careers').select('*').eq('is_approved', True)).data or []
    semantic_scores = _get_semantic_scores(response_id, summary, profile_row.data or {})
    top_careers = _report_order(response_id, score_careers(summary, profile_row.data or {}, careers, semantic_scores), get_effective_tier(profile_row.data.get('user_id')))[:5]

    from report_generator import get_or_generate_career_path
    try:
        result = get_or_generate_career_path(response_id, summary, profile_row.data or {}, top_careers,
            supabase, locale=locale, force=force)
    except Exception as e:
        send_failure_alert("Career path generation", e, response_id=response_id, supabase=supabase)
        raise HTTPException(status_code=500, detail="Career path generation failed, please try again")
    return result

RECOMMENDATION_FEEDBACK_REASONS = ("uninterested", "unqualified", "unfamiliar", "impractical")
MAX_FEEDBACK_ROWS_PER_RESPONSE = 20

class RecommendationFeedbackRequest(BaseModel):
    career_title: str = Field(min_length=1, max_length=120)
    reason: Literal["uninterested", "unqualified", "unfamiliar", "impractical"]
    locale: Literal["en", "ar"] = "en"

def _clean_feedback_title(title: str) -> str:
    return re.sub(r"\s+", " ", title or "").strip()[:120]

@app.get("/assessment/{response_id}/recommendation-feedback")
def get_recommendation_feedback(response_id: str, user=Depends(get_optional_user)):
    """The careers this user marked 'not for me', with the reason: {"items": [{career_title, reason}]}."""
    owner_row = _execute_with_retry(supabase.table('assessment_responses').select('user_id').eq('id', response_id).single())
    if not owner_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    _assert_can_view(owner_row.data.get('user_id'), user)
    try:
        rows = _execute_with_retry(supabase.table('recommendation_feedback')
            .select('career_title,reason').eq('response_id', response_id)).data or []
    except Exception as e:
        print("recommendation_feedback read failed (table missing?):", e)
        return {"items": []}
    return {"items": rows}

@app.post("/assessment/{response_id}/recommendation-feedback")
def save_recommendation_feedback(response_id: str, body: RecommendationFeedbackRequest, user=Depends(get_optional_user)):
    """Record (or change) why a career was rejected. Feedback only: it never changes a score or a report."""
    owner_row = _execute_with_retry(supabase.table('assessment_responses').select('user_id').eq('id', response_id).single())
    if not owner_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    _assert_can_view(owner_row.data.get('user_id'), user)
    title = _clean_feedback_title(body.career_title)
    if not title:
        raise HTTPException(status_code=422, detail="Missing career")
    try:
        existing = _execute_with_retry(supabase.table('recommendation_feedback')
            .select('career_title').eq('response_id', response_id)).data or []
        if title not in {r['career_title'] for r in existing} and len(existing) >= MAX_FEEDBACK_ROWS_PER_RESPONSE:
            raise HTTPException(status_code=429, detail="Too many careers marked already")
        supabase.table('recommendation_feedback').upsert({
            'response_id': response_id, 'career_title': title, 'locale': body.locale, 'reason': body.reason,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }, on_conflict='response_id,career_title').execute()
    except HTTPException:
        raise
    except Exception as e:
        print("recommendation_feedback write failed:", e)
        raise HTTPException(status_code=503, detail="This feature is not available yet, please try again later")
    return {"career_title": title, "reason": body.reason}

@app.delete("/assessment/{response_id}/recommendation-feedback")
def delete_recommendation_feedback(response_id: str, career_title: str, user=Depends(get_optional_user)):
    """Undo: the user changed their mind about a career."""
    owner_row = _execute_with_retry(supabase.table('assessment_responses').select('user_id').eq('id', response_id).single())
    if not owner_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    _assert_can_view(owner_row.data.get('user_id'), user)
    try:
        supabase.table('recommendation_feedback').delete() \
            .eq('response_id', response_id).eq('career_title', _clean_feedback_title(career_title)).execute()
    except Exception as e:
        print("recommendation_feedback delete failed:", e)
        raise HTTPException(status_code=503, detail="This feature is not available yet, please try again later")
    return {"deleted": True}

@app.get("/admin/recommendation-feedback")
def admin_recommendation_feedback(_=Depends(require_admin)):
    """Why users rejected careers: counts by reason and by career (top 30), plus the total."""
    try:
        rows = _execute_with_retry(supabase.table('recommendation_feedback').select('career_title,reason,locale')).data or []
    except Exception as e:
        print("recommendation_feedback admin read failed (table missing?):", e)
        return {"total": 0, "by_reason": {}, "by_career": []}
    by_reason: dict[str, int] = {}
    by_career: dict[str, dict] = {}
    for r in rows:
        by_reason[r['reason']] = by_reason.get(r['reason'], 0) + 1
        c = by_career.setdefault(r['career_title'], {"career_title": r['career_title'], "total": 0, "reasons": {}})
        c["total"] += 1
        c["reasons"][r['reason']] = c["reasons"].get(r['reason'], 0) + 1
    top = sorted(by_career.values(), key=lambda c: c["total"], reverse=True)[:30]
    return {"total": len(rows), "by_reason": by_reason, "by_career": top}

class DirectionRequest(BaseModel):
    label: str = Field(max_length=200)
    source: Literal["suggested", "user"]
    locale: Literal["en", "ar"] = "en"

MAX_DIRECTIONS_PER_RESPONSE = 5

def _direction_payload(row: dict, locale: str) -> dict:
    plans = row.get('plans') or {}
    return {
        "label": row.get('label'),
        "source": row.get('source'),
        "plan": plans.get(locale),
        "locales": list(plans.keys()),
    }

# (response_id, locale) -> "running" | "failed": stops the results page's polling from starting a second AI call,
# or retrying a failed one on every poll. In-process only (single uvicorn worker); a restart just allows one more try,
# and the cached plan in direction_plans is checked before any AI call is made.
_direction_autobuild: dict[tuple[str, str], str] = {}

def _autobuild_direction(response_id: str, label: str, source: str, locale: str):
    key = (response_id, locale)
    try:
        row = _execute_with_retry(supabase.table('assessment_responses')
            .select('user_id,current_stage,country,education_field,career_direction,experience_level,sectors_of_interest,answers')
            .eq('id', response_id).single())
        _build_direction_plan(response_id, row.data, label, source, locale)
        _direction_autobuild.pop(key, None)
    except HTTPException as e:
        print(f"direction auto-build refused for {response_id} ({locale}): {e.detail}")
        _direction_autobuild[key] = "failed"
    except Exception as e:
        print(f"direction auto-build failed for {response_id} ({locale}):", e)
        _direction_autobuild[key] = "failed"

@app.get("/assessment/{response_id}/direction")
def get_direction(response_id: str, background_tasks: BackgroundTasks, locale: str | None = None, user=Depends(get_optional_user)):
    """The direction the plan is built around (or null), with its plan for `locale` if one exists.

    The direction is the optional "field you have in mind" answer from the end of the assessment (QOFIELD), or one
    chosen earlier through POST. For a paid report whose plan is not built yet in this language, the build starts here
    in the background and `pending` is true: the results page polls until the plan appears. `failed_label` is set when
    the build was refused or failed, so the page can say so instead of polling forever."""
    loc = locale if locale in ('en', 'ar') else 'en'
    owner_row = _execute_with_retry(supabase.table('assessment_responses').select('user_id,answers').eq('id', response_id).single())
    if not owner_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    owner_user_id = owner_row.data.get('user_id')
    _assert_can_view_shared(owner_user_id, user)
    try:
        rows = _execute_with_retry(supabase.table('direction_plans')
            .select('*').eq('response_id', response_id).eq('is_selected', True)).data or []
    except Exception as e:
        # Table not created yet (migration not applied) or a DB hiccup: behave as "nothing chosen".
        print("direction_plans read failed:", e)
        return {"selected": None}
    selected = rows[0] if rows else None
    if selected and (selected.get('plans') or {}).get(loc):
        return {"selected": _direction_payload(selected, loc)}

    label = selected.get('label') if selected else clean_direction_label((owner_row.data.get('answers') or {}).get('QOFIELD'))
    source = selected.get('source') if selected else 'user'
    out = {"selected": _direction_payload(selected, loc) if selected else None}
    if not label:
        return out
    if get_effective_tier(owner_user_id) == "free":
        # Not built for free users; the page shows an unlock card because they did ask for a plan.
        return {**out, "requested_label": label}
    state = _direction_autobuild.get((response_id, loc))
    if state == "failed":
        return {**out, "failed_label": label}
    if state is None:
        _direction_autobuild[(response_id, loc)] = "running"
        background_tasks.add_task(_autobuild_direction, response_id, label, source, loc)
    return {**out, "pending": True, "pending_label": label}

def _build_direction_plan(response_id: str, profile: dict, label_raw: str, source: str, locale: str) -> dict:
    """Builds (or returns the cached) plan for one direction in one language and marks it as the selected one.
    Callers have already decided the user may have it (owner/admin and paid). Raises HTTPException on refusal."""
    label = clean_direction_label(label_raw)
    if not label:
        raise HTTPException(status_code=422, detail="Please use a short field or career name (letters, numbers and simple punctuation).")
    key = direction_key(label)
    enrich_profile(profile)

    # Identical requests (a double click, two tabs, a retry after a slow response) are serialised: the second one
    # waits for the first to finish, then finds the plan it cached instead of paying for another AI call.
    from report_generator import single_flight
    with single_flight(f"direction:{response_id}:{key}:{locale}"):
        try:
            existing = _execute_with_retry(supabase.table('direction_plans').select('*').eq('response_id', response_id)).data or []
        except Exception as e:
            print("direction_plans read failed:", e)
            raise HTTPException(status_code=503, detail="This feature is not available yet, please try again later")
        row = next((r for r in existing if r.get('direction_key') == key), None)
        if row is None and len(existing) >= MAX_DIRECTIONS_PER_RESPONSE:
            raise HTTPException(status_code=429, detail=f"You have already built plans for {MAX_DIRECTIONS_PER_RESPONSE} different directions")
        plans = dict((row or {}).get('plans') or {})

        if locale not in plans:
            rows = _execute_with_retry(supabase.table('assessment_results').select('*').eq('response_id', response_id))
            if not rows.data:
                raise HTTPException(status_code=404, detail="No results found for this response")
            summary = build_framework_output(rows.data)

            # Grounding: what we already say about this career (suggested), or the closest careers we know of (typed).
            related: list[str] = []
            context = ""
            try:
                from report_generator import get_or_generate_ai_content
                recs = (get_or_generate_ai_content(response_id, supabase, tier="launchpad", locale='en') or {}).get('career_recommendations') or []
                rec = next((r for r in recs if str(r.get('title', '')).casefold() == key), None)
                if rec:
                    context = " ".join(str(rec.get(k, '')) for k in ('fit_summary', 'gap') if rec.get(k))
                    related = [rec.get('title')]
            except Exception as e:
                print("direction: could not load career recommendations for grounding:", e)
            if not related:
                try:
                    emb = _gemini_embed(label)
                    matches = supabase.rpc("match_careers", {"query_embedding": emb, "match_count": 3}).execute().data or []
                    ids = [m['id'] for m in matches]
                    if ids:
                        titles = supabase.table('careers').select('id,title').in_('id', ids).execute().data or []
                        by_id = {t['id']: t['title'] for t in titles}
                        related = [by_id[i] for i in ids if i in by_id]
                except Exception as e:
                    print("direction: could not find related careers (continuing without):", e)

            from report_generator import generate_direction_plan
            try:
                plan = generate_direction_plan(profile, summary,
                    {"label": label, "source": source, "related": related, "context": context}, locale)
            except Exception as e:
                send_failure_alert("Direction plan generation", e, response_id=response_id, supabase=supabase)
                raise HTTPException(status_code=500, detail="We could not build your plan right now, please try again")
            if not plan.get("recognised", True):
                raise HTTPException(status_code=422, detail="We could not tell what field that is. Try a more common name, for example 'Supply chain management'.")
            plan.pop("recognised", None)
            plans[locale] = plan

        now = datetime.now(timezone.utc).isoformat()
        try:
            supabase.table('direction_plans').upsert({
                'response_id': response_id, 'direction_key': key, 'label': label,
                'source': (row or {}).get('source') or source, 'plans': plans, 'updated_at': now,
            }, on_conflict='response_id,direction_key').execute()
            supabase.table('direction_plans').update({'is_selected': False}).eq('response_id', response_id).execute()
            saved = supabase.table('direction_plans').update({'is_selected': True}) \
                .eq('response_id', response_id).eq('direction_key', key).execute().data or []
        except Exception as e:
            print("direction_plans write failed:", e)
            raise HTTPException(status_code=503, detail="This feature is not available yet, please try again later")
        return {"selected": _direction_payload(saved[0] if saved else {"label": label, "source": source, "plans": plans}, locale)}


@app.post("/assessment/{response_id}/direction")
def choose_direction(response_id: str, body: DirectionRequest, user=Depends(get_optional_user)):
    """Build the plan around a chosen direction (one of the suggested careers, or a field the user typed).
    Paid feature and it spends an AI call, so: owner or admin only, one generation per direction per language,
    and at most MAX_DIRECTIONS_PER_RESPONSE different directions per assessment."""
    profile_row = _execute_with_retry(supabase.table('assessment_responses')
        .select('user_id,current_stage,country,education_field,career_direction,experience_level,sectors_of_interest,answers')
        .eq('id', response_id).single())
    if not profile_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    profile = profile_row.data
    owner_user_id = profile.get('user_id')
    _assert_can_view(owner_user_id, user)
    _assert_can_force_refresh(owner_user_id, user)
    tier = "launchpad" if _is_admin(user) else get_effective_tier(owner_user_id)
    if tier == "free":
        raise HTTPException(status_code=403, detail="Building your plan around your own direction is part of the full report")

    return _build_direction_plan(response_id, profile, body.label, body.source, body.locale)

@app.get("/assessment/{response_id}/report")
def get_report(response_id: str, locale: str | None = None, user=Depends(get_optional_user)):
    owner_row = supabase.table('assessment_responses').select('user_id').eq('id', response_id).single().execute()
    if not owner_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    owner_user_id = owner_row.data.get('user_id')
    _assert_can_view_shared(owner_user_id, user)
    tier = get_effective_tier(owner_user_id)

    if locale not in (None, 'en', 'ar'):
        raise HTTPException(status_code=400, detail="locale must be 'en' or 'ar'")

    try:
        pdf_bytes = create_report(response_id, supabase, tier=tier, locale_override=locale)
    except json.JSONDecodeError as e:
        # json.JSONDecodeError subclasses ValueError — must be caught before it so an
        # occasional malformed Gemini response isn't mistaken for the "not found" case below.
        send_failure_alert("PDF report download", e, response_id=response_id, supabase=supabase)
        raise HTTPException(status_code=502, detail="AI report generation failed, please try again")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (GoogleAPICallError, RequestException) as e:
        # Gemini's own request deadline (or the raw embedding call's timeout) was
        # hit — surface this as a retryable "still working on it" instead of the
        # confusing "Report generation failed: 504 The request timed out" that
        # GoogleAPICallError's str() otherwise produces.
        send_failure_alert("PDF report download", e, response_id=response_id, supabase=supabase)
        raise HTTPException(status_code=503, detail="Report generation is taking longer than expected. Please try again in a moment.")
    except Exception as e:
        send_failure_alert("PDF report download", e, response_id=response_id, supabase=supabase)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    filename = f"career-report-{response_id[:8]}{'-' + locale if locale else ''}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@app.post("/assessment/{response_id}/report/email")
def email_report(response_id: str, background_tasks: BackgroundTasks, locale: str | None = None, user=Depends(get_optional_user)):
    owner_row = supabase.table('assessment_responses').select('user_id, email, full_name').eq('id', response_id).single().execute()
    if not owner_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    owner_user_id = owner_row.data.get('user_id')
    _assert_can_view(owner_user_id, user)
    tier = get_effective_tier(owner_user_id)

    if locale not in (None, 'en', 'ar'):
        raise HTTPException(status_code=400, detail="locale must be 'en' or 'ar'")

    to_email = owner_row.data.get('email')
    if not to_email:
        raise HTTPException(status_code=400, detail="No email address on file for this response")

    try:
        pdf_bytes = create_report(response_id, supabase, tier=tier, locale_override=locale)
    except json.JSONDecodeError as e:
        # json.JSONDecodeError subclasses ValueError — must be caught before it so an
        # occasional malformed Gemini response isn't mistaken for the "not found" case below.
        send_failure_alert("Email report", e, response_id=response_id, supabase=supabase)
        raise HTTPException(status_code=502, detail="AI report generation failed, please try again")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (GoogleAPICallError, RequestException) as e:
        send_failure_alert("Email report", e, response_id=response_id, supabase=supabase)
        raise HTTPException(status_code=503, detail="Report generation is taking longer than expected. Please try again in a moment.")
    except Exception as e:
        send_failure_alert("Email report", e, response_id=response_id, supabase=supabase)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    filename = f"career-report-{response_id[:8]}{'-' + locale if locale else ''}.pdf"
    template_row = supabase.table('email_templates').select('*').eq('key', 'report_email').limit(1).execute()
    background_tasks.add_task(
        send_report_email,
        to_email,
        owner_row.data.get('full_name'),
        pdf_bytes,
        filename,
        locale or 'en',
        template_row.data[0] if template_row.data else None,
        supabase,
    )
    return {"status": "queued", "email": to_email}

@app.get("/admin/email-templates")
def get_email_templates(_=Depends(require_admin)):
    data = supabase.table('email_templates').select('*').order('name').execute()
    return data.data or []

@app.put("/admin/email-templates/{key}")
def update_email_template(key: str, body: dict, _=Depends(require_admin)):
    result = supabase.table('email_templates').update(body).eq('key', key).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Template not found")
    return result.data[0]


# Beta cohort start used by the "beta_incomplete" segment below — keep in sync
# with BETA_COHORT_START in the admin frontend (src/app/admin/page.tsx).
BETA_COHORT_START_ISO = "2026-09-06T00:00:00Z"


# Named audiences an admin can target from the scheduler. Add a new one here
# (and a matching branch in _resolve_segment_recipients) rather than a migration.
SEGMENT_KEYS = (
    'beta_incomplete',
    'waitlist_all',
    'waitlist_no_assessment',
    'waitlist_assessment_completed',
    'waitlist_assessment_no_feedback',
)


class ScheduledEmailCreate(BaseModel):
    template_key: str
    recipient_type: Literal['single', 'segment']
    recipient_email: str | None = None
    recipient_name: str | None = None
    segment_key: str | None = None
    locale: str = "en"
    variables: dict = {}
    scheduled_for: str  # ISO datetime (UTC)


@app.get("/admin/scheduled-emails")
def get_scheduled_emails(_=Depends(require_admin)):
    data = supabase.table('scheduled_emails').select('*').order('scheduled_for', desc=True).execute()
    return data.data or []


@app.get("/admin/scheduled-emails/segment-preview")
def preview_segment(segment_key: str, _=Depends(require_admin)):
    """Lets the admin UI show 'this will email N people' before a segment send
    is confirmed, plus a few sample addresses to sanity-check the filter."""
    if segment_key not in SEGMENT_KEYS:
        raise HTTPException(status_code=400, detail="Unknown segment_key")
    recipients = _resolve_segment_recipients(segment_key)
    return {"count": len(recipients), "sample": [r['email'] for r in recipients[:5]]}


@app.post("/admin/scheduled-emails")
def create_scheduled_email(body: ScheduledEmailCreate, _=Depends(require_admin)):
    if body.recipient_type == 'single' and not body.recipient_email:
        raise HTTPException(status_code=400, detail="recipient_email is required for a single recipient")
    if body.recipient_type == 'segment' and body.segment_key not in SEGMENT_KEYS:
        raise HTTPException(status_code=400, detail="segment_key must be one of: " + ", ".join(SEGMENT_KEYS))
    result = supabase.table('scheduled_emails').insert(body.model_dump()).execute()
    return result.data[0]


@app.put("/admin/scheduled-emails/{schedule_id}")
def update_scheduled_email(schedule_id: str, body: dict, _=Depends(require_admin)):
    result = supabase.table('scheduled_emails').update(body).eq('id', schedule_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return result.data[0]


@app.delete("/admin/scheduled-emails/{schedule_id}")
def delete_scheduled_email(schedule_id: str, _=Depends(require_admin)):
    supabase.table('scheduled_emails').delete().eq('id', schedule_id).execute()
    return {"status": "deleted"}


def _resolve_segment_recipients(segment_key: str) -> list[dict]:
    """Returns [{email, first_name, locale}] for a named admin-facing segment. Keep
    the 'beta_incomplete' cohort window in sync with BETA_COHORT_START in the admin
    frontend. waitlist_signups has no FK to assessment_responses/beta_feedback,
    so the waitlist_* segments are joined in Python by lowercased email rather
    than via a PostgREST embed. Each recipient carries their own locale (from
    their assessment if completed, else their waitlist signup) so the sender
    renders each person's actual language rather than one language per batch —
    both email_templates and render_template() already support per-call locale,
    this was just never threaded through from here."""
    if segment_key == 'beta_incomplete':
        rows = supabase.table('assessment_responses') \
            .select('email, full_name, locale') \
            .eq('completed', False) \
            .gte('created_at', BETA_COHORT_START_ISO) \
            .not_.is_('email', 'null') \
            .execute()
        recipients = []
        seen_emails = set()
        for r in (rows.data or []):
            email = (r.get('email') or '').strip().lower()
            if not email or email in seen_emails:
                continue
            seen_emails.add(email)
            recipients.append({
                "email": r['email'], "first_name": (r.get('full_name') or '').split(' ')[0],
                "locale": r.get('locale') or 'en',
            })
        return recipients

    if segment_key in ('waitlist_all', 'waitlist_no_assessment', 'waitlist_assessment_completed', 'waitlist_assessment_no_feedback'):
        waitlist_rows = supabase.table('waitlist_signups').select('email, name, locale').execute().data or []
        assessment_rows = supabase.table('assessment_responses').select('id, email, full_name, completed, locale').execute().data or []
        # A user can retake the assessment, producing multiple rows for the same
        # email — if any of them is completed, that's the row that should decide
        # this email's segment membership (not whichever row Supabase happens to
        # return last).
        assessment_by_email: dict[str, dict] = {}
        for r in assessment_rows:
            email = (r.get('email') or '').strip().lower()
            if not email:
                continue
            existing = assessment_by_email.get(email)
            if existing is None or (r.get('completed') and not existing.get('completed')):
                assessment_by_email[email] = r

        stage2_done_ids = set()
        if segment_key == 'waitlist_assessment_no_feedback':
            fb_rows = supabase.table('beta_feedback').select('response_id').not_.is_('stage2_completed_at', 'null').execute().data or []
            stage2_done_ids = {r['response_id'] for r in fb_rows}

        recipients = []
        seen_emails = set()
        for w in waitlist_rows:
            email = (w.get('email') or '').strip().lower()
            if not email or email in seen_emails:
                continue
            assessment = assessment_by_email.get(email)
            completed = bool(assessment and assessment.get('completed'))

            if segment_key == 'waitlist_no_assessment' and completed:
                continue
            if segment_key == 'waitlist_assessment_completed' and not completed:
                continue
            if segment_key == 'waitlist_assessment_no_feedback' and (not completed or assessment['id'] in stage2_done_ids):
                continue

            seen_emails.add(email)
            first_name = ((assessment or {}).get('full_name') or w.get('name') or '').split(' ')[0]
            # Prefer the locale they actually used to take the assessment (more
            # reliable signal of language ability than the waitlist form, which
            # may default from browser locale) — fall back to their waitlist
            # signup locale, then 'en'.
            locale = ((assessment or {}).get('locale') or w.get('locale') or 'en')
            recipient = {"email": w['email'], "first_name": first_name, "locale": locale}
            if assessment:
                # Lets the sender build a per-recipient beta_feedback_url for
                # templates that need one (e.g. beta_feedback_stage2).
                recipient["response_id"] = assessment['id']
            recipients.append(recipient)
        return recipients

    return []


@app.post("/internal/jobs/send-scheduled-emails")
def send_scheduled_emails(request: Request):
    """Sends whatever admin-scheduled emails (see /admin/scheduled-emails) are
    due. Called by a VPS crontab entry (not a browser), authenticated with a
    shared secret — same pattern as /internal/jobs/refresh-matches."""
    if not INTERNAL_JOBS_KEY or not hmac.compare_digest(request.headers.get("X-Internal-Key", ""), INTERNAL_JOBS_KEY):
        raise HTTPException(status_code=401, detail="Invalid internal key")

    now = datetime.now(timezone.utc)
    due = _execute_with_retry(supabase.table('scheduled_emails')
        .select('*')
        .eq('status', 'pending')
        .lte('scheduled_for', now.isoformat()))

    processed = 0
    for row in (due.data or []):
        # Claim it first so an overlapping cron tick can't double-send.
        claim = supabase.table('scheduled_emails').update({'status': 'sending'}).eq('id', row['id']).eq('status', 'pending').execute()
        if not claim.data:
            continue
        processed += 1

        # Whatever happens below, this row must leave 'sending' — otherwise it's
        # excluded from the 'pending' query above and silently stuck forever.
        try:
            template_row = supabase.table('email_templates').select('*').eq('key', row['template_key']).limit(1).execute()
            template = template_row.data[0] if template_row.data else None
            if not template:
                supabase.table('scheduled_emails').update({
                    'status': 'failed', 'error': f"template '{row['template_key']}' not found", 'sent_at': datetime.now(timezone.utc).isoformat(),
                }).eq('id', row['id']).execute()
                continue
            if not template.get('is_active'):
                supabase.table('scheduled_emails').update({
                    'status': 'failed', 'error': f"template '{row['template_key']}' is not active", 'sent_at': datetime.now(timezone.utc).isoformat(),
                }).eq('id', row['id']).execute()
                continue

            if row['recipient_type'] == 'single':
                recipients = [{"email": row['recipient_email'], "first_name": row.get('recipient_name') or ''}]
            else:
                recipients = _resolve_segment_recipients(row['segment_key'])

            if not recipients:
                supabase.table('scheduled_emails').update({
                    'status': 'failed', 'error': 'No recipients matched', 'sent_at': datetime.now(timezone.utc).isoformat(),
                }).eq('id', row['id']).execute()
                continue

            sent_count = 0
            failed_count = 0
            last_error = None
            for i, recipient in enumerate(recipients):
                try:
                    # Segment recipients carry their own locale (see
                    # _resolve_segment_recipients); a single-recipient send has
                    # no such signal, so it falls back to the schedule's own
                    # locale field, which is exactly what the admin picked for
                    # that one person.
                    recipient_locale = recipient.get('locale') or row.get('locale') or 'en'
                    variables = {
                        **(row.get('variables') or {}),
                        "first_name": recipient.get('first_name') or (row.get('variables') or {}).get('first_name', ''),
                        # Matches the existing convention in /assessment/submit — the
                        # beta feedback template's {{full_name}} slot is filled with
                        # just the first name, not the full name.
                        "full_name": recipient.get('first_name') or (row.get('variables') or {}).get('full_name', ''),
                    }
                    if recipient.get('response_id'):
                        frontend_base = os.getenv('FRONTEND_URL', '').rstrip('/')
                        variables['beta_feedback_url'] = f"{frontend_base}/{recipient_locale}/beta-feedback/{recipient['response_id']}"
                        variables['results_url'] = f"{frontend_base}/{recipient_locale}/results/{recipient['response_id']}"
                    subject, html_body = render_template(template, variables, recipient_locale)
                    send_email(recipient['email'], subject, html_body, supabase=supabase)
                    sent_count += 1
                except Exception as e:
                    failed_count += 1
                    last_error = str(e)
                if i < len(recipients) - 1:
                    # send_email opens a fresh SMTP connection + login per call — for a
                    # large segment, a small gap avoids tripping the mail provider's
                    # rate/connection limits partway through the batch.
                    time.sleep(0.3)

            supabase.table('scheduled_emails').update({
                'status': 'failed' if sent_count == 0 else 'sent',
                'sent_count': sent_count,
                'failed_count': failed_count,
                'error': last_error,
                'sent_at': datetime.now(timezone.utc).isoformat(),
            }).eq('id', row['id']).execute()
        except Exception as e:
            supabase.table('scheduled_emails').update({
                'status': 'failed', 'error': f"unexpected error: {e}", 'sent_at': datetime.now(timezone.utc).isoformat(),
            }).eq('id', row['id']).execute()

    return {"processed": processed}


class SmtpSettingsRequest(BaseModel):
    host: str
    port: int
    user: str
    password: str | None = None  # omitted/blank = keep existing password
    from_email: str
    from_name: str

@app.get("/admin/smtp-settings")
def get_smtp_settings(_=Depends(require_admin)):
    row = supabase.table('app_settings').select('value').eq('key', 'smtp_settings').execute()
    value = (row.data[0]['value'] if row.data else None) or {}
    return {**value, "password": "••••••••" if value.get("password") else ""}

@app.put("/admin/smtp-settings")
def update_smtp_settings(body: SmtpSettingsRequest, _=Depends(require_admin)):
    existing = supabase.table('app_settings').select('value').eq('key', 'smtp_settings').execute()
    current = (existing.data[0]['value'] if existing.data else None) or {}
    value = body.model_dump()
    if not value.get("password"):
        value["password"] = current.get("password", "")
    supabase.table('app_settings').upsert({
        'key': 'smtp_settings',
        'value': value,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }, on_conflict='key').execute()
    invalidate_smtp_cache()
    return {**value, "password": "••••••••" if value.get("password") else ""}

class TestModeRequest(BaseModel):
    enabled: bool

@app.get("/admin/test-mode")
def get_test_mode(_=Depends(require_admin)):
    return {"enabled": _is_test_mode_enabled()}

@app.post("/admin/test-mode")
def set_test_mode(body: TestModeRequest, _=Depends(require_admin)):
    supabase.table('app_settings').upsert({
        'key': TEST_MODE_KEY,
        'value': body.enabled,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }, on_conflict='key').execute()
    _test_mode_cache["value"] = body.enabled
    _test_mode_cache["checked_at"] = datetime.now(timezone.utc)
    return {"enabled": body.enabled}

class HomepageModeRequest(BaseModel):
    mode: str

    @property
    def is_valid(self) -> bool:
        return self.mode in ("landing", "waitlist")

@app.get("/homepage-mode")
def get_homepage_mode_public():
    """Unauthenticated — read by the frontend root page on every request to decide
    whether to render the marketing landing page or the pre-launch waitlist page."""
    return {"mode": _get_homepage_mode()}

@app.get("/admin/homepage-mode")
def get_homepage_mode_admin(_=Depends(require_admin)):
    return {"mode": _get_homepage_mode()}

@app.post("/admin/homepage-mode")
def set_homepage_mode(body: HomepageModeRequest, _=Depends(require_admin)):
    if not body.is_valid:
        raise HTTPException(status_code=400, detail="mode must be 'landing' or 'waitlist'")
    supabase.table('app_settings').upsert({
        'key': HOMEPAGE_MODE_KEY,
        'value': body.mode,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }, on_conflict='key').execute()
    _homepage_mode_cache["value"] = body.mode
    _homepage_mode_cache["checked_at"] = datetime.now(timezone.utc)
    return {"mode": body.mode}

@app.get("/multi-currency")
def get_multi_currency_public():
    """Unauthenticated: the site reads this to decide whether to show local currencies or SAR only."""
    return {"enabled": _is_multi_currency_enabled()}

@app.get("/admin/multi-currency")
def get_multi_currency_admin(_=Depends(require_admin)):
    return {"enabled": _is_multi_currency_enabled()}

@app.post("/admin/multi-currency")
def set_multi_currency(body: TestModeRequest, _=Depends(require_admin)):
    supabase.table('app_settings').upsert({
        'key': MULTI_CURRENCY_KEY,
        'value': body.enabled,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }, on_conflict='key').execute()
    _multi_currency_cache["value"] = body.enabled
    _multi_currency_cache["checked_at"] = datetime.now(timezone.utc)
    return {"enabled": body.enabled}

@app.get("/beta-status")
def get_beta_status(request: Request):
    """Unauthenticated — read by the /assessment page to decide between the form and
    the "beta closed" page. `allowed` is true when the caller sent a valid preview secret."""
    closed, _ = _beta_settings()
    return {"closed": closed, "allowed": (not closed) or _beta_preview_allowed(request.headers.get('x-beta-preview'))}

def _beta_admin_payload() -> dict:
    closed, secret = _beta_settings()
    if not secret:
        secret = secrets.token_urlsafe(24)
        _save_beta_setting(BETA_PREVIEW_SECRET_KEY, secret)
    return {"closed": closed, "preview_secret": secret}

def _save_beta_setting(key: str, value) -> None:
    supabase.table('app_settings').upsert({
        'key': key,
        'value': value,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }, on_conflict='key').execute()
    _beta_cache["checked_at"] = None

class BetaClosedRequest(BaseModel):
    closed: bool

@app.get("/admin/beta-closed")
def get_beta_closed_admin(_=Depends(require_admin)):
    _beta_cache["checked_at"] = None
    return _beta_admin_payload()

@app.post("/admin/beta-closed")
def set_beta_closed(body: BetaClosedRequest, _=Depends(require_admin)):
    _beta_admin_payload()  # makes sure a preview secret exists before closing
    _save_beta_setting(BETA_CLOSED_KEY, body.closed)
    return _beta_admin_payload()

@app.post("/admin/beta-closed/regenerate")
def regenerate_beta_preview_secret(_=Depends(require_admin)):
    _save_beta_setting(BETA_PREVIEW_SECRET_KEY, secrets.token_urlsafe(24))
    return _beta_admin_payload()

class AiProviderRequest(BaseModel):
    provider: str

@app.get("/admin/ai-provider")
def get_ai_provider_admin(_=Depends(require_admin)):
    return {"provider": get_ai_provider()}

@app.post("/admin/ai-provider")
def set_ai_provider(body: AiProviderRequest, _=Depends(require_admin)):
    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail="provider must be 'gemini' or 'claude'")
    supabase.table('app_settings').upsert({
        'key': AI_PROVIDER_KEY,
        'value': body.provider,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }, on_conflict='key').execute()
    invalidate_ai_provider_cache()
    return {"provider": body.provider}

@app.get("/admin/country-profiles")
def get_country_profiles(_=Depends(require_admin)):
    data = supabase.table('country_profiles').select('*').order('country_name').execute()
    return data.data

@app.post("/admin/country-profiles")
def create_country_profile(body: dict, _=Depends(require_admin)):
    result = supabase.table('country_profiles').insert(body).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create country profile")
    profile = result.data[0]
    sync_country_profile_embedding(profile['country_code'], profile)
    return profile

@app.put("/admin/country-profiles/{country_code}")
def update_country_profile(country_code: str, body: dict, _=Depends(require_admin)):
    result = supabase.table('country_profiles').update(body).eq('country_code', country_code).execute()
    profile = result.data[0] if result.data else {}
    if profile:
        sync_country_profile_embedding(country_code, profile)
    return profile

@app.delete("/admin/country-profiles/{country_code}")
def delete_country_profile(country_code: str, _=Depends(require_admin)):
    supabase.table('country_profiles').delete().eq('country_code', country_code).execute()
    return {"deleted": country_code}

@app.post("/admin/country-profiles/embed-all")
def embed_all_country_profiles(_=Depends(require_admin)):
    profiles = supabase.table('country_profiles').select('*').execute().data or []
    for p in profiles:
        sync_country_profile_embedding(p['country_code'], p)
    return {"embedded": len(profiles)}

@app.post("/admin/careers/embed-all")
def embed_all_careers(_=Depends(require_admin)):
    careers = supabase.table('careers').select('*').execute().data or []
    for c in careers:
        sync_career_embedding(c['id'], c)
    return {"embedded": len(careers)}

@app.get("/admin/careers")
def get_careers_catalog(_=Depends(require_admin)):
    """Full career catalog with its current approve/reject state — the pool every
    AI recommendation (career-recommendations, ai-impact, courses, companies,
    job-listings) is filtered to `is_approved=True` from. Ordered by title so a
    rejected/re-approved entry doesn't jump around the list between loads.
    Excludes `embedding` — each row's 768-dim vector serializes to several KB of
    JSON, which was bloating this admin list (~200 rows) for no reason since the
    page never uses it."""
    data = _execute_with_retry(supabase.table('careers')
        .select('id,title,sector,riasec,top_values,top_strengths,work_pace,work_sector,'
                'entrepreneurship_friendly,education_fields,is_approved,created_at')
        .order('title'))
    return data.data or []

class CareerApprovalUpdate(BaseModel):
    is_approved: bool

@app.patch("/admin/careers/{career_id}")
def update_career_approval(career_id: str, body: CareerApprovalUpdate, _=Depends(require_admin)):
    result = _execute_with_retry(supabase.table('careers').update({'is_approved': body.is_approved}).eq('id', career_id))
    if not result.data:
        raise HTTPException(status_code=404, detail="Career not found")
    return {"ok": True}

@app.get("/admin/courses")
def get_courses(_=Depends(require_admin)):
    data = supabase.table('courses').select('*').order('created_at', desc=True).execute()
    return data.data or []

@app.post("/admin/courses")
def create_course(body: dict, _=Depends(require_admin)):
    result = supabase.table('courses').insert(body).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create course")
    return result.data[0]

@app.put("/admin/courses/{course_id}")
def update_course(course_id: str, body: dict, _=Depends(require_admin)):
    result = supabase.table('courses').update(body).eq('id', course_id).execute()
    return result.data[0] if result.data else {}

@app.delete("/admin/courses/{course_id}")
def delete_course(course_id: str, _=Depends(require_admin)):
    supabase.table('courses').delete().eq('id', course_id).execute()
    return {"deleted": course_id}

@app.get("/assessment/{response_id}/courses")
def get_course_recommendations(response_id: str, locale: str | None = None, user=Depends(get_optional_user)):
    rows = _execute_with_retry(supabase.table('assessment_results').select('*').eq('response_id', response_id))
    profile = _execute_with_retry(supabase.table('assessment_responses')
        .select('country, education_field, career_direction, sectors_of_interest, experience_level, user_id, current_stage, answers')
        .eq('id', response_id).single())
    if not rows.data or not profile.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    owner_user_id = profile.data.get('user_id')
    _assert_can_view_shared(owner_user_id, user)
    if get_effective_tier(owner_user_id) == "free":
        return []
    summary = build_framework_output(rows.data)
    careers = _execute_with_retry(supabase.table('careers').select('*').eq('is_approved', True)).data or []
    semantic_scores = _get_semantic_scores(response_id, summary, profile.data)
    top5    = _report_order(response_id, score_careers(summary, profile.data, careers, semantic_scores), get_effective_tier(owner_user_id))[:5]

    # Each course is tied to one of the top careers, with what it is about and why it is suggested. An AI picks from
    # the real course list (report_generator.build_course_recommendations); nothing is added just to fill the list.
    from report_generator import build_course_recommendations
    return build_course_recommendations(response_id, summary, profile.data, top5, supabase,
                                        locale if locale in ('en', 'ar') else 'en')

JOB_LISTINGS_CACHE_TTL = timedelta(hours=24)

# GCC currencies are pegged to USD — fixed rates, no live FX API needed
CURRENCY_TO_USD = {
    "SAR": 1 / 3.75,
    "BHD": 1 / 0.376,
    "AED": 1 / 3.6725,
    "QAR": 1 / 3.64,
    "KWD": 1 / 0.3075,
    "OMR": 1 / 0.3845,
    "USD": 1.0,
}
COUNTRY_DEFAULT_CURRENCY = {
    "SA": "SAR", "BH": "BHD", "AE": "AED", "QA": "QAR", "KW": "KWD", "OM": "OMR",
}

def _select_all(query_builder, page_size: int = 1000):
    """PostgREST caps unbounded selects at ~1000 rows — page through with .range() to get everything."""
    rows = []
    offset = 0
    while True:
        page = query_builder().range(offset, offset + page_size - 1).execute().data or []
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return rows

MARKET_ROLE_CATEGORIES = [
    "software engineer", "data analyst", "project manager", "accountant",
    "financial analyst", "marketing manager", "HR manager", "civil engineer",
    "mechanical engineer", "nurse", "doctor", "teacher", "sales manager",
    "operations manager", "supply chain", "business analyst", "architect",
    "cybersecurity", "logistics", "procurement", "legal counsel",
    "graphic designer", "banker", "consultant", "pharmacist",
]

MARKET_COUNTRIES = [
    {"code": "SA", "name": "Saudi Arabia", "query_suffix": "Saudi Arabia", "jooble_location": "Saudi Arabia"},
    {"code": "BH", "name": "Bahrain",      "query_suffix": "Bahrain",      "jooble_location": "Bahrain"},
    {"code": "AE", "name": "UAE",          "query_suffix": "United Arab Emirates", "jooble_location": "United Arab Emirates"},
    {"code": "QA", "name": "Qatar",        "query_suffix": "Qatar",        "jooble_location": "Qatar"},
    {"code": "KW", "name": "Kuwait",       "query_suffix": "Kuwait",       "jooble_location": "Kuwait"},
    {"code": "OM", "name": "Oman",         "query_suffix": "Oman",         "jooble_location": "Oman"},
]

def _get_week_start() -> str:
    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()

@app.post("/admin/market-analysis/fetch")
async def fetch_market_analysis(background_tasks: BackgroundTasks, _=Depends(require_admin)):
    week_start = _get_week_start()
    existing = supabase.table("market_fetch_status").select("status,started_at").eq("week", week_start).execute()
    if existing.data and existing.data[0]["status"] == "running":
        started_at = existing.data[0].get("started_at")
        stale = True
        if started_at:
            started_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            stale = (datetime.now(timezone.utc) - started_dt) > timedelta(minutes=20)
        if not stale:
            return {"week": week_start, "status": "running"}

    supabase.table("market_fetch_status").upsert({
        "week": week_start, "status": "running", "inserted": 0, "errors": 0,
        "insert_error": None, "started_at": datetime.now(timezone.utc).isoformat(), "finished_at": None,
    }, on_conflict="week").execute()

    background_tasks.add_task(_run_market_fetch, week_start)
    return {"week": week_start, "status": "started"}


async def _run_market_fetch(week_start: str):
    import asyncio
    mega_key = os.getenv("JSEARCH_MEGA_KEY")
    jooble_key = os.getenv("JOOBLE_API_KEY")

    def finish(inserted=0, errors=0, insert_error=None):
        supabase.table("market_fetch_status").update({
            "status": "done", "inserted": inserted, "errors": errors,
            "insert_error": insert_error, "finished_at": datetime.now(timezone.utc).isoformat(),
        }).eq("week", week_start).execute()

    if not mega_key and not jooble_key:
        return finish(insert_error="No job source API keys configured (JSEARCH_MEGA_KEY / JOOBLE_API_KEY)")

    try:
        existing_rows = _select_all(lambda: supabase.table("job_market_snapshots").select("job_id").eq("fetched_week", week_start).order("id"))
    except Exception as e:
        print(f"Market fetch aborted before start: {type(e).__name__}: {e!r}")
        return finish(insert_error=f"{type(e).__name__}: {e}")
    seen_ids = {r["job_id"] for r in existing_rows}

    tasks = [(country, role) for country in MARKET_COUNTRIES for role in MARKET_ROLE_CATEGORIES]
    all_rows: list = []
    errors = 0

    async def fetch_jsearch(client: httpx.AsyncClient, country: dict, role: str):
        if not mega_key:
            return []
        for attempt in range(3):
            try:
                resp = await client.get(
                    "https://jsearch-mega.p.rapidapi.com/search",
                    params={"query": f"{role} {country['query_suffix']}", "num_pages": "1", "page": "1"},
                    headers={
                        "X-RapidAPI-Key": mega_key,
                        "X-RapidAPI-Host": "jsearch-mega.p.rapidapi.com",
                    },
                    timeout=12.0,
                )
                if resp.status_code == 429 and attempt < 2:
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
                resp.raise_for_status()
                return [
                    {
                        "job_id": f"jsearch:{j.get('job_id')}",
                        "job_title": j.get("job_title"),
                        "company": j.get("employer_name"),
                        "location": f"{j.get('job_city', '')} {j.get('job_country', '')}".strip(),
                        "salary_min": j.get("job_min_salary"),
                        "salary_max": j.get("job_max_salary"),
                        "salary_currency": j.get("job_salary_currency"),
                        "url": j.get("job_apply_link"),
                    }
                    for j in (resp.json().get("data") or [])[:8] if j.get("job_id")
                ]
            except Exception as e:
                if attempt < 2 and isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429:
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
                print(f"JSearch error [{country['code']}][{role}]: {type(e).__name__}: {e!r}")
                return None

    async def fetch_jooble(client: httpx.AsyncClient, country: dict, role: str):
        if not jooble_key:
            return []
        try:
            resp = await client.post(
                f"https://jooble.org/api/{jooble_key}",
                json={"keywords": role, "location": country["jooble_location"]},
                timeout=12.0,
            )
            resp.raise_for_status()
            return [
                {
                    "job_id": f"jooble:{j.get('id')}",
                    "job_title": j.get("title"),
                    "company": j.get("company"),
                    "location": j.get("location"),
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                    "url": j.get("link"),
                }
                for j in (resp.json().get("jobs") or [])[:8] if j.get("id")
            ]
        except Exception as e:
            print(f"Jooble error [{country['code']}][{role}]: {type(e).__name__}: {e!r}")
            return None

    fatal_error = None
    try:
        async with httpx.AsyncClient() as client:
            # Small batches with a pause between them to stay under free-tier rate limits
            for i in range(0, len(tasks), 3):
                batch = tasks[i:i + 3]
                results = await asyncio.gather(*[
                    asyncio.gather(fetch_jsearch(client, c, r), fetch_jooble(client, c, r))
                    for c, r in batch
                ])
                if i + 3 < len(tasks):
                    await asyncio.sleep(1)
                for (country, role), (jsearch_jobs, jooble_jobs) in zip(batch, results):
                    for jobs in (jsearch_jobs, jooble_jobs):
                        if jobs is None:
                            errors += 1
                            continue
                        for job in jobs:
                            if job["job_id"] in seen_ids:
                                continue
                            seen_ids.add(job["job_id"])
                            all_rows.append({
                                "fetched_week": week_start,
                                "country_code": country["code"],
                                "country_name": country["name"],
                                "role_category": role,
                                **job,
                            })
    except Exception as e:
        print(f"Market fetch loop crashed: {type(e).__name__}: {e!r}")
        fatal_error = f"{type(e).__name__}: {e}"

    inserted = 0
    insert_error = fatal_error
    if all_rows:
        try:
            supabase.table("job_market_snapshots").upsert(all_rows, on_conflict="fetched_week,job_id").execute()
            inserted = len(all_rows)
        except Exception as e:
            print(f"Market snapshot insert failed: {e}")
            insert_error = insert_error or str(e)

    finish(inserted=inserted, errors=errors, insert_error=insert_error)


@app.get("/admin/market-analysis/fetch-status")
def get_market_fetch_status(_=Depends(require_admin)):
    week_start = _get_week_start()
    rows = supabase.table("market_fetch_status").select("*").eq("week", week_start).execute().data
    return rows[0] if rows else {"week": week_start, "status": "none"}

@app.get("/admin/market-analysis/trends")
def get_market_trends(_=Depends(require_admin)):
    rows = _select_all(lambda: supabase.table("job_market_snapshots").select("*").order("fetched_week", desc=False).order("id"))

    # Demand per role/week/country
    demand: dict = {}
    salary: dict = {}
    company_count: dict = {}   # company -> {SA: n, BH: n}
    role_titles: dict = {}     # role_category -> [job_title, ...]

    for r in rows:
        week = r["fetched_week"]
        country = r["country_code"]
        role = r["role_category"]
        key = (week, country, role)

        demand[key] = demand.get(key, 0) + 1

        if r.get("salary_min") or r.get("salary_max"):
            currency = r.get("salary_currency") or COUNTRY_DEFAULT_CURRENCY.get(country)
            rate = CURRENCY_TO_USD.get(currency)
            if rate:
                salary.setdefault(key, [])
                salary[key].extend(v * rate for v in [r.get("salary_min"), r.get("salary_max")] if v)

        company = (r.get("company") or "").strip()
        if company:
            if company not in company_count:
                company_count[company] = {"SA": 0, "BH": 0, "total": 0}
            company_count[company][country] = company_count[company].get(country, 0) + 1
            company_count[company]["total"] += 1

        title = (r.get("job_title") or "").strip()
        if title:
            role_titles.setdefault(role, {})
            role_titles[role][title] = role_titles[role].get(title, 0) + 1

    # Top 20 companies
    top_companies = sorted(
        [{"company": k, **v} for k, v in company_count.items()],
        key=lambda x: x["total"], reverse=True
    )[:20]

    # Top job titles per role (top 3)
    top_titles_by_role = {
        role: sorted(titles.items(), key=lambda x: x[1], reverse=True)[:3]
        for role, titles in role_titles.items()
    }

    # Recent 30 jobs (latest week)
    recent = supabase.table("job_market_snapshots") \
        .select("job_title, company, location, country_code, role_category, url, fetched_week, salary_min, salary_max, salary_currency") \
        .order("fetched_at", desc=True) \
        .limit(50) \
        .execute().data or []

    weeks = sorted({r["fetched_week"] for r in rows})
    roles = sorted({r["role_category"] for r in rows})

    return {
        "weeks": weeks,
        "roles": roles,
        "demand": [{"week": k[0], "country": k[1], "role": k[2], "count": v} for k, v in demand.items()],
        "salary": [{"week": k[0], "country": k[1], "role": k[2], "avg_salary_usd": round(sum(v)/len(v), 0)} for k, v in salary.items()],
        "top_companies": top_companies,
        "top_titles_by_role": top_titles_by_role,
        "recent_jobs": recent,
        "total_snapshots": len(rows),
        "total_companies": len(company_count),
    }

def _search_matching_jobs(response_id: str, ensure_report: bool = True) -> list[dict] | None:
    """Runs the JSearch/RapidAPI query for a response's top-3 matched careers.
    Shared by the on-demand /job-listings endpoint and the Launchpad daily
    job-matching refresh job (which passes ensure_report=False so it never generates a report). Returns None (not []) if the response has no
    scored assessment data to match against."""
    profile = supabase.table('assessment_responses') \
        .select('country, education_field, career_direction, sectors_of_interest, experience_level, current_stage, user_id, answers') \
        .eq('id', response_id).single().execute()
    rows = supabase.table('assessment_results') \
        .select('*') \
        .eq('response_id', response_id).execute()
    if not rows.data or not profile.data:
        return None
    # Uses the country they want to work in (QOTC) instead of where they live, and their study year.
    enrich_profile(profile.data)

    summary = build_framework_output(rows.data)
    careers = supabase.table('careers').select('*').eq('is_approved', True).execute().data or []
    semantic_scores = _get_semantic_scores(response_id, summary, profile.data)
    # The jobs are searched for the careers the report lists first, not the raw ranking.
    top3    = _report_order(response_id, score_careers(summary, profile.data, careers, semantic_scores), get_effective_tier(profile.data.get('user_id')), generate=ensure_report)[:3]

    raw_country = profile.data.get('country', '')
    country = COUNTRY_NAMES.get(raw_country, raw_country)
    country_code = COUNTRY_CODE_MAP.get(raw_country)
    # "Early career" is a current_stage (QO4) signal, not experience_level
    # (QO3B) — QO3B only asks actual years of experience for people who have
    # some, so it can't signal "no experience yet" on its own.
    is_early_career = profile.data.get('current_stage') in ENTERING_MARKET_STAGES
    # Still-enrolled users (high school/university) can't act on most "entry
    # level" job postings either — they need internships, not jobs. A fresh
    # grad who has already left school (current_stage == recent_graduate)
    # still gets real entry-level jobs via the is_early_career branch above.
    is_still_enrolled = profile.data.get('current_stage') in STILL_ENROLLED_STAGES
    rapidapi_key = os.getenv("RAPIDAPI_KEY")

    all_jobs = []
    seen_ids = set()

    # Recent graduates get entry-level jobs plus internships (one extra internship search for
    # their top career); still-enrolled users get internships only; everyone else regular jobs.
    # Final-year and postgraduate students are about to enter the market, so they also get entry-level jobs
    # (one extra search for their top career) alongside their internships.
    final_year_student = profile.data.get('current_stage') == 'university' and profile.data.get('study_year') in ('final_year', 'postgraduate', 'extended')
    searches = [(career, is_still_enrolled) for career in top3]
    if is_early_career and top3:
        searches.append((top3[0], True))
    if final_year_student and top3:
        searches.append((top3[0], False))
    per_search = 3 if (is_early_career or final_year_student) else 4
    # Highest education level we know they have: a graduate or a university student (about to have a bachelor's)
    # = bachelor's, a postgraduate student = postgraduate. Working users: unknown, so no education filter.
    stage_now = profile.data.get('current_stage')
    if stage_now == 'recent_graduate':
        user_education_rank = EDUCATION_RANK['bachelors']
    elif stage_now == 'university':
        user_education_rank = EDUCATION_RANK['postgraduate'] if profile.data.get('study_year') == 'postgraduate' else EDUCATION_RANK['bachelors']
    else:
        user_education_rank = None

    for career, internship_mode in searches:
        try:
            if internship_mode:
                query_prefix = "internship "
                job_requirements = None  # "internship" is not a valid job_requirements value (JSearch answers 400); use employment_types instead
            elif is_early_career or final_year_student:
                query_prefix = "entry level graduate "
                job_requirements = "under_3_years_experience,no_experience,no_degree"
            else:
                query_prefix = ""
                job_requirements = None
            def _jsearch(prefix: str, requirements):
                r = httpx.get(
                    "https://jsearch.p.rapidapi.com/search",
                    params={
                        "query": f"{prefix}{career['title']} {country}",
                        "num_pages": "1",
                        "page": "1",
                        **({"country": country_code.lower()} if country_code else {}),
                        # Bias JSearch's own results toward entry-level/internship
                        # postings for students/fresh grads rather than relying
                        # only on the post-fetch title/description filter below.
                        **({"job_requirements": requirements} if requirements else {}),
                        **({"employment_types": "INTERN"} if internship_mode else {}),
                    },
                    headers={
                        "X-RapidAPI-Key": rapidapi_key,
                        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                    },
                    timeout=8.0,
                )
                r.raise_for_status()
                return r
            resp = _jsearch(query_prefix, job_requirements)
            # In smaller markets (Bahrain) the entry-level wording plus the JSearch requirements filter can match
            # nothing at all while the plain query finds plenty. The senior-title, freshness and requirements filters
            # below still keep only suitable postings, so retry once without that narrowing.
            if job_requirements and not (resp.json().get("data") or []):
                resp = _jsearch("", None)
            # Take the first `per_search` listings that pass the filters (not the first few raw results, which
            # the freshness / requirement filters below may all reject).
            kept_from_search = 0
            for job in (resp.json().get("data") or []):
                if kept_from_search >= per_search:
                    break
                job_id = job.get("job_id")
                job_title = job.get("job_title")
                employer_name = job.get("employer_name")
                job_country = job.get("job_country")
                if not is_appropriate(job_title, employer_name, job.get("job_description")):
                    continue
                if not is_region_eligible(job_title, job.get("job_description"), job_country, country_code):
                    continue
                # Internship postings are inherently entry-level, so the
                # senior-title filter (built for regular job postings) doesn't
                # apply to them.
                if not internship_mode and not is_seniority_appropriate(job_title, job.get("job_description"), is_early_career or final_year_student):
                    continue
                # Drop stale or expired postings, and ones that ask for more education or experience than they have.
                if not is_job_fresh(job):
                    continue
                req = parse_job_requirements(job)
                if internship_mode:
                    exp_cap = MAX_EXPERIENCE_MONTHS_INTERNSHIP
                elif is_early_career or final_year_student:
                    exp_cap = MAX_EXPERIENCE_MONTHS_EARLY_CAREER
                else:
                    exp_cap = None
                if not meets_requirements(req, user_education_rank, exp_cap):
                    continue
                if job_id and job_id not in seen_ids:
                    seen_ids.add(job_id)
                    kept_from_search += 1
                    all_jobs.append({
                        "job_id": job_id,
                        "title": job_title,
                        "company": employer_name,
                        "location": f"{job.get('job_city', '')} {job.get('job_country', '')}".strip(),
                        "source": job.get("job_publisher"),
                        "url": job.get("job_apply_link"),
                        "matched_career": career['title'],
                        "is_internship": internship_mode,
                        "posted_at": job_posted_date(job),
                        "requires_education": req["education"],
                        "requires_experience_months": req["experience_months"],
                    })
        except Exception as e:
            print("JSearch error:", e)
            continue

    return all_jobs[:12]


@app.get("/assessment/{response_id}/job-listings")
def get_job_listings(response_id: str, force: bool = False, user=Depends(get_optional_user)):
    owner_row = _execute_with_retry(supabase.table('assessment_responses').select('user_id,current_stage').eq('id', response_id).single())
    if not owner_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    _assert_can_view_shared(owner_row.data.get('user_id'), user)
    if force:
        _assert_can_force_refresh(owner_row.data.get('user_id'), user)
    # High-school users see majors and courses instead — no jobs or internships (and no JSearch spend).
    if owner_row.data.get('current_stage') in NO_LISTINGS_STAGES:
        return {"jobs": []}

    # The apply links are part of the paid plan. Free users still get title / company / source (the page shows
    # them as a blurred teaser), but never the link — the UI blur alone is not a paywall.
    is_free_viewer = not _is_admin(user) and get_effective_tier(owner_row.data.get('user_id')) == "free"
    def _visible(jobs: list) -> dict:
        if is_free_viewer:
            jobs = [{k: v for k, v in j.items() if k != 'url'} for j in jobs]
        return {"jobs": jobs}

    cached = _execute_with_retry(supabase.table('job_listings_cache').select('*').eq('response_id', response_id))
    if cached.data and not force:
        fetched_at = datetime.fromisoformat(cached.data[0]['fetched_at'])
        if datetime.now(timezone.utc) - fetched_at < JOB_LISTINGS_CACHE_TTL:
            return _visible(cached.data[0]['jobs'])

    result_jobs = _search_matching_jobs(response_id)
    if result_jobs is None:
        raise HTTPException(status_code=404, detail="No results found for this response")

    _execute_with_retry(supabase.table('job_listings_cache').upsert({
        'response_id': response_id,
        'jobs': result_jobs,
        'fetched_at': datetime.now(timezone.utc).isoformat(),
    }))

    return _visible(result_jobs)


@app.post("/internal/jobs/refresh-matches")
def refresh_job_matches(request: Request):
    """Daily job-matching refresh for Launchpad subscribers. Called by a VPS
    crontab entry (not a browser), authenticated with a shared secret rather
    than a user session — see the manual-deployment note for the cron entry."""
    if not INTERNAL_JOBS_KEY or not hmac.compare_digest(request.headers.get("X-Internal-Key", ""), INTERNAL_JOBS_KEY):
        raise HTTPException(status_code=401, detail="Invalid internal key")

    plans = supabase.table('user_plans') \
        .select('user_id, subscription_current_period_end') \
        .not_.is_('subscription_current_period_end', 'null') \
        .execute()
    now = datetime.now(timezone.utc)
    launchpad_user_ids = [
        p['user_id'] for p in (plans.data or [])
        if datetime.fromisoformat(p['subscription_current_period_end']) > now
    ]

    inserted = 0
    for user_id in launchpad_user_ids:
        latest = supabase.table('assessment_responses') \
            .select('id') \
            .eq('user_id', user_id) \
            .eq('completed', True) \
            .order('created_at', desc=True) \
            .limit(1).execute()
        if not latest.data:
            continue
        response_id = latest.data[0]['id']

        jobs = _search_matching_jobs(response_id, ensure_report=False) or []
        existing_ids = {
            row['job_data'].get('job_id')
            for row in (supabase.table('job_matches').select('job_data').eq('user_id', user_id).execute().data or [])
        }
        new_jobs = [j for j in jobs if j.get('job_id') not in existing_ids]
        for job in new_jobs:
            supabase.table('job_matches').insert({
                'user_id': user_id,
                'response_id': response_id,
                'job_data': job,
            }).execute()
        inserted += len(new_jobs)

    return {"users_checked": len(launchpad_user_ids), "jobs_inserted": inserted}


JOB_MATCHES_RETRY_TTL = timedelta(hours=6)

@app.get("/jobs/my-matches")
def get_my_job_matches(user=Depends(get_current_user)):
    if get_effective_tier(user.id) != "launchpad":
        return []

    data = supabase.table('job_matches') \
        .select('*') \
        .eq('user_id', user.id) \
        .order('matched_at', desc=True) \
        .execute()
    rows = data.data or []
    real_rows = [r for r in rows if not r['job_data'].get('_no_results')]
    if real_rows:
        return real_rows

    # No real matches yet — either the daily cron hasn't run for this user yet
    # (fresh Launchpad subscriber) or tier access came from test mode rather
    # than a real subscription (test mode never appears in the cron's
    # subscriber list). Fetch on demand instead of making them wait.
    #
    # If the last attempt (real or empty) was recent, don't retry — every
    # dashboard reload calls this endpoint, and test-mode walkthroughs in
    # particular reload far more often than a real subscriber would, which
    # would otherwise burn the JSearch/RapidAPI quota on repeat empty results.
    if rows:
        last_attempt = datetime.fromisoformat(rows[0]['matched_at'])
        if datetime.now(timezone.utc) - last_attempt < JOB_MATCHES_RETRY_TTL:
            return []

    latest = supabase.table('assessment_responses') \
        .select('id') \
        .eq('user_id', user.id) \
        .eq('completed', True) \
        .order('created_at', desc=True) \
        .limit(1).execute()
    if not latest.data:
        return []

    jobs = _search_matching_jobs(latest.data[0]['id'], ensure_report=False) or []
    if not jobs:
        supabase.table('job_matches').insert({
            'user_id': user.id,
            'response_id': latest.data[0]['id'],
            'job_data': {'_no_results': True},
        }).execute()
        return []

    inserted = []
    for job in jobs:
        row = supabase.table('job_matches').insert({
            'user_id': user.id,
            'response_id': latest.data[0]['id'],
            'job_data': job,
        }).execute()
        if row.data:
            inserted.append(row.data[0])
    return inserted


@app.get("/assessment/my-assessments")
def get_my_assessments(user=Depends(get_current_user)):
    responses = supabase.table('assessment_responses') \
        .select('id, full_name, country, completed, created_at, locale') \
        .eq('user_id', user.id) \
        .eq('completed', True) \
        .order('created_at', desc=True) \
        .execute()

    items = []
    for r in (responses.data or []):
        top_type = None
        rows = supabase.table('assessment_results').select('*').eq('response_id', r['id']).execute()
        if rows.data:
            summary = build_framework_output(rows.data)
            top_types = summary.get('riasec', {}).get('top_types') or []
            top_type = top_types[0] if top_types else None
        items.append({**r, 'top_type': top_type})
    return items


@app.get("/applications")
def list_applications(user=Depends(get_current_user)):
    data = supabase.table('applications') \
        .select('*') \
        .eq('user_id', user.id) \
        .order('created_at', desc=True) \
        .execute()
    return data.data or []


@app.post("/applications")
def create_application(body: ApplicationCreate, user=Depends(get_current_user)):
    row = {**body.model_dump(), "user_id": user.id, "status": "saved"}
    result = supabase.table('applications').insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to save application")
    return result.data[0]


@app.patch("/applications/{application_id}")
def update_application(application_id: str, body: ApplicationUpdate, user=Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if 'status' in updates:
        if updates['status'] not in APPLICATION_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        if updates['status'] == 'applied':
            updates['applied_at'] = datetime.now(timezone.utc).isoformat()
    result = supabase.table('applications') \
        .update(updates) \
        .eq('id', application_id) \
        .eq('user_id', user.id) \
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Application not found")
    return result.data[0]


@app.delete("/applications/{application_id}")
def delete_application(application_id: str, user=Depends(get_current_user)):
    supabase.table('applications').delete().eq('id', application_id).eq('user_id', user.id).execute()
    return {"deleted": application_id}

@app.get("/assessment/{response_id}/companies")
def get_companies_suggestions(response_id: str, user=Depends(get_optional_user)):
    profile = _execute_with_retry(supabase.table('assessment_responses')
        .select('country, education_field, career_direction, sectors_of_interest, experience_level, user_id, current_stage, answers')
        .eq('id', response_id).single())
    rows = _execute_with_retry(supabase.table('assessment_results')
        .select('*')
        .eq('response_id', response_id))
    if not rows.data or not profile.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    enrich_profile(profile.data)  # country to work in (QOTC)
    owner_user_id = profile.data.get('user_id')
    _assert_can_view_shared(owner_user_id, user)
    tier = get_effective_tier(owner_user_id)
    if tier == "free":
        return []
    # The employer target list is for graduates and working users, not students.
    if profile.data.get('current_stage') in NO_COMPANIES_STAGES:
        return []
    company_limit = 50 if tier == "launchpad" else 20

    summary = build_framework_output(rows.data)
    careers = _execute_with_retry(supabase.table('careers').select('*').eq('is_approved', True)).data or []
    semantic_scores = _get_semantic_scores(response_id, summary, profile.data)
    top5    = score_careers(summary, profile.data, careers, semantic_scores)[:5]

    sectors = list(dict.fromkeys(c['sector'] for c in top5))
    country_code = COUNTRY_CODE_MAP.get(profile.data.get('country', ''))

    query = supabase.table('companies').select(
        'id, name_en, sector, size, is_government, career_page_url, logo_url, country_code'
    )
    if country_code:
        query = query.eq('country_code', country_code)
    if sectors:
        query = query.in_('sector', sectors)

    result = _execute_with_retry(query.order('name_en').limit(company_limit))
    return [c for c in (result.data or []) if is_appropriate(c.get('name_en'), c.get('sector'))]

def _claim_token(response_id: str) -> str:
    """Proof that a browser took this assessment: an HMAC of the response id with a server secret. It is handed back
    only in the submit response (the browser keeps it), so someone who merely holds a shared report link cannot
    compute it. Stateless, so no database column is needed."""
    secret = os.getenv("CLAIM_TOKEN_SECRET") or HUB_API_KEY or os.getenv("SUPABASE_KEY")
    if not secret:   # never sign with an empty key: the token would be guessable
        return ""
    return hmac.new(secret.encode(), f"claim:{response_id}".encode(), hashlib.sha256).hexdigest()[:40]

def _claim_response(user, response_id: str | None, token: str | None) -> int:
    """Attaches an unowned report to this account when the claim token is valid. Returns how many rows changed."""
    expected = _claim_token(str(response_id)) if response_id else ""
    if not expected or not token or not hmac.compare_digest(expected, str(token)):
        return 0
    result = supabase.table('assessment_responses').update({"user_id": user.id}) \
        .eq('id', str(response_id)).is_('user_id', 'null').execute()
    return len(result.data or [])

class ClaimRequest(BaseModel):
    token: str = Field(max_length=100)

@app.post("/assessment/{response_id}/claim")
def claim_assessment(response_id: str, body: ClaimRequest, user=Depends(get_current_user)):
    """Saves the report this browser just took to the account it signed up or signed in with, even when the account
    email differs from the email typed in the assessment (link-by-email only matches equal emails)."""
    return {"linked": _claim_response(user, response_id, body.token)}

@app.post("/assessment/link-by-email")
def link_by_email(user=Depends(get_current_user)):
    # Escape ILIKE wildcards in the email so a "_" (a valid, common local-part
    # character) or "%" can't widen the match to someone else's response —
    # this must stay case-insensitive (ilike, not eq) since assessment emails
    # aren't consistently lowercased at submit time.
    safe_email = (user.email or '').replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    result = supabase.table('assessment_responses') \
        .update({"user_id": user.id}) \
        .ilike('email', safe_email) \
        .is_('user_id', 'null') \
        .execute()
    linked = len(result.data or [])
    # A claim made at sign-up travels in the account's metadata, so it still works when the confirmation email is
    # opened in a different browser from the one that took the assessment.
    claim = (user.user_metadata or {}).get("claim") or {}
    if isinstance(claim, dict):
        linked += _claim_response(user, claim.get("response_id"), claim.get("token"))
    return {"linked": linked}

@app.get("/admin/coaching-sessions")
def list_coaching_sessions(user=Depends(require_admin)):
    result = supabase.table("coaching_sessions") \
        .select("id, client_label, topic, session_date, created_at") \
        .order("created_at", desc=True) \
        .execute()
    return result.data or []

@app.post("/admin/coaching-sessions")
def create_coaching_session(
    payload: coachingSessionRequest,
    user=Depends(require_admin),
):
    result = supabase.table("coaching_sessions").insert({
        "client_label": payload.client_label,
        "topic": payload.topic,
        "session_date": payload.session_date,
        "raw_transcript": payload.raw_transcript,
    }).execute()
    session = result.data[0]

    chunks = chunk_transcript(payload.raw_transcript)
    embed_and_store_chunks(session["id"], chunks)

    return {"session_id": session["id"], "chunks_created": len(chunks)}

@app.post("/coach")
def coach(payload: CoachRequest, user=Depends(get_current_user)):
    if get_effective_tier(user.id) == "free" and not _is_admin(user):
        raise HTTPException(status_code=403, detail="The AI coach is part of the paid plans")
    query_embedding = _gemini_embed(payload.message)

    matches = supabase.rpc("match_coaching_chunks", {
        "query_embedding": query_embedding,
        "match_count": 5,
    }).execute().data

    country_matches = supabase.rpc("match_country_profiles", {
        "query_embedding": query_embedding,
        "match_count": 2,
    }).execute().data or []

    examples = "\n\n".join(
        f"Situation: {m['situation']}\nCoach response: {m['coach_response']}"
        for m in matches
    )

    country_context = ""
    if country_matches:
        country_context = "\n\nRelevant country labour market context:\n" + "\n\n".join(
            f"Country: {c['country_name']}\n"
            f"Context tier: {c.get('context_tier', '')}\n"
            f"Labour market authority: {c.get('labour_market_authority', '')}\n"
            f"Nationalisation programme: {c.get('nationalisation_programme', '')}\n"
            f"Strategic priorities: {json.dumps(c.get('strategic_priorities') or {})}"
            for c in country_matches
        )

    system_prompt = f"{WRITING_RULES}{METHODOLOGY_DOC}\n\n{CULTURAL_GUARDRAIL}\n\nRelevant past examples:\n{examples}{country_context}"

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=payload.conversation_history + [{"role": "user", "content": payload.message}],
            timeout=30.0,
        )
    except Exception as e:
        send_failure_alert("AI Coach chat", e, user_email=user.email, user_name=(user.user_metadata or {}).get("full_name"), supabase=supabase)
        # See the AI Impact generation handler above for why this is an
        # HTTPException rather than a bare `raise`.
        raise HTTPException(status_code=500, detail="AI Coach is temporarily unavailable, please try again.")
    return {"reply": response.content[0].text}


class CoachChatRequest(BaseModel):
    mode: Literal["assessment", "results", "landing"]
    message: str = Field(min_length=1, max_length=500)
    history: list[dict] = Field(default_factory=list, max_length=12)
    locale: Literal["en", "ar"] = "en"
    # results mode: which report is being viewed. assessment mode: a random per-browser session id (rate limiting only).
    response_id: str | None = Field(default=None, max_length=64)
    session_id: str | None = Field(default=None, max_length=64)
    question_index: int | None = Field(default=None, ge=1, le=500)
    question_total: int | None = Field(default=None, ge=1, le=500)
    # The question currently on screen (assessment mode), so Sarah can explain it. Public assessment wording only.
    question_text: str | None = Field(default=None, max_length=600)
    question_type: str | None = Field(default=None, max_length=30)
    question_options: list[str] | None = Field(default=None, max_length=10)

@app.post("/coach/chat")
def coach_chat(payload: CoachChatRequest, request: Request, user=Depends(get_optional_user)):
    """Two-way coach bubble (Gemini). See coach_chat.py: assessment mode gets no user data, results mode gets
    only the profile summary every tier already sees. Not the paid /coach (Claude + coaching library)."""
    # Behind Traefik the LAST X-Forwarded-For entry is the one the proxy appended; earlier ones are client-supplied.
    ip = _client_ip(request)
    if not coach_chat_mod.check_rate_limit(f"ip:{ip}", coach_chat_mod.LIMIT_PER_IP):
        raise HTTPException(status_code=429, detail="Too many messages, please try again later.")

    tier, summary = "free", None
    if payload.mode == "results":
        if not payload.response_id:
            raise HTTPException(status_code=400, detail="response_id is required in results mode")
        if not coach_chat_mod.check_rate_limit(f"resp:{payload.response_id}", coach_chat_mod.LIMIT_RESULTS_RESPONSE):
            raise HTTPException(status_code=429, detail="Too many messages, please try again later.")
        profile = _execute_with_retry(supabase.table('assessment_responses')
            .select('user_id').eq('id', payload.response_id).single())
        if not profile.data:
            raise HTTPException(status_code=404, detail="No results found for this response")
        rows = _execute_with_retry(supabase.table('assessment_results')
            .select('framework, dimension, normalized_score').eq('response_id', payload.response_id))
        if not rows.data:
            raise HTTPException(status_code=404, detail="No results found for this response")
        summary = build_framework_output(rows.data)
        tier = "launchpad" if _is_admin(user) else get_effective_tier(profile.data.get('user_id'))
    elif payload.mode == "landing":
        if not payload.session_id:
            raise HTTPException(status_code=400, detail="session_id is required in landing mode")
        if not coach_chat_mod.check_rate_limit(f"land:{payload.session_id}", coach_chat_mod.LIMIT_LANDING_SESSION):
            return {"reply": None, "limited": True}
    else:
        if not payload.session_id:
            raise HTTPException(status_code=400, detail="session_id is required in assessment mode")
        if not coach_chat_mod.check_rate_limit(f"sess:{payload.session_id}", coach_chat_mod.LIMIT_ASSESSMENT_SESSION):
            # Not an error the user needs to see as one: the coach just stops chatting for now.
            return {"reply": None, "limited": True}

    try:
        reply = coach_chat_mod.generate_reply(payload.mode, payload.message, payload.history, payload.locale, tier, summary,
                                              (payload.question_index, payload.question_total) if payload.question_index and payload.question_total else None,
                                              {"text": payload.question_text, "type": payload.question_type, "options": payload.question_options}
                                              if payload.mode == "assessment" and payload.question_text else None)
    except Exception as e:
        print("Coach chat failed:", repr(e))
        raise HTTPException(status_code=503, detail="The coach is unavailable right now.")
    return {"reply": reply, "limited": False}


@app.post("/billing/checkout")
def create_checkout(body: CheckoutRequest, request: Request, user=Depends(get_current_user)):
    _save_checkout_context(user.id, request, body.fbp, body.fbc)
    plan = PLAN_CATALOG.get(body.plan_code)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Unknown plan_code: {body.plan_code}")
    if not plan.get("available", True):
        raise HTTPException(status_code=400, detail=f"{plan['name']} isn't available yet")
    # The paid report is built from an assessment, so nobody goes to the gateway before taking one
    # (an assessment taken before signing up counts when it was made with the same email).
    owned = supabase.table('assessment_responses').select('id').eq('user_id', user.id).limit(1).execute()
    if not owned.data and user.email:
        safe_email = user.email.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')  # ILIKE wildcards
        owned = supabase.table('assessment_responses').select('id').ilike('email', safe_email).limit(1).execute()
    if not owned.data:
        raise HTTPException(status_code=400, detail="assessment_required")

    full_name = (user.user_metadata or {}).get("full_name", "") or ""
    first_name, _, last_name = full_name.strip().partition(" ")

    # SAR unless the admin multi-currency switch is on and the buyer asked for a currency we have a price for.
    # PATHFINDER_TEST_AMOUNT (payment testing) always wins, so test charges never change currency.
    charge_amount, charge_currency = plan["amount"], plan["currency"]
    # Adding Launchpad on top of an existing Pathfinder purchase costs the upgrade price, not the package price.
    upgrade = body.plan_code == "launchpad_monthly" and not _test_amount and _owns_pathfinder(user.id)
    if upgrade:
        charge_amount = LAUNCHPAD_UPGRADE_SAR
    wanted = (body.currency or "").upper()
    if not _test_amount and wanted != charge_currency and _is_multi_currency_enabled():
        local = (LAUNCHPAD_UPGRADE_LOCAL if upgrade else LOCAL_PRICES.get(body.plan_code, {})).get(wanted)
        if local is not None:
            charge_amount, charge_currency = local, wanted

    payload = {
        "external_user_id": user.id,
        "first_name": first_name or "Customer",
        "last_name": last_name or "Account",
        "email": user.email,
        "plan_code": body.plan_code,
        "plan_name": plan["name"],
        "amount": charge_amount,
        "currency": charge_currency,
        # Back to the page language the buyer was using (the frontend sends /<locale>/account/billing on to the dashboard)
        "return_url": BILLING_RETURN_URL.replace("/account/billing", f"/{body.locale if body.locale in ('en', 'ar') else 'en'}/account/billing"),
    }

    try: 
        resp = httpx.post(
            f"{SHOP_BASE_URL}/api/hub/orders",
            json=payload,
            headers={"Authorization": f"Bearer {HUB_API_KEY}"},
            timeout=15.0,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        print("Shop rejected the order:", e.response.status_code, e.response.text[:500])   # details stay in the logs, not the response
        raise HTTPException(status_code=502, detail="The payment page could not be created. Please try again.")
    except httpx.RequestError as e:
        print("Could not reach Shop:", e)
        raise HTTPException(status_code=502, detail="The payment page could not be created. Please try again.")

    checkout_url = resp.json().get("checkout_url")
    if not checkout_url:
        raise HTTPException(status_code=502, detail="Shop response did not include a checkout_url")

    return {"checkout_url": checkout_url}


@app.get("/billing/transaction")
def get_my_transaction(user=Depends(get_current_user)):
    data = supabase.table('transactions') \
        .select('*') \
        .eq('user_id', user.id) \
        .order('created_at', desc=True) \
        .execute()
    return data.data or []


@app.get("/billing/plan")
def get_my_plan(user=Depends(get_current_user)):
    row = supabase.table('user_plans').select('*').eq('user_id', user.id).execute()
    plan = row.data[0] if row.data else {}
    tier = get_effective_tier(user.id)
    return {
        "tier": tier,
        "pathfinder_unlocked": bool(plan.get('pathfinder_unlocked')),
        "pathfinder_unlocked_at": plan.get('pathfinder_unlocked_at'),
        "subscription_plan_code": plan.get('subscription_plan_code'),
        "subscription_status": "active" if tier == "launchpad" else ("expired" if plan.get('subscription_current_period_end') else None),
        "subscription_current_period_end": plan.get('subscription_current_period_end'),
        # Replaced by our own scheduling (the /coaching/* endpoints below); no longer a Calendly link.
        # "booking_url": _coaching_booking_url(user) if tier == "launchpad" else None,
    }

def _academy_coaching(method: str, path: str, user, *, params: dict | None = None, json_body: dict | None = None):
    """Calls the academy's coaching API on behalf of a Launchpad user (identified by email). Raises HTTPException."""
    if get_effective_tier(user.id) != "launchpad":
        raise HTTPException(status_code=403, detail="launchpad_required")
    if not HUB_API_KEY:
        raise HTTPException(status_code=500, detail="HUB_API_KEY is not configured")
    try:
        resp = httpx.request(method, f"{ACADEMY_BASE_URL}/api/hub/coaching{path}",
                             params={**(params or {}), **({"email": user.email} if method == "GET" else {})},
                             json=({**json_body, "email": user.email} if json_body is not None else None),
                             headers={"Authorization": f"Bearer {HUB_API_KEY}"}, timeout=20.0)
    except httpx.RequestError as e:
        print("academy coaching request failed:", e)
        raise HTTPException(status_code=502, detail="coaching_unavailable")
    if resp.status_code == 409:
        raise HTTPException(status_code=409, detail=resp.json().get("error", "conflict"))
    if resp.status_code >= 400:
        print("academy coaching error:", resp.status_code, resp.text[:300])
        raise HTTPException(status_code=502, detail="coaching_unavailable")
    return resp.json()

class CoachingBookRequest(BaseModel):
    start: str = Field(max_length=40)

class CoachingCancelRequest(BaseModel):
    booking_id: int

@app.get("/coaching/status")
def coaching_status(user=Depends(get_current_user)):
    """Sessions left and the user's upcoming sessions (with their Meet link)."""
    return _academy_coaching("GET", "", user)

@app.get("/coaching/slots")
def coaching_slots(date_from: str | None = None, date_to: str | None = None, user=Depends(get_current_user)):
    """Free start times (UTC ISO) for the user's next coaching session."""
    params = {k: v for k, v in {"from": date_from, "to": date_to}.items() if v}
    return _academy_coaching("GET", "/slots", user, params=params)

@app.post("/coaching/book")
def coaching_book(body: CoachingBookRequest, user=Depends(get_current_user)):
    return _academy_coaching("POST", "/book", user, json_body={"start": body.start})

@app.post("/coaching/cancel")
def coaching_cancel(body: CoachingCancelRequest, user=Depends(get_current_user)):
    return _academy_coaching("POST", "/cancel", user, json_body={"booking_id": body.booking_id})

def _coaching_booking_url(user) -> str | None:
    """Scheduling link for the Launchpad coaching session (COACHING_BOOKING_URL, e.g. a Calendly event link), with the
    buyer's name and email prefilled and their user id in utm_content so the booking can be matched to them.
    None when no link is configured (the dashboard then shows the contact details instead)."""
    base = (os.getenv("COACHING_BOOKING_URL") or "").strip()
    if not base:
        return None
    from urllib.parse import urlencode
    # The booking is matched to an academy coaching purchase (utm_content=purchase_<id>), so the buyer must have
    # one with sessions left. None otherwise (or if the academy is unreachable): the dashboard shows contact details.
    try:
        r = httpx.get(f"{ACADEMY_BASE_URL}/api/hub/coaching", params={"email": user.email},
                      headers={"Authorization": f"Bearer {HUB_API_KEY}"}, timeout=8.0).json()
    except Exception as e:
        print("academy coaching lookup failed:", e)
        return None
    if not r.get("purchase_id"):
        return None
    name = (user.user_metadata or {}).get("full_name", "") or ""
    params = {"embed_domain": "myetijahi.com", "embed_type": "Inline", "hide_gdpr_banner": "1",
              "utm_source": "etijahi", "utm_content": f"purchase_{r['purchase_id']}"}
    if name:
        params["name"] = name
    if user.email:
        params["email"] = user.email
    return base + ("&" if "?" in base else "?") + urlencode(params)

def _invalidate_free_tier_report_cache(user_id: str):
    """Called whenever a user's tier upgrades off 'free'. Their assessment_responses rows
    may already hold a free-tier-sized AI report cache (fewer careers/AI-impact items than
    a paid report should show) — nulling it out forces report_generator.create_report() and
    GET /assessment/{id}/ai-impact to regenerate at full size on the next request."""
    supabase.table('assessment_responses').update({
        'ai_impact_cache_free': None,
        'ai_content_cache_free': None,
        'ai_impact_cache_ar_free': None,
        'ai_content_cache_ar_free': None,
    }).eq('user_id', user_id).execute()

def _full_report_ready_email(name: str | None, url: str, locale: str) -> tuple[str, str]:
    import html as _h
    first = _h.escape((name or '').strip().split(' ')[0])
    if locale == 'ar':
        subject = "تقريرك الكامل من إتجاهي جاهز"
        body = (f'<div dir="rtl" style="font-family:Arial,sans-serif;font-size:15px;color:#1f2937;line-height:1.7">'
                f'<p>مرحباً {first}،</p><p>شكراً لك. تقريرك الكامل جاهز الآن، ويشمل الخطة والدورات والشهادات وتحليل تأثير الذكاء الاصطناعي.</p>'
                f'<p><a href="{url}" style="display:inline-block;background:#0770ba;color:#fff;padding:11px 20px;border-radius:10px;text-decoration:none">افتح تقريرك الكامل</a></p>'
                f'<p>فريق إتجاهي</p></div>')
    else:
        subject = "Your full Etijahi report is ready"
        body = (f'<div style="font-family:Arial,sans-serif;font-size:15px;color:#1f2937;line-height:1.7">'
                f'<p>Hi {first},</p><p>Thank you. Your full report is ready, including your plan, courses, certifications and the AI-impact analysis.</p>'
                f'<p><a href="{url}" style="display:inline-block;background:#0770ba;color:#fff;padding:11px 20px;border-radius:10px;text-decoration:none">Open your full report</a></p>'
                f'<p>The Etijahi team</p></div>')
    return subject, body

def _notify_coaching_purchase(user_id: str, amount, currency: str):
    """Tells the team a Launchpad buyer is waiting for their 1:1 coaching session, so nobody falls through the cracks.
    Best-effort: a failure here never affects the payment."""
    try:
        name = email = phone = ''
        try:
            u = supabase.auth.admin.get_user_by_id(user_id).user
            email = getattr(u, 'email', '') or ''
            phone = getattr(u, 'phone', '') or ''
            name = (getattr(u, 'user_metadata', None) or {}).get('full_name', '') or ''
        except Exception:
            pass
        import html as _h
        name, email, phone = _h.escape(name), _h.escape(email), _h.escape(phone)
        html = (f'<p>A customer bought <b>Launchpad</b> and is owed a 1:1 coaching session.</p>'
                f'<p>Name: {name or "—"}<br>Email: {email or "—"}<br>Phone: {phone or "—"}<br>'
                f'Paid: {amount} {currency}<br>User id: {user_id}</p><p>Please contact them to book the session.</p>')
        send_email(to=ADMIN_ALERT_EMAIL, subject="New Launchpad purchase: book the coaching session", html_body=html, supabase=supabase)
    except Exception as e:
        print("coaching purchase notification failed:", e)

def _create_academy_coaching_purchase(user_id: str, order_ref: str):
    """Gives a Launchpad buyer their 1:1 coaching entitlement in the Etijah academy (idempotent per order_ref).
    Best-effort: a failure here never affects the payment."""
    try:
        u = supabase.auth.admin.get_user_by_id(user_id).user
        httpx.post(f"{ACADEMY_BASE_URL}/api/hub/coaching-purchases",
                   json={"email": u.email, "name": (getattr(u, 'user_metadata', None) or {}).get("full_name", ""),
                         "order_ref": order_ref},
                   headers={"Authorization": f"Bearer {HUB_API_KEY}"}, timeout=15.0).raise_for_status()
    except Exception as e:
        print("academy coaching purchase failed:", e)

_prewarm_inflight: set[str] = set()

def _prewarm_full_report(user_id: str):
    """Runs after a successful payment (background task): builds the buyer's full report right away, in the
    report's language, so it is mostly ready by the time they open it, then emails them the link. Everything it
    saves is the same cache the results page and PDF use, so nothing is generated twice (see single_flight).
    Best-effort: a failure alerts the admin and the report is simply built the first time it is opened."""
    rid = None
    try:
        rows = supabase.table('assessment_responses').select('id,locale,email,full_name') \
            .eq('user_id', user_id).order('created_at', desc=True).limit(1).execute()
        if not rows.data:
            return
        row = rows.data[0]
        rid = row['id']
        locale = row.get('locale') if row.get('locale') in ('en', 'ar') else 'en'
        if rid in _prewarm_inflight:
            return
        _prewarm_inflight.add(rid)
        try:
            create_report(rid, supabase, tier="launchpad", locale_override=locale)
        finally:
            _prewarm_inflight.discard(rid)
        if row.get('email'):
            url = f"{(os.getenv('FRONTEND_URL') or 'https://myetijahi.com').rstrip('/')}/{locale}/results/{rid}"
            subject, html_body = _full_report_ready_email(row.get('full_name'), url, locale)
            send_email(to=row['email'], subject=subject, html_body=html_body, supabase=supabase)
    except Exception as e:
        send_failure_alert("Full report build after purchase", e, response_id=rid, supabase=supabase)

def _activate_plan(user_id: str, plan_code: str):
    """Applies a paid plan_code to user_plans. Pathfinder is a permanent, one-time
    unlock; launchpad_* extends a rolling subscription window independently of it."""
    catalog_entry = PLAN_CATALOG.get(plan_code)
    if not catalog_entry:
        return

    _invalidate_free_tier_report_cache(user_id)

    if plan_code == "pathfinder":
        supabase.table('user_plans').upsert({
            'user_id': user_id,
            'pathfinder_unlocked': True,
            'pathfinder_unlocked_at': datetime.now(timezone.utc).isoformat(),
        }, on_conflict='user_id').execute()
        return

    # Launchpad is Pathfinder plus a coaching session, so the full report stays unlocked for life even after the
    # Launchpad window below ends.
    supabase.table('user_plans').upsert({
        'user_id': user_id,
        'pathfinder_unlocked': True,
        'pathfinder_unlocked_at': datetime.now(timezone.utc).isoformat(),
    }, on_conflict='user_id').execute()

    now = datetime.now(timezone.utc)
    existing = supabase.table('user_plans').select('subscription_current_period_end').eq('user_id', user_id).execute()
    base = now
    if existing.data:
        current_end = existing.data[0].get('subscription_current_period_end')
        if current_end:
            current_end_dt = datetime.fromisoformat(current_end)
            if current_end_dt > now:
                base = current_end_dt
    new_end = base + timedelta(days=catalog_entry["extension_days"])
    supabase.table('user_plans').upsert({
        'user_id': user_id,
        'subscription_plan_code': plan_code,
        'subscription_status': 'active',
        'subscription_current_period_end': new_end.isoformat(),
    }, on_conflict='user_id').execute()


def _save_checkout_context(user_id: str, request: Request, fbp: str | None, fbc: str | None):
    """Remembers the buyer's IP / user agent / Meta cookies at checkout time. The
    payment webhook is server-to-server (from the shop), so this is the only moment
    those browser-side values are visible. Best-effort — never blocks checkout."""
    try:
        fwd = request.headers.get("x-forwarded-for", "")
        ip = fwd.split(",")[0].strip() or (request.client.host if request.client else None)
        supabase.table('checkout_context').upsert({
            'user_id': user_id,
            'client_ip': ip,
            'client_user_agent': request.headers.get("user-agent"),
            'fbp': fbp,
            'fbc': fbc,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }, on_conflict='user_id').execute()
    except Exception as e:
        print("checkout_context save failed:", e)


def _load_checkout_context(user_id: str) -> dict:
    """Latest checkout context for this user, if recent enough to belong to the
    payment being confirmed (a webhook lands within minutes of checkout)."""
    try:
        row = supabase.table('checkout_context').select('*').eq('user_id', user_id).execute()
        if not row.data:
            return {}
        ctx = row.data[0]
        if datetime.now(timezone.utc) - datetime.fromisoformat(ctx['updated_at']) > timedelta(hours=24):
            return {}
        return ctx
    except Exception as e:
        print("checkout_context load failed:", e)
        return {}


def _send_meta_purchase_event(user_id: str, order_ref: str, amount: float, currency: str, tap_charge_id: str | None):
    """Server-side Purchase event to Meta's Conversions API. Best-effort — must
    never fail or delay the webhook response that confirms payment to the user."""
    if not META_PIXEL_ID or not META_ACCESS_TOKEN:
        return
    try:
        email = phone = None
        try:
            user_resp = supabase.auth.admin.get_user_by_id(user_id)
            email = getattr(user_resp.user, "email", None) if user_resp else None
            phone = getattr(user_resp.user, "phone", None) if user_resp else None
        except Exception:
            pass

        user_data = {}
        if email:
            user_data["em"] = [hashlib.sha256(email.strip().lower().encode()).hexdigest()]
        phone_digits = "".join(ch for ch in (phone or "") if ch.isdigit())
        if phone_digits:
            user_data["ph"] = [hashlib.sha256(phone_digits.encode()).hexdigest()]

        # Browser-side identifiers captured at checkout (IP, user agent, _fbp, _fbc).
        ctx = _load_checkout_context(user_id)
        if ctx.get("client_ip"):
            user_data["client_ip_address"] = ctx["client_ip"]
        if ctx.get("client_user_agent"):
            user_data["client_user_agent"] = ctx["client_user_agent"]
        if ctx.get("fbp"):
            user_data["fbp"] = ctx["fbp"]
        if ctx.get("fbc"):
            user_data["fbc"] = ctx["fbc"]

        payload = {
            "data": [{
                "event_name": "Purchase",
                "event_time": int(time.time()),
                "event_id": order_ref,  # dedup key if you ever also fire the browser Pixel
                "action_source": "website",
                "user_data": user_data,
                "custom_data": {
                    "currency": currency,
                    "value": amount,
                    "content_ids": [order_ref],
                    "content_type": "product",
                    **({"tap_charge_id": tap_charge_id} if tap_charge_id else {}),
                },
            }],
            "access_token": META_ACCESS_TOKEN,
        }
        if META_TEST_EVENT_CODE:
            payload["test_event_code"] = META_TEST_EVENT_CODE

        resp = httpx.post(
            f"https://graph.facebook.com/v21.0/{META_PIXEL_ID}/events",
            json=payload, timeout=10.0,
        )
        if resp.status_code >= 400:
            print(f"Meta CAPI rejected purchase event for order_ref={order_ref}: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Meta CAPI purchase event failed for order_ref={order_ref}:", e)


@app.post("/hub/transactions")
async def receive_hub_transaction(request: Request, background_tasks: BackgroundTasks):
    if not HUB_API_KEY:
        raise HTTPException(status_code=500, detail="HUB_API_KEY is not configured")
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature", "")
    expected = hmac.new(HUB_API_KEY.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid Signature")

    body = HubTransactionBody(**json.loads(raw_body))

    # record_hub_transaction (Postgres function) always writes/refreshes the
    # transaction row, and atomically reports whether THIS call is the one
    # that just transitioned it from not-paid to paid — so a duplicate/
    # retried webhook delivery for the same order_ref (payment providers
    # commonly retry) can't double-apply the plan. Done as a single DB-side
    # function rather than a multi-step read-then-write from here, since a
    # multi-step version has a real race window between its steps (see its
    # definition for the exact locking it relies on).
    try:
        result = supabase.rpc('record_hub_transaction', {
            'p_user_id': body.external_user_id,
            'p_order_ref': body.order_ref,
            'p_plan_code': body.plan_code,
            'p_amount': body.amount,
            'p_currency': body.currency,
            'p_status': body.status,
            'p_tap_charge_id': body.tap_charge_id,
            'p_paid_at': body.paid_at,
        }).execute()
    except Exception as e:
        # A genuine failure here (not just "already handled") must not be
        # swallowed as if it were — otherwise a customer can pay and never
        # get their plan with zero trace, since the provider won't retry a
        # 200 response.
        print(f"record_hub_transaction failed for order_ref={body.order_ref}:", e)
        raise HTTPException(status_code=500, detail="Failed to record transaction")

    if result.data:
        # Meta first: it's best-effort and never raises, so a failure in the plan
        # write below can't stop the Purchase event from being sent.
        _send_meta_purchase_event(body.external_user_id, body.order_ref, body.amount, body.currency, body.tap_charge_id)
        _activate_plan(body.external_user_id, body.plan_code)
        # Start building the full report now so it is mostly ready when the buyer comes back.
        background_tasks.add_task(_prewarm_full_report, body.external_user_id)
        if str(body.plan_code).startswith('launchpad'):
            background_tasks.add_task(_notify_coaching_purchase, body.external_user_id, body.amount, body.currency)
            background_tasks.add_task(_create_academy_coaching_purchase, body.external_user_id, body.order_ref)

    return {"received": True}