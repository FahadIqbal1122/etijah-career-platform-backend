"""
One-off backfill: generate the AI Impact section for assessment_responses that
never got one because app_settings.ai_provider was pointed at "claude" without
an ANTHROPIC_API_KEY set (2026-09-03 to 2026-09-07), causing every ai-impact
request to 500 before caching anything.

Mirrors the exact logic of GET /assessment/{response_id}/ai-impact in main.py,
run directly against Supabase instead of over HTTP so it isn't gated by
per-user auth. Re-runnable: skips any response_id that already has a cache.

Usage:
  python scripts/backfill_ai_impact.py --dry-run     # list affected response_ids
  python scripts/backfill_ai_impact.py --run          # actually generate + cache
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from scoring_engine import build_framework_output, score_careers
from report_generator import generate_ai_impact
from main import _get_semantic_scores, get_effective_tier  # noqa: E402

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

BREAK_START = "2026-09-03 08:29:06+00"


def find_affected():
    rows = supabase.table("assessment_responses") \
        .select("id,completed,full_name,current_stage,country,education_field,sectors_of_interest,ai_impact_cache,ai_impact_cache_free,user_id,created_at") \
        .gte("created_at", BREAK_START) \
        .eq("completed", True) \
        .execute().data or []
    return [r for r in rows if not r.get("ai_impact_cache") and not r.get("ai_impact_cache_free")]


def backfill_one(profile: dict) -> bool:
    response_id = profile["id"]
    tier = get_effective_tier(profile.get("user_id"))
    is_free = tier == "free"
    careers_cap = 2 if is_free else 5
    cache_col = "ai_impact_cache_free" if is_free else "ai_impact_cache"

    result_rows = supabase.table("assessment_results").select("*").eq("response_id", response_id).execute().data
    if not result_rows:
        print(f"  SKIP {response_id}: no assessment_results rows")
        return False

    summary = build_framework_output(result_rows)
    careers = supabase.table("careers").select("*").execute().data or []
    semantic_scores = _get_semantic_scores(response_id, summary, profile)
    top_careers = score_careers(summary, profile, careers, semantic_scores)[:careers_cap]

    result = generate_ai_impact(profile, summary, top_careers, career_count=careers_cap)
    supabase.table("assessment_responses").update({cache_col: result}).eq("id", response_id).execute()
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    affected = find_affected()
    print(f"{len(affected)} responses missing AI impact since {BREAK_START}.")

    if not args.run:
        for r in affected:
            print(f"  {r['id']}  ({r.get('created_at')})")
        print("\nDry run — nothing generated. Pass --run to backfill.")
        return

    done, failed = 0, []
    for i, profile in enumerate(affected, 1):
        response_id = profile["id"]
        try:
            if backfill_one(profile):
                done += 1
                print(f"[{i}/{len(affected)}] OK {response_id}")
        except Exception as e:
            failed.append(response_id)
            print(f"[{i}/{len(affected)}] FAILED {response_id}: {e}")
        time.sleep(0.5)  # be gentle on the LLM API for a batch

    print(f"\nDone. Backfilled {done}/{len(affected)}.")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed)}")


if __name__ == "__main__":
    main()
