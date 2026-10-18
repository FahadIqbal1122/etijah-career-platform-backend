"""
Prints estimated Gemini / Claude spend for the last N days (default 3) from the ai_usage_log table, with the biggest
causes: per day, per model, per call label, per endpoint, per assessment, per client IP, and the priciest single calls.

    python scripts/ai_usage_report.py        # last 3 days
    python scripts/ai_usage_report.py 14
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import ai_usage

days = int(sys.argv[1]) if len(sys.argv) > 1 else 3
data = ai_usage.summarize(days=days, top=10)
print(f"Last {days} day(s): {data['calls']} calls, ~${data['est_cost_usd']} (estimate)\n")
for section in ("by_day", "by_provider_model", "by_kind", "by_label", "by_endpoint", "by_response_id", "by_client_ip"):
    print(f"-- {section}")
    for r in data[section]:
        print(f"  {str(r['key'])[:70]:<72} ${r['cost']:<9} {r['calls']:>6} calls  {r['out_tokens']:>9} out tok  {r['failed']} failed")
print("\n-- priciest calls")
for c in data["priciest_calls"]:
    print(" ", c)
