"""
Shared AI-provider setting (app_settings.ai_provider) — lets an admin switch which LLM
backs report narrative generation (Gemini vs Claude) without a redeploy. Self-contained
with its own Supabase client (like smtp_service.py) so report_generator.py doesn't need
to import from main.py, which itself imports report_generator — that would be a cycle.
"""

import os
from datetime import datetime, timezone, timedelta
from supabase import create_client

AI_PROVIDER_KEY = "ai_provider"
VALID_PROVIDERS = ("gemini", "claude")

_supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

_provider_cache = {"value": None, "checked_at": None}
_PROVIDER_CACHE_TTL = timedelta(seconds=10)


def get_ai_provider() -> str:
    """Admin-togglable (app_settings.ai_provider), AI_PROVIDER env var as the
    fallback/seed so an unset DB row doesn't change existing behavior. Cached
    briefly since report generation calls this on every request."""
    now = datetime.now(timezone.utc)
    if _provider_cache["checked_at"] and now - _provider_cache["checked_at"] < _PROVIDER_CACHE_TTL:
        return _provider_cache["value"]
    provider = os.getenv("AI_PROVIDER", "gemini").lower()
    if provider not in VALID_PROVIDERS:
        provider = "gemini"
    try:
        row = _supabase.table("app_settings").select("value").eq("key", AI_PROVIDER_KEY).execute()
        if row.data and row.data[0]["value"] in VALID_PROVIDERS:
            provider = row.data[0]["value"]
    except Exception as e:
        print("AI provider lookup failed, using env default:", e)
    _provider_cache["value"] = provider
    _provider_cache["checked_at"] = now
    return provider


def invalidate_ai_provider_cache():
    _provider_cache["checked_at"] = None
