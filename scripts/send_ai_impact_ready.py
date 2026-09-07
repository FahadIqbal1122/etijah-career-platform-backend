"""
One-off notification: tell everyone whose AI Career Impact section failed to
generate (app_settings.ai_provider was pointed at "claude" with no
ANTHROPIC_API_KEY set, 2026-09-03 to 2026-09-07) that it's fixed and their
results are ready to revisit. Uses the 'ai_impact_ready' email_templates row.

Re-runnable: successfully-sent response_ids are logged to
sent_ai_impact_ready_log.json (next to this script) and skipped on retry.

Usage:
  python scripts/send_ai_impact_ready.py --dry-run              # list recipients, send nothing
  python scripts/send_ai_impact_ready.py --test you@example.com # send one test copy, no log write
  python scripts/send_ai_impact_ready.py --send                 # actually send to every unsent recipient
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from smtp_service import render_template, send_email

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sent_ai_impact_ready_log.json")
FRONTEND_BASE = os.getenv("FRONTEND_URL", "").rstrip("/")
BREAK_START = "2026-09-03 08:29:06+00"

# Internal/staff addresses to skip even if they fall in the affected window.
EXCLUDE_EMAILS = {"dina@etijahcoaching.com"}

# The exact response_ids that had no ai_impact_cache/ai_impact_cache_free before
# scripts/backfill_ai_impact.py ran on 2026-09-07 — NOT every response created
# since BREAK_START, most of which were served fine from a pre-existing cache.
AFFECTED_RESPONSE_IDS = {
    "41e7d89e-6a53-481f-9740-15990475aaeb", "bc4b66f8-9574-44b3-abcf-60d51848ec68",
    "d1e540f3-de16-427a-9d16-5172ac8fed7f", "22ff9d2d-9ef1-406e-8641-636a748348a1",
    "98716990-fac1-4835-8f63-f8aa75a04a50", "d8cf9a60-9d06-41fb-8e22-c93ac40621ee",
    "258af229-f444-4756-a989-aaf4e2fdb741", "59f4dbf1-24d2-474f-959f-364f78610917",
    "beb0c9d9-c665-4b3a-befd-114a1617b72d", "8d92e8d1-926e-4735-a64e-01fb7a9ef978",
    "3455d2e6-9f0d-4eb7-b8f9-5aa01356d2a0", "fb2d22cc-aa43-4a6d-bc48-078678cd0fee",
    "28df4d1d-0b87-4a62-8a67-db7e96398a40", "c1e8a809-0f34-44c0-aaf0-c1a95864aca8",
    "876951f6-52b4-4997-a9b1-e9c59f46be2d", "9bba8724-8a73-4d5c-96e8-76582c3fda8a",
    "20c1162a-a99b-4b7d-ba54-1808a0937cc0", "6aebbce1-0f84-4f58-97e4-2466020aa10a",
    "70b6b940-d7a1-4a6a-b910-d75451d1c5a2", "0eab51ca-3533-40b6-8ad1-78d0bf4adab5",
    "375f5242-b162-4ff0-ba7f-e567e777e1cc", "57b37560-7481-4808-9a04-9fe4f6006d50",
    "6746ff8e-f59e-4052-9cfb-beea3922f047", "644ad23b-2376-4c1d-89aa-ddf458789c13",
    "2e691c81-c406-4304-be1b-b57dbaa9d951", "1ee02e7b-aeed-4503-bbdd-2a6b305c7e7d",
    "f7817022-9664-43d8-bdb8-8c21a6caef72", "0a8585ef-f21e-418f-aada-31fa3021f0d9",
    "e68404d2-ffec-4cbd-b331-3771b4318cfd", "c7f8bff6-e7de-480f-b3e5-0cef028444e9",
    "f59d3140-e10b-4302-8780-8f0bf99dc495",
}


def load_sent_log() -> set:
    if not os.path.exists(LOG_PATH):
        return set()
    with open(LOG_PATH) as f:
        return set(json.load(f))


def append_sent_log(response_id: str, sent: set):
    sent.add(response_id)
    with open(LOG_PATH, "w") as f:
        json.dump(sorted(sent), f, indent=2)


def first_name_of(full_name: str | None) -> str:
    if not full_name:
        return "there"
    return full_name.strip().split(" ")[0]


def find_recipients():
    """One row per affected *person* (deduped by email, keeping their most
    recent response_id) — several of the 31 affected rows are repeat
    submissions from the same email. Restricted to AFFECTED_RESPONSE_IDS, not
    every response since BREAK_START (most of those were served fine from a
    pre-existing cache and were never actually broken)."""
    rows = supabase.table("assessment_responses") \
        .select("id, full_name, email, locale, created_at") \
        .in_("id", list(AFFECTED_RESPONSE_IDS)) \
        .order("created_at", desc=True) \
        .execute().data or []
    by_email = {}
    for r in rows:
        email = (r.get("email") or "").strip().lower()
        if not email or email in EXCLUDE_EMAILS:
            continue
        if email not in by_email:  # first hit wins = most recent (rows already desc)
            by_email[email] = r
    return list(by_email.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", help="Send a single test copy to this address instead of broadcasting")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()

    template_row = supabase.table("email_templates").select("*").eq("key", "ai_impact_ready").limit(1).execute()
    if not template_row.data:
        print("ai_impact_ready template not found — apply migrations/ai_impact_ready_email_template.sql first.")
        sys.exit(1)
    template = template_row.data[0]

    if args.test:
        results_url = f"{FRONTEND_BASE}/en/results/00000000-0000-0000-0000-000000000000"
        feedback_url = f"{FRONTEND_BASE}/en/beta-feedback/00000000-0000-0000-0000-000000000000"
        subject, html_body = render_template(
            template, {"full_name": "there", "results_url": results_url, "feedback_url": feedback_url}, locale="en"
        )
        send_email(to=args.test, subject=subject, html_body=html_body, supabase=supabase)
        print(f"Test email sent to {args.test}")
        return

    recipients = find_recipients()
    already_sent = load_sent_log()
    pending = [r for r in recipients if r["id"] not in already_sent]

    print(f"{len(recipients)} affected people, {len(already_sent)} already sent, {len(pending)} pending.")

    if not args.send:
        print("Dry run — no emails sent. Pass --send to broadcast.")
        for r in pending:
            print(f"  {r['email']}  ({r.get('full_name') or 'no name'})  locale={r.get('locale')}  response_id={r['id']}")
        return

    sent_count, failed = 0, []
    for r in pending:
        locale = r.get("locale") or "en"
        results_url = f"{FRONTEND_BASE}/{locale}/results/{r['id']}"
        feedback_url = f"{FRONTEND_BASE}/{locale}/beta-feedback/{r['id']}"
        subject, html_body = render_template(
            template, {"full_name": r.get("full_name") or "", "results_url": results_url, "feedback_url": feedback_url}, locale=locale
        )
        try:
            send_email(to=r["email"], subject=subject, html_body=html_body, supabase=supabase)
            append_sent_log(r["id"], already_sent)
            sent_count += 1
            print(f"Sent to {r['email']} ({sent_count}/{len(pending)})")
        except Exception as e:
            failed.append(r["email"])
            print(f"FAILED to send to {r['email']}: {e}")
        time.sleep(0.5)

    print(f"\nDone. Sent {sent_count}/{len(pending)}.")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed)}")


if __name__ == "__main__":
    main()
