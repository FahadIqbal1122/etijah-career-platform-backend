import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "test-key-for-claims")

import main


class ClaimTests(unittest.TestCase):
    def test_token_is_stable_and_per_response(self):
        a, b = main._claim_token("r1"), main._claim_token("r2")
        self.assertEqual(a, main._claim_token("r1"))
        self.assertNotEqual(a, b)
        self.assertTrue(a)

    def test_valid_token_links_an_unowned_report(self):
        fake = MagicMock()
        fake.table.return_value.update.return_value.eq.return_value.is_.return_value.execute.return_value.data = [{"id": "r1"}]
        user = MagicMock(id="u1")
        with patch.object(main, "supabase", fake):
            self.assertEqual(main._claim_response(user, "r1", main._claim_token("r1")), 1)
        fake.table.return_value.update.assert_called_once_with({"user_id": "u1"})

    def test_wrong_or_missing_token_links_nothing(self):
        fake = MagicMock()
        user = MagicMock(id="u1")
        with patch.object(main, "supabase", fake):
            self.assertEqual(main._claim_response(user, "r1", main._claim_token("r2")), 0)
            self.assertEqual(main._claim_response(user, "r1", ""), 0)
            self.assertEqual(main._claim_response(user, None, "x"), 0)
        fake.table.assert_not_called()

    def test_no_secret_means_no_token(self):
        with patch.object(main, "HUB_API_KEY", None), patch.dict(os.environ, {"SUPABASE_KEY": "", "CLAIM_TOKEN_SECRET": ""}):
            self.assertEqual(main._claim_token("r1"), "")
            self.assertEqual(main._claim_response(MagicMock(id="u"), "r1", ""), 0)


if __name__ == "__main__":
    unittest.main()
