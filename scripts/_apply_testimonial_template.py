"""One-off helper: parse migrations/testimonial_request_email_template.sql's
single-quoted literals (with '' escapes) and insert the row via the Supabase
table API, since this environment has no direct Postgres/psql access for
running the .sql migration file itself. Not meant to be reused."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrations", "testimonial_request_email_template.sql")
text = open(path, encoding="utf-8").read()

# Grab everything between "values" and the trailing ") on conflict"
start = text.index("values") + len("values")
end = text.rindex(")\non conflict")
body = text[start:end]

# Tokenize single-quoted string literals with '' as an escaped quote.
literals = []
i = 0
n = len(body)
while i < n:
    if body[i] == "'":
        j = i + 1
        buf = []
        while j < n:
            if body[j] == "'" and j + 1 < n and body[j + 1] == "'":
                buf.append("'")
                j += 2
                continue
            if body[j] == "'":
                break
            buf.append(body[j])
            j += 1
        literals.append("".join(buf))
        i = j + 1
    else:
        i += 1

assert len(literals) == 8, f"expected 8 string literals (variables cast counts as one), got {len(literals)}"
key, name, description, subject_en, subject_ar, body_html_en, body_html_ar, variables_json = literals

row = {
    "key": key,
    "name": name,
    "description": description,
    "is_active": True,
    "subject_en": subject_en,
    "subject_ar": subject_ar,
    "body_html_en": body_html_en,
    "body_html_ar": body_html_ar,
    "variables": json.loads(variables_json),
}

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
existing = supabase.table("email_templates").select("key").eq("key", key).execute()
if existing.data:
    print(f"{key} already exists — not overwriting (on conflict do nothing).")
else:
    supabase.table("email_templates").insert(row).execute()
    print(f"Inserted email_templates row for key={key!r}.")
