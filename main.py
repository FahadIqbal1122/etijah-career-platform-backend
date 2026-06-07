import os
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from scoring_engine import compute_scores, build_framework_output
from pydantic import BaseModel, EmailStr
from typing import Any
import io
from fastapi.responses import StreamingResponse
from report_generator import create_report

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
    if emails:
        responses = supabase.table('assessment_responses').select('email').in_('email', emails).eq('completed', True).execute()
        assessment_emails = [r['email'] for r in responses.data] if responses.data else []
    result = [{**l, 'has_assessment': l['email'] in assessment_emails} for l in (links.data or [])]
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

    summary = build_framework_output(rows.data)
    return {'results': rows.data, 'summary': summary}

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
    # Get stored results
    rows = supabase.table('assessment_results') \
        .select('*') \
        .eq('response_id', response_id) \
        .execute()
    if not rows.data:
        raise HTTPException(status_code=404, detail="No results found")

    # Get user profile data (education + sectors of interest)
    profile = supabase.table('assessment_responses') \
        .select('education_field, sectors_of_interest') \
        .eq('id', response_id) \
        .single() \
        .execute()

    user_education = profile.data.get('education_field', '') if profile.data else ''
    user_sectors = profile.data.get('sectors_of_interest', []) if profile.data else []

    summary = build_framework_output(rows.data)
    careers = supabase.table('careers').select('*').execute().data or []

    user_riasec = summary.get('riasec', {}).get('top_types', [])
    user_values = summary.get('values', {}).get('top_values', [])
    user_strengths = summary.get('strengths', {}).get('top_strengths', [])
    work_style = summary.get('work_style', {})
    entreprenuer = summary.get('entrepreneurship', {})

    # Derive work preferences from normalized scores
    user_pace = 'fast' if work_style.get('pace', 50) >= 50 else 'steady'
    user_sector = 'private' if work_style.get('sector', 50) >= 50 else 'public'
    user_entrepreneur_score = (
        entreprenuer.get('risk_tolerance', 0) +
        entreprenuer.get('portfolio_interest', 0)
    ) / 2

    # Normalize sector names for matching
    sector_map = {
        'technology': 'Technology', 'healthcare': 'Healthcare',
        'finance': 'Finance', 'government': 'Government',
        'hospitality': 'Hospitality', 'education': 'Education',
        'creative': 'Creative', 'consulting': 'Business',
        'real_estate': 'Real Estate', 'sports': 'Sports',
        'nonprofit': 'Social Services', 'logistics': 'Operations',
        'energy': 'Engineering', 'media': 'Media',
    }
    user_sector_names = [sector_map.get(s, s) for s in (user_sectors or [])]

    def score_career(career):
        score = 0

        # RIASEC - Weighted by rank (primary match worth more)
        for i, t in enumerate(user_riasec):
            if t in (career['riasec'] or []):
                score += 3 - i # primary=3, second=2, third=1
        
        # Values
        for v in user_values:
            if v in (career['top_values'] or []):
                score += 2

        # Strengths
        for s in user_strengths:
            if s in (career['top_strengths'] or []):
                score += 2

        # Work Style
        if career['work_pace'] == user_pace:
            score += 1
        if career['work_sector'] == user_sector:
            score += 1

        # Entrepreneurship
        if career['entrepreneurship_friendly'] and user_entrepreneur_score >= 50:
            score += 2
        
        # Education match
        if user_education and user_education != 'not_applicable':
            if user_education in (career['education_fields'] or []):
                score += 3

        # Sectors of interest
        if career['sector'] in user_sector_names:
            score += 2
        
        return score

    scored = sorted(careers, key=score_career, reverse=True)
    top10 = scored[:10]

    return {
        "riasec_code": ''.join(t[0].upper() for t in user_riasec),
        "suggestions": [
            {
                "title": c['title'],
                "sector": c['sector'],
                "entrepreneurship_friendly": c['entrepreneurship_friendly']
            }
            for c in top10
        ]
    }

@app.get("/assessment/{response_id}/report")
def get_report(response_id: str):
    try:
        pdf_bytes = create_report(response_id, supabase)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPSException(status_code=500, details=f"Report generation failed: {str(e)}")

    filename = f"career-report-{response_id[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

