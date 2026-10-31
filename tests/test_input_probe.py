"""Factorial probe isolates model-instruction and scraper changes."""
import unittest

from src.input_probe import VARIANTS, event_variants, compare_scores, summarize


class InputProbeTests(unittest.TestCase):
    def test_variants_isolate_each_change_and_url_removal(self):
        raw = {
            "url": "https://gocath.org/de/event/jugend",
            "title": "Jugendmesse",
            "description": "Gottesdienst. Ähnliche Veranstaltungen Yoga Workshop",
        }
        variants = event_variants("gocath", raw)
        self.assertEqual(set(variants), set(VARIANTS))
        self.assertEqual(variants["baseline"][0]["description"], raw["description"])
        self.assertEqual(variants["rules_only"][0], variants["baseline"][0])
        self.assertEqual(variants["clean_only"][0], variants["combined"][0])
        self.assertEqual(variants["optimized"][0], variants["combined"][0])
        self.assertIn("Gottesdienst.", variants["clean_only"][0]["description"])
        self.assertNotIn("Yoga", variants["clean_only"][0]["description"])
        self.assertEqual([variants[v][1] for v in VARIANTS],
                         [False, False, True, True, True])
        self.assertEqual([variants[v][2] for v in VARIANTS],
                         [False, False, False, False, True])

    def test_regnum_source_not_mutated(self):
        raw = {"url": "https://regnumchristi.eu/vid=1", "title": "Gebet",
               "description": "Gebetsabend mit jungen Erwachsenen"}
        variants = event_variants("regnum_christi", raw)
        self.assertTrue(all(v[0]["description"] == raw["description"] for v in variants.values()))

    def test_summary_counts_status_and_choice_changes(self):
        def outcome(tokens, status, different=False):
            return {"tokens": tokens, "relevance": status,
                    "comparison": {"mean_abs_score_change": .1 if different else 0,
                                   "choice_changed": {"format": ["a", "b"]} if different else {}}}
        rows = [{"variants": {
            "baseline": outcome(1000, "review"),
            "clean_only": outcome(900, "review"),
            "rules_only": outcome(700, "likely_relevant", True),
            "combined": outcome(650, "review"),
            "optimized": outcome(600, "review"),
        }}]
        result = summarize(rows)
        self.assertEqual(result["rules_only"]["relevance_changed_count"], 1)
        self.assertEqual(result["rules_only"]["choice_changed_count"], 1)
        self.assertEqual(result["clean_only"]["saved_percent"], 10)
        self.assertEqual(result["optimized"]["saved_input_tokens"], 400)


if __name__ == "__main__":
    unittest.main()
