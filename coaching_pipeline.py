import os
import json
from anthropic import Anthropic
import google.generativeai as genai
from supabase import create_client, Client

client = Anthropic()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

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
    )
    return parse_json_beats(response.content[0].text) #parse + validate JSON

def embed_and_store_chunks(session_id: str, chunks: list[dict]):
    for i, chunk in enumerate(chunks):
        text_for_embedding = f"Situation: {chunk['situation']}\nResponse: {chunk['coach_response']}"
        embedding = genai.embed_content(
            model="models/text-embedding-004",
            content=text_for_embedding,
        )["embedding"]

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