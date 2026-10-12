"""Re-scores the six RIASEC types of saved assessments with the scoring fixed on 12 Oct 2026.

What changed: the either/or questions (Q6, QFC_RI, QFC_SE) now score 6/1 and credit the opposite type, so every type can
reach 0-100, and raw_score is the plain sum of the answers (it used to include the flat-profile x3 weight).

Dry run by default (prints what would change, writes nothing):
    PYTHONPATH=. python scripts/recalculate_riasec.py
Write the corrections:
    PYTHONPATH=. python scripts/recalculate_riasec.py --apply

Only framework='riasec' rows are touched. Run scripts/compute_score_norms.py afterwards (the population averages move),
and regenerate any report whose text quotes RIASEC scores. Reports already generated keep their cached text.
"""
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(".env")
import scoring_engine as se

apply = "--apply" in sys.argv
sb = create_client(os.environ["SUPABASE_URL"], os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"])


def fetch_all(table, cols):
    rows, offset = [], 0
    while True:
        batch = sb.table(table).select(cols).range(offset, offset + 999).execute().data
        rows += batch
        offset += 1000
        if len(batch) < 1000:
            return rows


stored = {}
for r in fetch_all("assessment_results", "response_id,framework,dimension,raw_score,normalized_score"):
    if r["framework"] == "riasec":
        stored.setdefault(r["response_id"], {})[r["dimension"]] = r

people = changed_people = rows_changed = skipped = missing_row = 0
for r in fetch_all("assessment_responses", "id,answers"):
    old = stored.get(r["id"])
    answers = r.get("answers")
    if not old or not isinstance(answers, dict) or not answers:
        skipped += 1
        continue
    people += 1
    new = {x["dimension"]: x for x in se.compute_scores(answers) if x["framework"] == "riasec"}
    touched = False
    for dim, n in new.items():
        o = old.get(dim)
        if o is None:
            missing_row += 1   # a type that had no saved row (not expected): left alone, reported
            continue
        if abs(float(o["normalized_score"]) - n["normalized_score"]) < 0.05 and abs(float(o["raw_score"]) - n["raw_score"]) < 0.05:
            continue
        rows_changed += 1
        touched = True
        if apply:
            sb.table("assessment_results").update({"raw_score": n["raw_score"], "normalized_score": n["normalized_score"]}) \
                .eq("response_id", r["id"]).eq("framework", "riasec").eq("dimension", dim).execute()
    changed_people += touched

print(f"{people} assessments checked | people with changed RIASEC: {changed_people} | rows {'updated' if apply else 'that would change'}: {rows_changed} | "
      f"skipped (no saved answers/results): {skipped} | types with no saved row: {missing_row}"
      + ("" if apply else "   (dry run: nothing written)"))
