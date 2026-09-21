"""
One-off broadcast of the 'testimonial_request' email_templates row to everyone
who completed the Etijahi assessment during beta, asking for a short written
testimonial ahead of the next stage. English body goes to locale=en
responses, Arabic body to locale=ar responses (any other/missing locale
falls back to English).

Recipients are deduped by email, keeping their most recent response's name
and locale, matching the pattern in send_ai_impact_ready.py.

Usage:
  python scripts/send_testimonial_request.py --dry-run                 # list recipients, send nothing
  python scripts/send_testimonial_request.py --test you@example.com    # send one EN + one AR test copy now
  python scripts/send_testimonial_request.py --schedule "2026-09-17T15:00:00Z"
      # insert one scheduled_emails row per recipient for the given UTC time
      # (the existing VPS cron already polls scheduled_emails and sends what's due)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from smtp_service import render_template, send_email

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

TEMPLATE_KEY = "testimonial_request"

# Internal/staff addresses to skip.
EXCLUDE_EMAILS = {"business@etijahcoaching.com", "dina@etijahcoaching.com"}


def find_recipients():
    """One row per person (deduped by email, keeping their most recent
    completed response) among everyone who completed the assessment."""
    rows = supabase.table("assessment_responses") \
        .select("id, full_name, email, locale, created_at") \
        .eq("completed", True) \
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
    parser.add_argument("--test", help="Send one EN and one AR test copy to this address now")
    parser.add_argument("--dry-run", action="store_true", help="List recipients, send/schedule nothing")
    parser.add_argument("--schedule", help="Insert scheduled_emails rows for this UTC ISO datetime, e.g. 2026-09-17T15:00:00Z")
    args = parser.parse_args()

    template_row = supabase.table("email_templates").select("*").eq("key", TEMPLATE_KEY).limit(1).execute()
    if not template_row.data:
        print(f"{TEMPLATE_KEY} template not found — apply migrations/testimonial_request_email_template.sql first.")
        sys.exit(1)
    template = template_row.data[0]

    if args.test:
        for locale in ("en", "ar"):
            subject, html_body = render_template(template, {"full_name": "there" if locale == "en" else "صديقنا"}, locale=locale)
            send_email(to=args.test, subject=f"[TEST-{locale.upper()}] {subject}", html_body=html_body, supabase=supabase)
            print(f"Test {locale} email sent to {args.test}")
        return

    recipients = find_recipients()
    en_count = sum(1 for r in recipients if (r.get("locale") or "en") == "en")
    ar_count = sum(1 for r in recipients if r.get("locale") == "ar")
    other_count = len(recipients) - en_count - ar_count
    print(f"{len(recipients)} unique people completed the assessment: {en_count} en, {ar_count} ar, {other_count} other (sent as en).")

    if args.dry_run:
        for r in recipients:
            print(f"  {r['email']}  ({r.get('full_name') or 'no name'})  locale={r.get('locale')}")
        return

    if not args.schedule:
        print("Pass --schedule '<UTC ISO datetime>' to queue the send, or --dry-run to just list recipients.")
        return

    rows = []
    for r in recipients:
        locale = r.get("locale") if r.get("locale") in ("en", "ar") else "en"
        rows.append({
            "template_key": TEMPLATE_KEY,
            "recipient_type": "single",
            "recipient_email": r["email"],
            "recipient_name": r.get("full_name"),
            "locale": locale,
            "variables": {"full_name": r.get("full_name") or ("there" if locale == "en" else "صديقنا")},
            "scheduled_for": args.schedule,
        })

    inserted = supabase.table("scheduled_emails").insert(rows).execute()
    print(f"Scheduled {len(inserted.data or [])} emails for {args.schedule} ({en_count} en, {ar_count} ar).")


if __name__ == "__main__":
    main()
