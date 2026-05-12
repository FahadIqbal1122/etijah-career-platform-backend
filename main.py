import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from scoring_engine import compute_scores

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)


@app.get("/")
def root():
    return {"status": "ok"}

@aoo.post("/assessment/{response_id}/score")
def score_assessment(response_id:str):
    # Fetch the response
    row = supabase.table('assessment_responses') \
        .select('answers') \
        .eq('id', response_id) \
        .single() \
        .execute()
    if not row.data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Response not found")

    answers = row.data['answers']
    results = compute_scores(answers)

    # Insert into assessment_results
    rows_to_insert = [
        {**r, 'response_id': response_id}
        for r in results
    ]
    supabase.table('assessment_results').upsert(rows_to_insert).execute()

    return {'scored': len(rows_to_insert), 'results': results}
