import os
import json
import requests
from anthropic import Anthropic
from supabase import create_client, Client

client = Anthropic()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def _gemini_embed(text: str) -> list[float]:
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={api_key}"
    resp = requests.post(url, json={"content": {"parts": [{"text": text}]}, "outputDimensionality": 768}, timeout=30)
    resp.raise_for_status()
    return resp.json()["embedding"]["values"]

def chunk_transcript(raw_transcript: str) -> list[dict]:
    prompt = f"""Split this speaker-labeled coaching transcript into discrete beats.
    Each beat is one client situation/question and the coach's response to it.
    Return JSON: a list of objects with "situation" and "coach_response" keys, in order.
    
    Transcript:
    {raw_transcript}"""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        timeout=60.0,
    )
    return parse_json_beats(response.content[0].text) #parse + validate JSON

def embed_and_store_chunks(session_id: str, chunks: list[dict]):
    for i, chunk in enumerate(chunks):
        text_for_embedding = f"Situation: {chunk['situation']}\nResponse: {chunk['coach_response']}"
        embedding = _gemini_embed(text_for_embedding)

        supabase.table("coaching_chunks").insert({
            "session_id": session_id,
            "situation": chunk["situation"],
            "coach_response": chunk["coach_response"],
            "chunk_order": i,
            "embedding": embedding,
        }).execute()

def parse_json_beats(text: str) -> list[dict]:
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON array found in model output: {text!r}")

    beats = json.loads(text[start:end])
    for beat in beats:
        if "situation" not in beat or "coach_response" not in beat:
            raise ValueError(f"Beat missing required keys: {beat!r}")
    return beats


def embed_country_profile(profile: dict) -> list[float]:
    header = f"Country: {profile.get('country_name', '')} ({profile.get('country_code', '')})"
    if profile.get('raw_notes'):
        text = f"{header}\n\n{profile['raw_notes']}"
    else:
        parts = [header]
        for key, label in [
            ('labour_market_authority', 'Labour market authority'),
            ('nationalisation_programme', 'Nationalisation programme'),
        ]:
            if profile.get(key):
                parts.append(f"{label}: {profile[key]}")
        for key, label in [
            ('strategic_priorities', 'Strategic priorities'),
            ('nationalisation_rates_by_sector', 'Nationalisation rates by sector'),
            ('wage_support_tiers', 'Wage support tiers'),
        ]:
            if profile.get(key):
                val = profile[key]
                parts.append(f"{label}: {json.dumps(val) if isinstance(val, (dict, list)) else val}")
        text = "\n".join(parts)
    return _gemini_embed(text)


def sync_country_profile_embedding(country_code: str, profile: dict):
    embedding = embed_country_profile(profile)
    supabase.table("country_profiles").update({"embedding": embedding}).eq("country_code", country_code).execute()


def embed_career(career: dict) -> list[float]:
    parts = [f"Career: {career.get('title', '')}"]
    if career.get('sector'):
        parts.append(f"Sector: {career['sector']}")
    if career.get('riasec'):
        parts.append(f"RIASEC type: {', '.join(career['riasec'])}")
    if career.get('top_values'):
        parts.append(f"Core values: {', '.join(career['top_values'])}")
    if career.get('top_strengths'):
        parts.append(f"Key strengths: {', '.join(career['top_strengths'])}")
    if career.get('work_pace'):
        parts.append(f"Work pace: {career['work_pace']}")
    if career.get('work_sector'):
        parts.append(f"Work sector: {career['work_sector']}")
    if career.get('education_fields'):
        parts.append(f"Related education fields: {', '.join(career['education_fields'])}")
    return _gemini_embed("\n".join(parts))


def sync_career_embedding(career_id: str, career: dict):
    embedding = embed_career(career)
    supabase.table("careers").update({"embedding": embedding}).eq("id", career_id).execute()