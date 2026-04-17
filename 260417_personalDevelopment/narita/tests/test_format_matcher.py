import unittest

from app.services.format_matcher import match_format_with_score


class TestFormatMatcher(unittest.TestCase):
    def test_match_best_format(self):
        registered = [
            {
                "format_id": "fmt_a",
                "name": "A",
                "fields": [
                    {"box_norm": {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1}},
                    {"box_norm": {"x": 0.6, "y": 0.1, "w": 0.2, "h": 0.1}},
                ],
            },
            {
                "format_id": "fmt_b",
                "name": "B",
                "fields": [
                    {"box_norm": {"x": 0.1, "y": 0.5, "w": 0.2, "h": 0.1}},
                    {"box_norm": {"x": 0.6, "y": 0.5, "w": 0.2, "h": 0.1}},
                ],
            },
        ]

        detected = [
            {"x": 102, "y": 48, "w": 196, "h": 52},
            {"x": 598, "y": 52, "w": 202, "h": 50},
        ]

        matched, score, _ = match_format_with_score(registered, detected, 1000, 500)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["format_id"], "fmt_a")
        self.assertLess(score, 0.18)

    def test_unmatched_when_far(self):
        registered = [
            {
                "format_id": "fmt_a",
                "name": "A",
                "fields": [
                    {"box_norm": {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1}},
                ],
            }
        ]
        detected = [{"x": 900, "y": 450, "w": 50, "h": 20}]

        matched, score, _ = match_format_with_score(registered, detected, 1000, 500)
        self.assertIsNone(matched)
        self.assertGreater(score, 0.18)


if __name__ == "__main__":
    unittest.main()
