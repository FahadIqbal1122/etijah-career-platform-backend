from http import HTTPStatus
import os
from threading import _profile_hook
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from scoring_engine import compute_scores, build_framework_output, score_careers
from pydantic import BaseModel, EmailStr
from typing import Any
import io
from datetime import datetime, timezone, timedelta
from fastapi.responses import StreamingResponse
from report_generator import create_report
import httpx
from coaching_methodology import METHODOLOGY_DOC 
from coaching_pipeline import chunk_transcript, embed_and_store_chunks, client
import google.generativeai as genai

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://careercompass.etijahcoaching.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)

_bearer = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(_bearer)):
    try:
        response = supabase.auth.get_user(credentials.credentials)
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or Expired token")

def require_admin(user=Depends(get_current_user)):
    role = (user.app_metadata or {}).get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class OnetLinkRequest(BaseModel):
    email: str
    onet_url: str
    label: str | None = None

class CheckExistingRequest(BaseModel):
    email: str
    phone: str

class LinkByEmailRequest(BaseModel):
    user_id: str
    email: EmailStr

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

class coachingSessionRequest(BaseModel):
    client_label: str | None = None
    topic: str | None = None
    session_date: str | None = None #YYYY-MM-DD
    raw_transcript: str

class CoachRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []

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

    if result.data:
        return {"id": result.data}
    return None


@app.post("/assessment/submit")
def submit_assessment(body: SubmitRequest):
    # Save to DB
    result = supabase.rpc('insert_assessment_response', {
        'payload': body.model_dump()
    }).execute()

    response_id = result.data
    if not response_id:
        raise HTTPException(status_code=500, detail="Failed to insert assessment response")
    # Score it 
    results = compute_scores(body.answers)
    summary = build_framework_output(results)
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
def get_results(response_id: str):
    rows = supabase.table('assessment_results') \
        .select('*') \
        .eq('response_id', response_id) \
        .execute()
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found for this response")

    profile = supabase.table('assessment_responses') \
        .select('email') \
        .eq('id', response_id).single().execute()

    summary = build_framework_output(rows.data)
    return {'results': rows.data, 'summary': summary, 'email': profile.data.get('email') if profile.data else None}

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

@app.get("/assessment/{response_id}/career-suggestions")
def get_career_suggestions(response_id: str):
    rows = supabase.table('assessment_results') \
        .select('*').eq('response_id', response_id).execute()
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found")

    profile = supabase.table('assessment_responses') \
        .select('education_field, sectors_of_interest') \
        .eq('id', response_id).single().execute()
  
    summary = build_framework_output(rows.data)
    careers = supabase.table('careers').select('*').execute().data or []
    top10   = score_careers(summary, profile.data or {}, careers)

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
def get_ai_impact(response_id: str):
    profile_row = supabase.table('assessment_responses') \
        .select('full_name,current_stage,country,education_field,sectors_of_interest,ai_impact_cache') \
        .eq('id', response_id).single().execute()
    if not profile_row.data:
        raise HTTPException(status_code=404, detail="No results found")

    if profile_row.data.get('ai_impact_cache'):
        return profile_row.data['ai_impact_cache']

    rows = supabase.table('assessment_results') \
        .select('*').eq('response_id', response_id).execute()
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found")

    summary = build_framework_output(rows.data)
    careers = supabase.table('careers').select('*').execute().data or []
    top5    = score_careers(summary, profile_row.data or {}, careers)[:5]

    from report_generator import generate_ai_impact
    result = generate_ai_impact(profile_row.data or {}, summary, top5)

    supabase.table('assessment_responses') \
        .update({'ai_impact_cache': result}) \
        .eq('id', response_id).execute()

    return result

@app.get("/assessment/{response_id}/report")
def get_report(response_id: str):
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
    return result.data[0]

@app.put("/admin/country-profiles/{country_code}")
def update_country_profile(country_code: str, body: dict, _=Depends(require_admin)):
    result = supabase.table('country_profiles').update(body).eq('country_code', country_code).execute()
    return result.data[0] if result.data else {}

@app.delete("/admin/country-profiles/{country_code}")
def delete_country_profile(country_code: str, _=Depends(require_admin)):
    supabase.table('country_profiles').delete().eq('country_code', country_code).execute()
    return {"deleted": country_code}

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
def get_course_recommendations(response_id: str):
    rows = supabase.table('assessment_results').select('*').eq('response_id', response_id).execute()
    profile = supabase.table('assessment_responses') \
        .select('country, education_field, sectors_of_interest') \
        .eq('id', response_id).single().execute()
    if not rows.data or not profile.data:
        raise HTTPException(status_code=404, detail="No results found")
    summary = build_framework_output(rows.data)
    careers = supabase.table('careers').select('*').execute().data or []
    top5    = score_careers(summary, profile.data, careers)[:5]

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

@app.get("/assessment/{response_id}/job-listings")
def get_job_listings(response_id: str):
    cached = supabase.table('job_listings_cache').select('*').eq('response_id', response_id).execute()
    if cached.data:
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
    top3    = score_careers(summary, profile.data, careers)[:3]

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
                if job_id and job_id not in seen_ids:
                    seen_ids.add(job_id)
                    all_jobs.append({
                        "title": job.get("job_title"),
                        "company": job.get("employer_name"),
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
def get_companies_suggestions(response_id: str):
    profile = supabase.table('assessment_responses') \
        .select('country, education_field, sectors_of_interest') \
        .eq('id', response_id).single().execute()
    rows = supabase.table('assessment_results') \
        .select('*') \
        .eq('response_id', response_id).execute()
    if not rows.data or not profile.data:
        raise HTTPException(status_code=404, detail="No data found")

    summary = build_framework_output(rows.data)
    careers = supabase.table('careers').select('*').execute().data or []
    top5    = score_careers(summary, profile.data, careers)[:5]

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
    return result.data or []

@app.post("/assessment/link-by-email")
def link_by_email(body: LinkByEmailRequest):
    try:
        admin_user = supabase.auth.admin.get_user_by_id(body.user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid user_id")

    if not admin_user.user or (admin_user.user.email or "").lower() != body.email.lower():
        raise HTTPException(status_code=403, detail="user_id does not match the email")

    result = supabase.table('assessment_responses') \
        .update({"user_id": body.user_id}) \
        .ilike('email', body.email) \
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
    query_embedding = genai.embed_content(
        model="models/text-embedding-004",
        content=payload.message,
    )["embedding"]

    matches = supabase.rpc("match_coaching_chunks", {
        "query_embedding": query_embedding,
        "match_count": 5,
    }).execute().data

    examples = "\n\n".join(
        f"Situation: {m['situation']}\nCoach response: {m['coach_response']}"
        for m in matches
    )

    system_prompt = f"{METHODOLOGY_DOC}\n\nRelevant past examples:\n{examples}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=payload.conversation_history + [{"role": "user", "content": payload.message}],
    )
    return {"reply": response.content[0].text}