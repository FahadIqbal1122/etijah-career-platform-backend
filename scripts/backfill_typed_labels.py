"""Adds the English twins (QOFIELD_en, QO5_other_en, QO6_other_en) to assessments submitted before they existed.

Dry run by default (prints what it would store, writes nothing):
    PYTHONPATH=. python scripts/backfill_typed_labels.py
Write the changes:
    PYTHONPATH=. python scripts/backfill_typed_labels.py --apply

Only adds new keys inside answers; no other column or key is touched. Reports already generated stay cached; a
regenerated report picks the English label up for career matching.
"""
import os
import re
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(".env")
import report_generator as rg

apply = "--apply" in sys.argv
sb = create_client(os.environ["SUPABASE_URL"], os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"])
non_ascii = re.compile(r"[^\x00-\x7F]")

rows = sb.table("assessment_responses").select("id,answers").execute().data
todo = changed = 0
for r in rows:
    answers = r.get("answers") or {}
    labels = {k: answers.get(k) for k in rg.TYPED_LABEL_KEYS
              if isinstance(answers.get(k), str) and non_ascii.search(answers[k]) and f"{k}_en" not in answers}
    if not labels:
        continue
    todo += 1
    english = rg.translate_typed_labels(labels)
    if not english:
        print(f"{r['id'][:8]}: could not translate {labels}")
        continue
    changed += 1
    print(f"{r['id'][:8]}: " + ", ".join(f"{k} {labels[k]!r} -> {v!r}" for k, v in english.items()))
    if apply:
        sb.table("assessment_responses").update({"answers": {**answers, **{f"{k}_en": v for k, v in english.items()}}}).eq("id", r["id"]).execute()
print(f"{todo} assessments have untranslated Arabic text; {changed} {'updated' if apply else 'would be updated'}.")
