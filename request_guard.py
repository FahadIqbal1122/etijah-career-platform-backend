"""Abuse guards for the public (no-login) endpoints: a request-size cap, and per-IP rate limits on the POST
endpoints that anyone can call and that write to the database. Registered as middleware in main.py (inside the CORS
layer, so a refusal still carries the CORS headers and the browser can read it)."""
import re
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

MAX_BODY_BYTES = 1_000_000          # assessment submissions are a few tens of KB; nothing public needs more
MAX_ADMIN_BODY_BYTES = 20_000_000   # admin uploads (coaching transcripts, bulk imports)

# path -> (max requests, window seconds) per client IP. Limits are generous: a classroom or an office shares one IP.
# Only endpoints the BROWSER calls directly belong here. /waitlist, /partners, /bug-report, /feedback, /waitlist/events and
# /featured-course/events are reached through the frontend's /api/* routes (server to server), so the backend sees one
# IP for every visitor; those routes carry their own per-visitor limit (frontend src/lib/rateLimit.ts).
POST_LIMITS: dict[str, tuple[int, int]] = {
    "/assessment/telemetry": (6000, 3600),
    # Anonymous, and each submit queues an email to the address typed in plus an AI call. Roomy enough for a school
    # computer lab sharing one IP; main.py also caps the emails sent to any one address.
    "/assessment/submit": (200, 3600),
    # Answers "does this email/phone already have a report", so it must not be scriptable.
    "/assessment/check-existing": (60, 3600),
}
# GET endpoints that are expensive and open to anyone holding a report link (the PDF is rebuilt on every call).
GET_LIMITS: list[tuple["re.Pattern[str]", tuple[int, int]]] = [
    (re.compile(r"^/assessment/[^/]+/report$"), (60, 3600)),
]
PREFIX_LIMITS: list[tuple[str, tuple[int, int]]] = [("/beta-feedback/", (600, 3600))]

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    """Behind Traefik the LAST X-Forwarded-For entry is the one the proxy appended; earlier ones are client-supplied."""
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[-1].strip() if fwd else "") or (request.client.host if request.client else "unknown")


def allow(key: str, limit: tuple[int, int]) -> bool:
    max_hits, window = limit
    now = time.monotonic()
    with _lock:
        if len(_hits) > 20000:   # bounded memory: forget keys idle for longer than the longest window
            for k in [k for k, d in _hits.items() if not d or d[-1] < now - 3600]:
                del _hits[k]
        q = _hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= max_hits:
            return False
        q.append(now)
        return True


def _limit_for(path: str) -> tuple[str, tuple[int, int]] | None:
    if path in POST_LIMITS:
        return path, POST_LIMITS[path]
    for prefix, lim in PREFIX_LIMITS:
        if path.startswith(prefix):
            return prefix, lim
    return None


class RequestGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            cap = MAX_ADMIN_BODY_BYTES if request.url.path.startswith("/admin/") else MAX_BODY_BYTES
            try:
                size = int(request.headers.get("content-length") or 0)
            except ValueError:
                size = 0
            if size > cap:
                return JSONResponse(status_code=413, content={"detail": "Request too large"})
        found = None
        if request.method == "POST":
            found = _limit_for(request.url.path)
        elif request.method == "GET":
            for pattern, lim in GET_LIMITS:
                if pattern.match(request.url.path):
                    found = (pattern.pattern, lim)
                    break
        if found and not allow(f"{found[0]}|{client_ip(request)}", found[1]):
            return JSONResponse(status_code=429, content={"detail": "Too many requests, please try again later."})
        response = await call_next(request)
        # API responses are JSON, never pages: say so, and keep browsers from sniffing or framing them.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response
