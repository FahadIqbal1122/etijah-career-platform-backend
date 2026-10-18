"""
AI spend tracking. Every Gemini / Claude call records its tokens, an estimated cost and what caused it (endpoint,
assessment, client IP, call label) in the ai_usage_log table (migrations/ai_usage_log.sql) and as one
"[AI usage] ..." line in the container logs, so a cost spike can be traced to a cause instead of guessed at.

Self-contained like ai_provider.py (own Supabase client, no project imports) so any module can import it without a
cycle. Recording must never break or slow a request: rows are queued and written by a background thread, and every
failure here is swallowed. If the table does not exist yet the log lines still appear.

Costs are ESTIMATES from the PRICES table below (USD per 1M tokens: input, output incl. thinking, cached input).
Update it when prices change; the provider consoles remain the source of truth for the bill.

Report on it with:  python scripts/ai_usage_report.py [days]   or   GET /admin/ai-usage?days=3
"""

import contextvars
import os
import queue
import re
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta

PRICES = {
    "gemini-2.5-flash": (0.30, 2.50, 0.03),
    "gemini-embedding-001": (0.15, 0.0, 0.0),
    "claude-sonnet-4-6": (3.00, 15.00, 0.30),
}
EXPENSIVE_CALL_USD = 0.25   # a single call above this gets an extra warning line in the logs

# Set per request by RequestGuardMiddleware (request_guard.py): {"path": ..., "ip": ...}. Copied into worker threads
# by anyio / _submit_in_context, so AI calls made deep inside a request still know which request caused them.
_request_ctx: contextvars.ContextVar = contextvars.ContextVar("ai_usage_request", default=None)

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def set_request_context(path: str, ip: str | None):
    _request_ctx.set({"path": path, "ip": ip})


def from_gemini(usage) -> dict:
    """Token fields from a Gemini response's usage_metadata (generate_content). Thinking tokens are billed as output."""
    if usage is None:
        return {}
    prompt = int(getattr(usage, "prompt_token_count", 0) or 0)
    cached = int(getattr(usage, "cached_content_token_count", 0) or 0)
    cand = int(getattr(usage, "candidates_token_count", 0) or 0)
    total = int(getattr(usage, "total_token_count", 0) or 0)
    thinking = int(getattr(usage, "thoughts_token_count", 0) or 0) or max(0, total - prompt - cand)
    return {"input_tokens": max(0, prompt - cached), "cached_tokens": cached,
            "output_tokens": cand + thinking, "thinking_tokens": thinking}


def from_claude(usage) -> dict:
    """Token fields from an Anthropic response's usage."""
    if usage is None:
        return {}
    created = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
    return {"input_tokens": int(getattr(usage, "input_tokens", 0) or 0) + created,
            "cached_tokens": int(getattr(usage, "cache_read_input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0), "thinking_tokens": 0}


def _estimate(model: str, input_tokens: int, cached_tokens: int, output_tokens: int) -> float:
    p_in, p_out, p_cached = PRICES.get(model or "", (0.0, 0.0, 0.0))
    return (input_tokens * p_in + cached_tokens * p_cached + output_tokens * p_out) / 1_000_000


def record(*, provider: str, model: str, kind: str, label: str = "", response_id: str | None = None,
           input_tokens: int = 0, cached_tokens: int = 0, output_tokens: int = 0, thinking_tokens: int = 0,
           seconds: float | None = None, ok: bool = True, error: str | None = None):
    """Log one AI call. Never raises."""
    try:
        ctx = _request_ctx.get() or {}
        path = ctx.get("path") or ""
        label = label or ""
        found = _UUID.search(label) or _UUID.search(path)
        rid = response_id or (found.group(0) if found else None)
        cost = _estimate(model, input_tokens, cached_tokens, output_tokens)
        row = {
            "provider": provider, "model": model, "kind": kind,
            "label": _UUID.sub("", label).rstrip(":") or None,
            "endpoint": _UUID.sub("{id}", path) or None,
            "response_id": rid, "client_ip": ctx.get("ip"),
            "input_tokens": input_tokens, "cached_tokens": cached_tokens,
            "output_tokens": output_tokens, "thinking_tokens": thinking_tokens,
            "est_cost_usd": round(cost, 5), "seconds": round(seconds, 2) if seconds is not None else None,
            "ok": ok, "error": (error or None) and error[:200],
        }
        print(f"[AI usage] {provider}/{model} kind={kind} label={row['label']} endpoint={row['endpoint']} "
              f"rid={rid} ip={row['client_ip']} in={input_tokens} cached={cached_tokens} out={output_tokens} "
              f"think={thinking_tokens} ~${cost:.4f} {seconds or 0:.1f}s ok={ok}" + (f" err={error}" if error else ""))
        if cost >= EXPENSIVE_CALL_USD:
            print(f"[AI usage] EXPENSIVE CALL ~${cost:.2f}: {provider}/{model} label={row['label']} endpoint={row['endpoint']}")
        _queue.put_nowait(row)
        _ensure_worker()
    except queue.Full:
        pass
    except Exception as e:  # tracking must never break a request
        print("[AI usage] could not record:", type(e).__name__, e)


# ── background writer ────────────────────────────────────────────────────────
_queue: "queue.Queue[dict]" = queue.Queue(maxsize=5000)
_worker_started = False
_worker_lock = threading.Lock()
_client = None


def _get_client():
    global _client
    if _client is None:
        from supabase import create_client
        from db_client import disable_http2
        _client = disable_http2(create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")))
    return _client


def _ensure_worker():
    global _worker_started
    if _worker_started:
        return
    with _worker_lock:
        if not _worker_started:
            threading.Thread(target=_writer, name="ai-usage-writer", daemon=True).start()
            _worker_started = True


def _writer():
    last_warn = 0.0
    while True:
        batch = [_queue.get()]
        time.sleep(1.0)   # let a burst (one report = many calls) collect into one insert
        while len(batch) < 100:
            try:
                batch.append(_queue.get_nowait())
            except queue.Empty:
                break
        try:
            _get_client().table("ai_usage_log").insert(batch).execute()
        except Exception as e:
            if time.monotonic() - last_warn > 600:   # e.g. migration not applied yet: say so, but not on every batch
                print("[AI usage] could not write ai_usage_log (log lines still work):", type(e).__name__, str(e)[:200])
                last_warn = time.monotonic()


# ── reporting ────────────────────────────────────────────────────────────────
def summarize(days: int = 3, top: int = 10) -> dict:
    """Aggregated spend for the last `days` days: totals, per day, and the biggest causes."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows: list[dict] = []
    client = _get_client()
    for page in range(100):   # up to 100k rows
        chunk = (client.table("ai_usage_log").select("*").gte("created_at", since)
                 .order("created_at").range(page * 1000, page * 1000 + 999).execute().data or [])
        rows += chunk
        if len(chunk) < 1000:
            break

    def group(keyfn, limit=top, by_cost=True):
        ranked = list(_by(rows, keyfn).items())
        if by_cost:
            ranked.sort(key=lambda kv: -kv[1]["cost"])
        else:
            ranked.sort(key=lambda kv: str(kv[0]))
        return [{"key": k, **{x: (round(v, 3) if x == "cost" else v) for x, v in a.items()}} for k, a in ranked[:limit]]

    by_day = group(lambda r: str(r["created_at"])[:10], limit=days + 1, by_cost=False)
    priciest = sorted(rows, key=lambda r: -float(r.get("est_cost_usd") or 0))[:top]
    return {
        "since": since, "calls": len(rows), "est_cost_usd": round(sum(float(r.get("est_cost_usd") or 0) for r in rows), 3),
        "by_day": by_day,
        "by_provider_model": group(lambda r: f"{r['provider']}/{r.get('model')}"),
        "by_kind": group(lambda r: r.get("kind")),
        "by_label": group(lambda r: r.get("label")),
        "by_endpoint": group(lambda r: r.get("endpoint")),
        "by_response_id": group(lambda r: r.get("response_id")),
        "by_client_ip": group(lambda r: r.get("client_ip")),
        "priciest_calls": [{k: r.get(k) for k in ("created_at", "provider", "model", "label", "endpoint", "response_id",
                                                  "client_ip", "input_tokens", "output_tokens", "thinking_tokens",
                                                  "est_cost_usd", "seconds", "ok")} for r in priciest],
    }


def _by(rows, keyfn) -> dict:
    agg: dict = defaultdict(lambda: {"calls": 0, "cost": 0.0, "out_tokens": 0, "failed": 0})
    for r in rows:
        a = agg[keyfn(r)]
        a["calls"] += 1
        a["cost"] += float(r.get("est_cost_usd") or 0)
        a["out_tokens"] += int(r.get("output_tokens") or 0)
        a["failed"] += 0 if r.get("ok") else 1
    return agg
