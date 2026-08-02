from http import HTTPStatus
import os
from threading import _profile_hook
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from scoring_engine import compute_scores, build_framework_output, score_careers, get_career_semantic_scores
from pydantic import BaseModel, EmailStr
from typing import Any
import io
from datetime import datetime, timezone, timedelta
from fastapi.responses import StreamingResponse
from report_generator import create_report
import httpx, hmac, hashlib, json
from coaching_methodology import METHODOLOGY_DOC
from coaching_pipeline import chunk_transcript, embed_and_store_chunks, client, embed_country_profile, sync_country_profile_embedding, sync_career_embedding, _gemini_embed
from content_policy import is_appropriate, CULTURAL_GUARDRAIL

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://careercompass.etijahcoaching.com",
        "https://myetijahi.com",
        "https://www.myetijahi.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import traceback
from fastapi.responses import JSONResponse
from fastapi import Request

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"error": str(exc)})

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)

HUB_API_KEY = os.getenv("HUB_API_KEY")
SHOP_BASE_URL = os.getenv("SHOP_BASE_URL", "https://shop.etijahcoaching.com")
BILLING_RETURN_URL = "https://myetijahi.com/account/billing"
PLAN_EXTENSTION_DAYS = 30

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
    try:
        response = supabase.auth.get_user(credentials.credentials)
        return response.user if response.user else None
    except Exception:
        return None

def require_admin(user=Depends(get_current_user)):
    role = (user.app_metadata or {}).get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def _assert_can_view(owner_user_id: str | None, user):
    if owner_user_id and (not user or (user.id != owner_user_id and (user.app_metadata or {}).get("role") != "admin")):
        raise HTTPException(status_code=404, detail="No results found for this response")


class OnetLinkRequest(BaseModel):
    email: str
    onet_url: str
    label: str | None = None

class CheckExistingRequest(BaseModel):
    email: str
    phone: str

class SubmitRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    country: str
    nationality: str
    age_bracket: str
    current_stage: str
    education_field: str
    sectors_of_interest: list[str]
    career_structure: str
    languages: list[str]
    geographic_openness: str
    why_here: str
    answers: dict[str, Any]
    completed: bool
    locale: str | None = 'en'

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

class coachingSessionRequest(BaseModel):
    client_label: str | None = None
    topic: str | None = None
    session_date: str | None = None #YYYY-MM-DD
    raw_transcript: str

class CoachRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []

class CheckoutRequest(BaseModel):
    plan_code: str
    plan_name: str
    amount: float
    currency: str = "BHD"

class HubTransactionBody(BaseModel):
    external_user_id: str
    order_ref: str
    plan_code: str
    amount: float
    currency: str
    status: str
    tap_charge_id: str | None = None
    paid_at: str | None = None

COUNTRY_CODE_MAP = {
    'saudi_arabia': 'SA',
    'bahrain': 'BH',
    'kuwait': 'KW',
    'oman': 'OM',
    'qatar': 'QA',
}

@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/admin/submissions")
def get_submissions(_=Depends(require_admin)):
    data = supabase.table('assessment_responses') \
        .select('id, full_name, email, phone, country, age_bracket, current_stage, completed, created_at') \
        .order('created_at', desc=True) \
        .execute()
    return data.data or []


@app.post("/assessment/check-existing")
def check_existing(body: CheckExistingRequest):
    result = supabase.rpc('check_existing_response', {
        'p_email': body.email,
        'p_phone': body.phone,
    }).execute()

    if not result.data:
        return None

    row = supabase.table('assessment_responses').select('user_id').eq('id', result.data).single().execute()
    if row.data and row.data.get('user_id'):
        return {"id": None, "claimed": True}

    return {"id": result.data}


@app.post("/assessment/submit")
def submit_assessment(body: SubmitRequest, user=Depends(get_optional_user)):
    # Score it first, before writing anything — a payload with no recognizable
    # question answers can't be scored, so reject cleanly instead of leaving
    # an orphaned response row with no results.
    results = compute_scores(body.answers)
    if not results:
        raise HTTPException(status_code=422, detail="No scoreable answers found in payload")
    summary = build_framework_output(results)

    # Save to DB
    result = supabase.rpc('insert_assessment_response', {
        'payload': body.model_dump()
    }).execute()

    response_id = result.data
    if not response_id:
        raise HTTPException(status_code=500, detail="Failed to insert assessment response")

    if user:
        supabase.table('assessment_responses') \
            .update({'user_id': user.id}) \
            .eq('id', response_id).execute()

    rows = [{**r, "response_id": response_id} for r in results]
    # Insert results
    supabase.table('assessment_results').upsert(rows, on_conflict='response_id,framework,dimension').execute()
    # Return summary
    return {"response_id": response_id, "summary": summary}


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
def get_onet_links():
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
def add_onet_link(body: OnetLinkRequest):
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


@app.get("/assessment/{response_id}/results")
def get_results(response_id: str, user=Depends(get_optional_user)):
    profile = supabase.table('assessment_responses') \
        .select('email, user_id') \
        .eq('id', response_id).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    _assert_can_view(profile.data.get('user_id'), user)

    rows = supabase.table('assessment_results') \
        .select('*') \
        .eq('response_id', response_id) \
        .execute()
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found for this response")

    summary = build_framework_output(rows.data)
    return {'results': rows.data, 'summary': summary, 'email': profile.data.get('email')}

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

@app.get("/assessment/{response_id}/career-suggestions")
def get_career_suggestions(response_id: str, user=Depends(get_optional_user)):
    rows = supabase.table('assessment_results') \
        .select('*').eq('response_id', response_id).execute()
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found")

    profile = supabase.table('assessment_responses') \
        .select('education_field, sectors_of_interest, user_id') \
        .eq('id', response_id).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="No results found")
    _assert_can_view(profile.data.get('user_id'), user)

    summary = build_framework_output(rows.data)
    careers = supabase.table('careers').select('*').execute().data or []
    semantic_scores = get_career_semantic_scores(supabase, summary, profile.data or {})
    top10   = score_careers(summary, profile.data or {}, careers, semantic_scores)

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

@app.get("/assessment/{response_id}/ai-impact")
def get_ai_impact(response_id: str, force: bool = False, user=Depends(get_optional_user)):
    profile_row = supabase.table('assessment_responses') \
        .select('full_name,current_stage,country,education_field,sectors_of_interest,ai_impact_cache,user_id') \
        .eq('id', response_id).single().execute()
    if not profile_row.data:
        raise HTTPException(status_code=404, detail="No results found")
    _assert_can_view(profile_row.data.get('user_id'), user)

    if profile_row.data.get('ai_impact_cache') and not force:
        return profile_row.data['ai_impact_cache']

    rows = supabase.table('assessment_results') \
        .select('*').eq('response_id', response_id).execute()
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found")

    summary = build_framework_output(rows.data)
    careers = supabase.table('careers').select('*').execute().data or []
    semantic_scores = get_career_semantic_scores(supabase, summary, profile_row.data or {})
    top5    = score_careers(summary, profile_row.data or {}, careers, semantic_scores)[:5]

    from report_generator import generate_ai_impact
    result = generate_ai_impact(profile_row.data or {}, summary, top5)

    supabase.table('assessment_responses') \
        .update({'ai_impact_cache': result}) \
        .eq('id', response_id).execute()

    return result

@app.get("/assessment/{response_id}/report")
def get_report(response_id: str, user=Depends(get_optional_user)):
    owner_row = supabase.table('assessment_responses').select('user_id').eq('id', response_id).single().execute()
    if not owner_row.data:
        raise HTTPException(status_code=404, detail="No results found for this response")
    _assert_can_view(owner_row.data.get('user_id'), user)

    try:
        pdf_bytes = create_report(response_id, supabase)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    filename = f"career-report-{response_id[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

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
def get_course_recommendations(response_id: str, user=Depends(get_optional_user)):
    rows = supabase.table('assessment_results').select('*').eq('response_id', response_id).execute()
    profile = supabase.table('assessment_responses') \
        .select('country, education_field, sectors_of_interest, user_id') \
        .eq('id', response_id).single().execute()
    if not rows.data or not profile.data:
        raise HTTPException(status_code=404, detail="No results found")
    _assert_can_view(profile.data.get('user_id'), user)
    summary = build_framework_output(rows.data)
    careers = supabase.table('careers').select('*').execute().data or []
    semantic_scores = get_career_semantic_scores(supabase, summary, profile.data)
    top5    = score_careers(summary, profile.data, careers, semantic_scores)[:5]

    user_riasec = set(summary.get('riasec', {}).get('top_types', []))
    sectors     = set(c['sector'] for c in top5)

    all_courses = supabase.table('courses').select('*').execute().data or []

    def score_course(course):
        riasec_overlap = len(set(course.get('riasec_tags') or []) & user_riasec)
        sector_overlap = len(set(course.get('career_tags') or []) & sectors)
        return sector_overlap * 3 + riasec_overlap * 2

    scored  = sorted(all_courses, key=score_course, reverse=True)
    matched = [c for c in scored if score_course(c) > 0][:10]
    return matched if matched else scored[:10]

JOB_LISTINGS_CACHE_TTL = timedelta(hours=24)

MARKET_ROLE_CATEGORIES = [
    "software engineer", "data analyst", "project manager", "accountant",
    "financial analyst", "marketing manager", "HR manager", "civil engineer",
    "mechanical engineer", "nurse", "doctor", "teacher", "sales manager",
    "operations manager", "supply chain", "business analyst", "architect",
    "cybersecurity", "logistics", "procurement", "legal counsel",
    "graphic designer", "banker", "consultant", "pharmacist",
]

MARKET_COUNTRIES = [
    {"code": "SA", "name": "Saudi Arabia", "query_suffix": "Saudi Arabia"},
    {"code": "BH", "name": "Bahrain", "query_suffix": "Bahrain"},
]

def _get_week_start() -> str:
    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()

@app.post("/admin/market-analysis/fetch")
async def fetch_market_analysis(_=Depends(require_admin)):
    import asyncio
    mega_key = os.getenv("JSEARCH_MEGA_KEY")
    if not mega_key:
        return {"week": _get_week_start(), "inserted": 0, "errors": 0, "insert_error": "JSEARCH_MEGA_KEY is not set on the backend"}
    week_start = _get_week_start()

    existing = supabase.table("job_market_snapshots") \
        .select("job_id") \
        .eq("fetched_week", week_start) \
        .execute()
    seen_ids = {r["job_id"] for r in (existing.data or [])}

    tasks = [
        (country, role)
        for country in MARKET_COUNTRIES
        for role in MARKET_ROLE_CATEGORIES
    ]

    all_rows = []
    errors = 0

    async def fetch_one(client: httpx.AsyncClient, country: dict, role: str):
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
                return country, role, resp.json().get("data") or []
            except Exception as e:
                if attempt < 2 and isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429:
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
                print(f"Market fetch error [{country['code']}][{role}]: {type(e).__name__}: {e!r}")
                return country, role, None

    async with httpx.AsyncClient() as client:
        # Small batches with a pause between them to stay under the RapidAPI rate limit
        for i in range(0, len(tasks), 3):
            batch = tasks[i:i+3]
            results = await asyncio.gather(*[fetch_one(client, c, r) for c, r in batch])
            if i + 3 < len(tasks):
                await asyncio.sleep(1)
            for country, role, jobs in results:
                if jobs is None:
                    errors += 1
                    continue
                for job in jobs[:8]:
                    job_id = job.get("job_id")
                    if not job_id or job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    all_rows.append({
                        "fetched_week": week_start,
                        "country_code": country["code"],
                        "country_name": country["name"],
                        "role_category": role,
                        "job_id": job_id,
                        "job_title": job.get("job_title"),
                        "company": job.get("employer_name"),
                        "location": f"{job.get('job_city', '')} {job.get('job_country', '')}".strip(),
                        "salary_min": job.get("job_min_salary"),
                        "salary_max": job.get("job_max_salary"),
                        "salary_currency": job.get("job_salary_currency"),
                        "url": job.get("job_apply_link"),
                    })

    inserted = 0
    insert_error = None
    if all_rows:
        try:
            supabase.table("job_market_snapshots").upsert(all_rows, on_conflict="fetched_week,job_id").execute()
            inserted = len(all_rows)
        except Exception as e:
            print(f"Market snapshot insert failed: {e}")
            insert_error = str(e)

    result = {"week": week_start, "inserted": inserted, "errors": errors}
    if insert_error:
        result["insert_error"] = insert_error
    return result

@app.get("/admin/market-analysis/trends")
def get_market_trends(_=Depends(require_admin)):
    rows = supabase.table("job_market_snapshots") \
        .select("*") \
        .order("fetched_week", desc=False) \
        .execute().data or []

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
            salary.setdefault(key, [])
            salary[key].extend(v for v in [r.get("salary_min"), r.get("salary_max")] if v)

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
        "salary": [{"week": k[0], "country": k[1], "role": k[2], "avg_salary": round(sum(v)/len(v), 0)} for k, v in salary.items()],
        "top_companies": top_companies,
        "top_titles_by_role": top_titles_by_role,
        "recent_jobs": recent,
        "total_snapshots": len(rows),
        "total_companies": len(company_count),
    }

@app.get("/assessment/{response_id}/job-listings")
def get_job_listings(response_id: str, force: bool = False, user=Depends(get_optional_user)):
    owner_row = supabase.table('assessment_responses').select('user_id').eq('id', response_id).single().execute()
    if not owner_row.data:
        raise HTTPException(status_code=404, detail="No results found")
    _assert_can_view(owner_row.data.get('user_id'), user)

    cached = supabase.table('job_listings_cache').select('*').eq('response_id', response_id).execute()
    if cached.data and not force:
        fetched_at = datetime.fromisoformat(cached.data[0]['fetched_at'])
        if datetime.now(timezone.utc) - fetched_at < JOB_LISTINGS_CACHE_TTL:
            return {"jobs": cached.data[0]['jobs']}

    profile = supabase.table('assessment_responses') \
        .select('country, education_field, sectors_of_interest') \
        .eq('id', response_id).single().execute()
    rows = supabase.table('assessment_results') \
        .select('*') \
        .eq('response_id', response_id).execute()
    if not rows.data or not profile.data:
        raise HTTPException(status_code=404, detail="No results found")

    summary = build_framework_output(rows.data)
    careers = supabase.table('careers').select('*').execute().data or []
    semantic_scores = get_career_semantic_scores(supabase, summary, profile.data)
    top3    = score_careers(summary, profile.data, careers, semantic_scores)[:3]

    country = profile.data.get('country', '')
    rapidapi_key = os.getenv("RAPIDAPI_KEY")

    all_jobs = []
    seen_ids = set()

    for career in top3:
        try:
            resp = httpx.get(
                "https://jsearch.p.rapidapi.com/search",
                params={"query": f"{career['title']} {country}", "num_pages": "1", "page": "1"},
                headers={
                    "X-RapidAPI-Key": rapidapi_key,
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                },
                timeout=8.0,
            )
            resp.raise_for_status()
            for job in (resp.json().get("data") or [])[:4]:
                job_id = job.get("job_id")
                job_title = job.get("job_title")
                employer_name = job.get("employer_name")
                if not is_appropriate(job_title, employer_name, job.get("job_description")):
                    continue
                if job_id and job_id not in seen_ids:
                    seen_ids.add(job_id)
                    all_jobs.append({
                        "title": job_title,
                        "company": employer_name,
                        "location": f"{job.get('job_city', '')} {job.get('job_country', '')}".strip(),
                        "source": job.get("job_publisher"),

                        "url": job.get("job_apply_link"),
                        "matched_career": career['title'],
                    })
        except Exception as e:
            print("JSearch error:", e)
            continue

    result_jobs = all_jobs[:12]

    supabase.table('job_listings_cache').upsert({
        'response_id': response_id,
        'jobs': result_jobs,
        'fetched_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    return {"jobs": result_jobs}


@app.get("/assessment/my-assessments")
def get_my_assessments(user=Depends(get_current_user)):
    responses = supabase.table('assessment_responses') \
        .select('id, full_name, country, completed, created_at') \
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
    profile = supabase.table('assessment_responses') \
        .select('country, education_field, sectors_of_interest, user_id') \
        .eq('id', response_id).single().execute()
    rows = supabase.table('assessment_results') \
        .select('*') \
        .eq('response_id', response_id).execute()
    if not rows.data or not profile.data:
        raise HTTPException(status_code=404, detail="No data found")
    _assert_can_view(profile.data.get('user_id'), user)

    summary = build_framework_output(rows.data)
    careers = supabase.table('careers').select('*').execute().data or []
    semantic_scores = get_career_semantic_scores(supabase, summary, profile.data)
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

    result = query.order('name_en').limit(15).execute()
    return [c for c in (result.data or []) if is_appropriate(c.get('name_en'), c.get('sector'))]

@app.post("/assessment/link-by-email")
def link_by_email(user=Depends(get_current_user)):
    result = supabase.table('assessment_responses') \
        .update({"user_id": user.id}) \
        .ilike('email', user.email) \
        .is_('user_id', 'null') \
        .execute()
    return {"linked": len(result.data or [])}

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

    system_prompt = f"{METHODOLOGY_DOC}\n\n{CULTURAL_GUARDRAIL}\n\nRelevant past examples:\n{examples}{country_context}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=payload.conversation_history + [{"role": "user", "content": payload.message}],
    )
    return {"reply": response.content[0].text}


@app.post("/billing/checkout")
def create_checkout(body: CheckoutRequest, user=Depends(get_current_user)):
    full_name = (user.user_metadata or {}).get("full_name", "") or ""
    first_name, _, last_name = full_name.strip().partition(" ")

    payload = {
        "external_user_id": user.id,
        "first_name": first_name or "Customer",
        "last_name": last_name or "Account",
        "email": user.email,
        "plan_code": body.plan_code,
        "plan_name": body.plan_name,
        "amount": body.amount,
        "currency": body.currency,
        "return_url": BILLING_RETURN_URL,
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
        raise HTTPException(status_code=502, detail=f"Shop rejected the order: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Shop: {e}")

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
    if not row.data:
        return {"plan_code": None, "status": "free", "current_period_end": None}
    plan = row.data[0]
    is_active = plan['status'] == 'active' and datetime.fromisoformat(plan['current_period_end']) > datetime.now(timezone.utc)
    return {**plan, "status": "active" if is_active else "expired"}

def _active_plan(user_id: str, plan_code: str):
    now = datetime.now(timezone.utc)
    existing = supabase.table('user_plans').select('current_period_end').eq('user_id', user_id).execute()
    base = now
    if existing.data:
        current_end = existing.data[0].get('current_period_end')
        if current_end:
            current_end_dt = datetime.fromisoformat(current_end)
            if current_end_dt > now:
                base = current_end_dt
    new_end = base + timedelta(days=PLAN_EXTENSTION_DAYS)
    supabase.table('user_plans').upsert({
        'user_id': user_id,
        'plan_code': plan_code,
        'status': 'active',
        'current_period_end': new_end.isoformat(),
    }, on_conflict='user_id').execute()


@app.post("/hub/transactions")
async def receive_hub_transaction(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature", "")
    expected = hmac.new(HUB_API_KEY.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid Signature")

    body = HubTransactionBody(**json.loads(raw_body))

    existing = supabase.table('transactions') \
        .select('status') \
        .eq('order_ref', body.order_ref) \
        .execute()
    already_paid = bool(existing.data) and existing.data[0]['status'] == 'paid'

    supabase.table('transactions').upsert({
        'user_id': body.external_user_id,
        'order_ref': body.order_ref,
        'plan_code': body.plan_code,
        'amount': body.amount,
        'currency': body.currency,
        'status': body.status, 
        'tap_charge_id': body.tap_charge_id,
        'paid_at': body.paid_at,
    }, on_conflict='order_ref').execute()

    if body.status == 'paid' and not already_paid:
        _active_plan(body.external_user_id, body.plan_code)
    
    return {"received": True}