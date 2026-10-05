"""Corrects the emotional-stability score saved before 4 Oct 2026, when Q21 and Q22 were scored backwards.

Dry run by default (prints what would change, writes nothing):
    PYTHONPATH=. python scripts/recalculate_stability.py
Write the corrections:
    PYTHONPATH=. python scripts/recalculate_stability.py --apply

Each assessment is re-scored from its saved answers with the current scoring code. Only the big_five / stability row is
written; every other row is compared and reported but never touched, so a mismatch there is a warning, not a change.
Reports that were already generated keep their cached text (written from the old score); regenerate them if the
sentence about emotional stability matters.
"""
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(".env")
import scoring_engine as se

apply = "--apply" in sys.argv
sb = create_client(os.environ["SUPABASE_URL"], os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"])

stored = {}
offset = 0
while True:
    batch = sb.table("assessment_results").select("response_id,framework,dimension,raw_score,normalized_score").range(offset, offset + 999).execute().data
    for r in batch:
        stored.setdefault(r["response_id"], {})[(r["framework"], r["dimension"])] = r
    offset += 1000
    if len(batch) < 1000:
        break

responses, offset = [], 0
while True:
    batch = sb.table("assessment_responses").select("id,answers").range(offset, offset + 999).execute().data
    responses += batch
    offset += 1000
    if len(batch) < 1000:
        break

changed = unchanged = no_answers = other_mismatch = 0
before, after = [], []
for r in responses:
    old = stored.get(r["id"])
    answers = r.get("answers")
    if not old or not isinstance(answers, dict) or not answers:
        no_answers += 1
        continue
    new = {(x["framework"], x["dimension"]): x for x in se.compute_scores(answers)}
    mism = [k for k, v in new.items() if k != ("big_five", "stability") and k in old and abs(float(old[k]["normalized_score"]) - v["normalized_score"]) > 0.05]
    if mism:
        other_mismatch += 1
        print(f"  warning {r['id'][:8]}: other dimensions differ from the saved ones {mism[:3]} (left untouched)")
    key = ("big_five", "stability")
    if key not in new or key not in old:
        continue
    o, n = float(old[key]["normalized_score"]), new[key]["normalized_score"]
    if abs(o - n) < 0.05:
        unchanged += 1
        continue
    changed += 1
    before.append(o); after.append(n)
    if apply:
        sb.table("assessment_results").update({"raw_score": new[key]["raw_score"], "normalized_score": new[key]["normalized_score"]}) \
            .eq("response_id", r["id"]).eq("framework", "big_five").eq("dimension", "stability").execute()

mean = lambda v: sum(v) / len(v) if v else 0
print(f"{len(responses)} assessments | stability {'corrected' if apply else 'would change'}: {changed} | already right: {unchanged} | skipped (no saved answers/results): {no_answers} | "
      f"warnings on other dimensions: {other_mismatch}")
print(f"average stability {mean(before):.0f} -> {mean(after):.0f} for the {changed} affected" + ("" if apply else "   (dry run: nothing written)"))
