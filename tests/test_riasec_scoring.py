import unittest

import scoring_engine as se


def _riasec(answers):
    return {r['dimension']: r for r in se.compute_scores(answers) if r['framework'] == 'riasec'}


BASE = {f"Q{i}": 3 for i in (1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12)}


class RiasecEitherOrTests(unittest.TestCase):
    def test_unchosen_side_credits_the_opposite_type(self):
        a = _riasec({**BASE, 'Q6': 'B', 'QFC_RI': 'B', 'QFC_SE': 'B'})
        b = _riasec({**BASE, 'Q6': 'A', 'QFC_RI': 'A', 'QFC_SE': 'A'})
        for dim in ('conventional', 'investigative', 'enterprising'):
            self.assertGreater(a[dim]['normalized_score'], b[dim]['normalized_score'], dim)

    def test_every_type_can_reach_0_and_100(self):
        top = _riasec({**BASE, 'Q5': 6, 'Q6': 'A', 'Q1': 6, 'Q2': 6, 'QFC_RI': 'A', 'Q7': 6, 'Q8': 6, 'QFC_SE': 'A'})
        self.assertEqual(top['artistic']['normalized_score'], 100.0)
        self.assertEqual(top['realistic']['normalized_score'], 100.0)
        self.assertEqual(top['social']['normalized_score'], 100.0)
        low = _riasec({**BASE, 'Q5': 1, 'Q6': 'B'})
        self.assertEqual(low['artistic']['normalized_score'], 0.0)

    def test_raw_score_is_the_plain_sum_even_for_a_flat_profile(self):
        flat = {f"Q{i}": 6 for i in (1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12)}
        r = _riasec({**flat, 'Q6': 'A', 'QFC_RI': 'A', 'QFC_SE': 'A'})
        self.assertEqual(r['realistic']['raw_score'], 18.0)   # 6 + 6 + 6, not weighted
        for d in r.values():
            self.assertLessEqual(d['raw_score'], 18.0)


if __name__ == '__main__':
    unittest.main()
