"""The daily AI spend cap (ai_usage.check_budget): blocks new AI calls once the last 24h of estimated spend reaches the
cap, alerts once a day, can be switched off, and never blocks when the spend cannot be read."""
import unittest

import ai_usage


class _Q:
    def __init__(self, rows, boom):
        self._rows, self._boom = rows, boom

    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def gte(self, *a, **k): return self
    def order(self, *a, **k): return self
    def range(self, *a, **k): return self

    def execute(self):
        if self._boom:
            raise RuntimeError("db down")
        return type("R", (), {"data": self._rows})()


class _DB:
    def __init__(self, spent_rows=(), cap_rows=(), boom=False):
        self.spent_rows, self.cap_rows, self.boom = list(spent_rows), list(cap_rows), boom

    def table(self, name):
        return _Q(self.cap_rows if name == "app_settings" else self.spent_rows, self.boom)


def _setup(spent=0.0, cap_setting=None, boom=False):
    ai_usage._client = _DB([{"est_cost_usd": spent}] if spent else [],
                           [{"value": cap_setting}] if cap_setting is not None else [], boom)
    ai_usage._budget.update(spent=0.0, pending=0.0, cap=ai_usage.DEFAULT_DAILY_CAP_USD, checked_at=None, alerted=None)
    alerts = []
    ai_usage.set_cap_alert(lambda spent, cap: alerts.append((spent, cap)))
    return alerts


class DailyCapTests(unittest.TestCase):
    def tearDown(self):
        ai_usage._client = None
        ai_usage.set_cap_alert(None)

    def test_under_the_cap_nothing_is_blocked(self):
        _setup(spent=3.0)
        ai_usage.check_budget()

    def test_over_the_cap_blocks_and_alerts_once(self):
        alerts = _setup(spent=10.5)
        with self.assertRaises(ai_usage.DailyCapExceeded):
            ai_usage.check_budget()
        with self.assertRaises(ai_usage.DailyCapExceeded):
            ai_usage.check_budget()
        self.assertEqual(len(alerts), 1)

    def test_cap_setting_overrides_the_default(self):
        _setup(spent=10.5, cap_setting=50)
        ai_usage.check_budget()   # $10.5 is under the $50 the admin set
        _setup(spent=10.5, cap_setting=5)
        with self.assertRaises(ai_usage.DailyCapExceeded):
            ai_usage.check_budget()

    def test_zero_cap_means_no_cap(self):
        _setup(spent=500.0, cap_setting=0)
        ai_usage.check_budget()

    def test_unreadable_spend_never_blocks(self):
        _setup(boom=True)
        ai_usage.check_budget()

    def test_an_unpriced_model_is_never_free(self):
        self.assertGreater(ai_usage._estimate("some-new-model", 100_000, 0, 50_000), 1.0)
        self.assertEqual(ai_usage._estimate("claude-haiku-5-5", 1_000_000, 0, 0), 0.10)

    def test_spend_since_the_last_refresh_counts_immediately(self):
        _setup(spent=9.0)
        ai_usage.check_budget()   # reads $9, under the $10 cap
        ai_usage.record(provider="claude", model="claude-sonnet-4-6", kind="report", label="x",
                        input_tokens=100_000, output_tokens=60_000)   # ~$1.20, before the writer has stored it
        with self.assertRaises(ai_usage.DailyCapExceeded):
            ai_usage.check_budget()


if __name__ == "__main__":
    unittest.main()
