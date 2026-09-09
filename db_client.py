"""Shared helper for every module-level `create_client(...)` Supabase client in
this app (main.py, report_generator.py, ai_provider.py, coaching_pipeline.py).
Standalone with no project-internal imports so any of those can import it
without risking a circular import."""

import httpx


def disable_http2(client):
    """supabase-py's postgrest sub-client hardcodes http2=True on its one shared
    httpx.Client (see SyncPostgrestClient.__init__ in postgrest-py) — every
    .table()/.rpc() call on a given `supabase` client goes through that single
    HTTP/2 connection. FastAPI's sync `def` routes run in a shared threadpool,
    so concurrent requests drive that one connection's h2 state machine from
    multiple OS threads at once. h2 isn't thread-safe for that: it corrupts
    mid-flight, surfacing as httpx.RemoteProtocolError (ConnectionTerminated),
    httpx.LocalProtocolError (StreamIDTooLowError, "Invalid input SEND_HEADERS"),
    or even a bare RuntimeError: deque mutated during iteration from h2's
    internal frame buffer. HTTP/1.1 connections are checked in/out of the pool
    one request at a time instead of shared, so this whole class of corruption
    can't happen with it — rebuild the session without http2 right after the
    client is constructed, before anything else touches it."""
    old = client.postgrest.session
    client.postgrest.session = httpx.Client(
        base_url=old.base_url, headers=old.headers, timeout=old.timeout,
        follow_redirects=True, http2=False,
    )
    return client
