"""
One-off script: export two CSVs for the beta outreach lists, using the exact
same matching logic as _resolve_segment_recipients() in main.py (segments
'waitlist_assessment_no_feedback' and 'waitlist_no_assessment').

Run from etijah-career-platform-backend/ with its venv active:
    python3 scripts/export_beta_segments.py

Writes:
    ../Documents/beta_no_feedback.csv    — completed the assessment, never finished the full (stage 2) feedback form
    ../Documents/beta_no_assessment.csv  — signed up for the waitlist, never completed an assessment
"""
import os
import csv
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from db_client import disable_http2

FRONTEND_BASE = "https://myetijahi.com"
OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "Documents",
)


def main():
    supabase = disable_http2(create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"]))

    waitlist_rows = supabase.table('waitlist_signups').select('email, name, phone, locale, created_at').execute().data or []
    assessment_rows = supabase.table('assessment_responses').select('id, email, full_name, phone, completed, locale').execute().data or []

    # Same "prefer the completed row" collision handling as _resolve_segment_recipients.
    assessment_by_email: dict[str, dict] = {}
    for r in assessment_rows:
        email = (r.get('email') or '').strip().lower()
        if not email:
            continue
        existing = assessment_by_email.get(email)
        if existing is None or (r.get('completed') and not existing.get('completed')):
            assessment_by_email[email] = r

    fb_rows = supabase.table('beta_feedback').select('response_id').not_.is_('stage2_completed_at', 'null').execute().data or []
    stage2_done_ids = {r['response_id'] for r in fb_rows}

    no_feedback_rows = []
    no_assessment_rows = []
    seen_emails = set()

    for w in waitlist_rows:
        email = (w.get('email') or '').strip().lower()
        if not email or email in seen_emails:
            continue
        seen_emails.add(email)

        assessment = assessment_by_email.get(email)
        completed = bool(assessment and assessment.get('completed'))
        locale = ((assessment or {}).get('locale') or w.get('locale') or 'en')
        name = ((assessment or {}).get('full_name') or w.get('name') or '')
        # Prefer the assessment's phone (required field there) over the waitlist
        # form's (optional, less consistently filled), same precedence as name/locale.
        phone = ((assessment or {}).get('phone') or w.get('phone') or '')

        if not completed:
            no_assessment_rows.append({
                "email": w['email'],
                "name": name,
                "phone": phone,
                "language": "Arabic" if locale == "ar" else "English",
                "signed_up_at": w.get('created_at') or '',
                "assessment_link": f"{FRONTEND_BASE}/{locale}/assessment",
            })
            continue

        response_id = assessment['id']
        if response_id in stage2_done_ids:
            continue  # completed the full feedback form — not part of this list

        no_feedback_rows.append({
            "email": w['email'],
            "name": name,
            "phone": phone,
            "language": "Arabic" if locale == "ar" else "English",
            "feedback_form_link": f"{FRONTEND_BASE}/{locale}/beta-feedback/{response_id}",
        })

    os.makedirs(OUT_DIR, exist_ok=True)

    path1 = os.path.join(OUT_DIR, "beta_no_feedback.csv")
    with open(path1, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "name", "phone", "language", "feedback_form_link"])
        writer.writeheader()
        writer.writerows(no_feedback_rows)
    print(f"wrote {path1} ({len(no_feedback_rows)} rows)")

    path2 = os.path.join(OUT_DIR, "beta_no_assessment.csv")
    with open(path2, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "name", "phone", "language", "signed_up_at", "assessment_link"])
        writer.writeheader()
        writer.writerows(no_assessment_rows)
    print(f"wrote {path2} ({len(no_assessment_rows)} rows)")


if __name__ == "__main__":
    main()
