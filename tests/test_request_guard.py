import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import request_guard
from request_guard import RequestGuardMiddleware


def make_client():
    app = FastAPI()
    app.add_middleware(RequestGuardMiddleware)

    @app.post("/waitlist")
    def waitlist(body: dict): return {"ok": True}

    @app.post("/assessment/submit")
    def submit(body: dict): return {"ok": True}

    @app.post("/admin/big")
    def big(body: dict): return {"ok": True}

    return TestClient(app)


class RequestGuardTests(unittest.TestCase):
    def setUp(self):
        request_guard._hits.clear()

    def test_oversized_public_body_is_refused(self):
        r = make_client().post("/assessment/submit", content=b"{" + b" " * (request_guard.MAX_BODY_BYTES + 10) + b"}",
                               headers={"content-type": "application/json"})
        self.assertEqual(r.status_code, 413)

    def test_admin_body_gets_a_higher_cap(self):
        r = make_client().post("/admin/big", json={"t": "x" * 2_000_000})
        self.assertEqual(r.status_code, 200)

    def test_public_post_is_rate_limited_per_ip(self):
        c = make_client()
        limit = request_guard.POST_LIMITS["/waitlist"][0]
        codes = [c.post("/waitlist", json={}, headers={"x-forwarded-for": "9.9.9.9"}).status_code for _ in range(limit + 1)]
        self.assertEqual(codes[:limit], [200] * limit)
        self.assertEqual(codes[-1], 429)
        # another visitor is not affected
        self.assertEqual(c.post("/waitlist", json={}, headers={"x-forwarded-for": "8.8.8.8"}).status_code, 200)

    def test_spoofed_first_forwarded_entry_does_not_dodge_the_limit(self):
        c = make_client()
        limit = request_guard.POST_LIMITS["/waitlist"][0]
        for i in range(limit):
            c.post("/waitlist", json={}, headers={"x-forwarded-for": f"1.1.1.{i}, 7.7.7.7"})
        r = c.post("/waitlist", json={}, headers={"x-forwarded-for": "2.2.2.2, 7.7.7.7"})
        self.assertEqual(r.status_code, 429)


if __name__ == "__main__":
    unittest.main()
