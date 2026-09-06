"""
One-off broadcast of the 'beta_invite' email_templates row to every row in
waitlist_signups. Re-runnable: successfully-sent addresses are appended to
sent_beta_invite_log.json (next to this script) and skipped on future runs,
so a crash partway through doesn't cause duplicate sends on retry.

Usage:
  python scripts/send_beta_invite.py --test you@example.com   # send one test copy, no log write
  python scripts/send_beta_invite.py --dry-run                 # list recipients, send nothing
  python scripts/send_beta_invite.py --send                    # actually broadcast
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

from smtp_service import render_template, send_email  # noqa: E402

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sent_beta_invite_log.json")
UNSUBSCRIBE_MAILTO = "mailto:info@myetijahi.com?subject=Unsubscribe"


def load_sent_log() -> set:
    if not os.path.exists(LOG_PATH):
        return set()
    with open(LOG_PATH) as f:
        return set(json.load(f))


def append_sent_log(email: str, sent: set):
    sent.add(email)
    with open(LOG_PATH, "w") as f:
        json.dump(sorted(sent), f, indent=2)


def first_name_of(full_name: str | None) -> str:
    if not full_name:
        return "there"
    return full_name.strip().split(" ")[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", help="Send a single test copy to this address instead of broadcasting")
    parser.add_argument("--dry-run", action="store_true", help="List recipients without sending")
    parser.add_argument("--send", action="store_true", help="Actually send to every unsent waitlist address")
    args = parser.parse_args()

    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    template_row = supabase.table("email_templates").select("*").eq("key", "beta_invite").limit(1).execute()
    if not template_row.data:
        print("beta_invite template not found — apply migrations/beta_invite_email_template.sql first.")
        sys.exit(1)
    template = template_row.data[0]

    if args.test:
        subject, html_body = render_template(
            template, {"first_name": "there", "unsubscribe_url": UNSUBSCRIBE_MAILTO}
        )
        send_email(to=args.test, subject=subject, html_body=html_body, supabase=supabase)
        print(f"Test email sent to {args.test}")
        return

    rows = supabase.table("waitlist_signups").select("email, name").execute().data or []
    already_sent = load_sent_log()
    pending = [r for r in rows if r["email"] not in already_sent]

    print(f"{len(rows)} total waitlist signups, {len(already_sent)} already sent, {len(pending)} pending.")

    if not args.send:
        print("Dry run — no emails sent. Pass --send to broadcast.")
        for r in pending:
            print(f"  {r['email']}  ({r.get('name') or 'no name'})")
        return

    sent_count, failed = 0, []
    for r in pending:
        email = r["email"]
        subject, html_body = render_template(
            template,
            {"first_name": first_name_of(r.get("name")), "unsubscribe_url": UNSUBSCRIBE_MAILTO},
        )
        try:
            send_email(to=email, subject=subject, html_body=html_body, supabase=supabase)
            append_sent_log(email, already_sent)
            sent_count += 1
            print(f"Sent to {email} ({sent_count}/{len(pending)})")
        except Exception as e:
            failed.append(email)
            print(f"FAILED to send to {email}: {e}")
        time.sleep(0.5)  # be gentle on the SMTP connection for a large batch

    print(f"\nDone. Sent {sent_count}/{len(pending)}.")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed)}")


if __name__ == "__main__":
    main()
