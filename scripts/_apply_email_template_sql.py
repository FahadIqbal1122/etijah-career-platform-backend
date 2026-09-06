"""One-off helper: parse a single-row `insert into email_templates (...) values (...)`
migration file (the format used under migrations/) and upsert it via the Supabase
client, since this project has no direct Postgres/psql access configured locally.
"""
import os
import re
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def parse_single_row_insert(sql: str):
    cols_match = re.search(r"insert into email_templates \(([^)]+)\)", sql)
    columns = [c.strip() for c in cols_match.group(1).split(",")]

    values_start = sql.index("values") + len("values")
    body = sql[values_start:].strip()
    assert body.startswith("(")
    body = body[1:]

    values = []
    buf = ""
    in_string = False
    i = 0
    while i < len(body):
        ch = body[i]
        if in_string:
            if ch == "'" and i + 1 < len(body) and body[i + 1] == "'":
                buf += "'"
                i += 2
                continue
            if ch == "'":
                in_string = False
                i += 1
                continue
            buf += ch
            i += 1
            continue
        else:
            if ch == "'":
                in_string = True
                i += 1
                continue
            if ch == ")":
                values.append(buf.strip())
                break
            if ch == ",":
                values.append(buf.strip())
                buf = ""
                i += 1
                continue
            buf += ch
            i += 1

    cleaned = []
    for v in values:
        v = v.strip()
        if v.endswith("::jsonb"):
            v = v[: -len("::jsonb")].strip()
        if v == "true":
            v = True
        elif v == "false":
            v = False
        cleaned.append(v)

    return dict(zip(columns, cleaned))


def main():
    path = sys.argv[1]
    with open(path) as f:
        sql = f.read()
    row = parse_single_row_insert(sql)
    import json
    row["variables"] = json.loads(row["variables"])

    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    result = supabase.table("email_templates").upsert(row, on_conflict="key").execute()
    print("Upserted:", result.data[0]["key"] if result.data else result)


if __name__ == "__main__":
    main()
