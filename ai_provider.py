"""
Shared AI-provider setting (app_settings.ai_provider) — lets an admin switch which LLM
backs report narrative generation (Gemini vs Claude) without a redeploy. Self-contained
with its own Supabase client (like smtp_service.py) so report_generator.py doesn't need
to import from main.py, which itself imports report_generator — that would be a cycle.
"""

import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from db_client import disable_http2

AI_PROVIDER_KEY = "ai_provider"
VALID_PROVIDERS = ("gemini", "claude")

_supabase = disable_http2(create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")))

_provider_cache = {"value": None, "checked_at": None}
_PROVIDER_CACHE_TTL = timedelta(seconds=10)


GEMINI_ENABLED_KEY = "gemini_enabled"
_gemini_cache = {"value": True, "checked_at": None}
_GEMINI_CACHE_TTL = timedelta(seconds=10)


class GeminiSwitchedOff(RuntimeError):
    """A Gemini call was attempted while app_settings.gemini_enabled is false (see is_gemini_enabled)."""


def is_gemini_enabled() -> bool:
    """Master switch for every Google Gemini call (app_settings.gemini_enabled). On unless the row says false, so a missing
    row or a failed lookup never changes existing behaviour. Off = Claude does all text generation and translation, with no
    fallback to Gemini, and the embedding calls (which Claude cannot do) are skipped; callers treat that as 'no
    embedding available'. Cached briefly, like the provider setting."""
    now = datetime.now(timezone.utc)
    if _gemini_cache["checked_at"] and now - _gemini_cache["checked_at"] < _GEMINI_CACHE_TTL:
        return _gemini_cache["value"]
    enabled = True
    try:
        row = _supabase.table("app_settings").select("value").eq("key", GEMINI_ENABLED_KEY).execute()
        if row.data and row.data[0]["value"] is False:
            enabled = False
    except Exception as e:
        print("Gemini switch lookup failed, leaving Gemini on:", e)
    _gemini_cache["value"] = enabled
    _gemini_cache["checked_at"] = now
    return enabled


def invalidate_gemini_cache():
    _gemini_cache["checked_at"] = None


def get_ai_provider() -> str:
    """Admin-togglable (app_settings.ai_provider), AI_PROVIDER env var as the
    fallback/seed so an unset DB row doesn't change existing behavior. Cached
    briefly since report generation calls this on every request. Always 'claude' while Gemini is switched off."""
    if not is_gemini_enabled():
        return "claude"
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
