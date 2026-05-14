import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from scoring_engine import compute_scores, build_framework_output
from pydantic import BaseModel, EmailStr
from typing import Any

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

@app.get("/")
def root():
    return {"status": "ok"}


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
def score_assessment(response_id:str):
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
