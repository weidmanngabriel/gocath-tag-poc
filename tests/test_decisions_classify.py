import unittest
from unittest.mock import Mock, patch

from src.decisions_classify import classify_decisions, URL


class DecisionsClassifierTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "criteria": [
                {"id": "format_mass", "category": "Format", "label": "Heilige Messe",
                 "description": "Eine Messe findet statt", "threshold": 0.65, "weight": 1},
                {"id": "topic_faith", "category": "Thema", "label": "Glaubensbildung",
                 "description": "Glaubensinhalte", "threshold": 0.65, "weight": 1},
            ],
            "tags": ["Heilige Messe"],
        }
        self.event = {"title": "Fußballturnier", "description": "Fußball"}

    @patch("src.decisions_classify.requests.post")
    def test_all_scores_including_low_stored(self, post):
        response = Mock(ok=True)
        response.json.return_value = {
            "answers": [
                {"type": "predicate", "name": "topic_faith", "probability": 0.02},
                {"type": "predicate", "name": "format_mass", "probability": 0.94},
            ],
            "usage": {"input_tokens": 40, "output_tokens": 0, "total_tokens": 40,
                      "input_tokens_details": {"cached_tokens": 12}},
        }
        post.return_value = response
        usage = {}
        tags = classify_decisions(self.event, "secret", self.config, usage)
        self.assertEqual(post.call_args.args[0], URL)
        payload = post.call_args.kwargs["json"]
        self.assertEqual([q["name"] for q in payload["questions"]],
                         ["format_mass", "topic_faith"])
        self.assertTrue(all(q["type"] == "predicate" for q in payload["questions"]))
        self.assertEqual([s["score"] for s in tags["criteria_scores"]], [0.94, 0.02])
        self.assertEqual(tags["standard_tags"], ["Heilige Messe"])
        self.assertEqual(tags["additional_tags"], [])
        self.assertEqual(usage["cached_tokens"], 12)

    @patch("src.decisions_classify.requests.post")
    def test_missing_scores_rejected_not_misclassified(self, post):
        response = Mock(ok=True)
        response.json.return_value = {"answers": [
            {"type": "predicate", "name": "format_mass", "probability": 0.7}
        ]}
        post.return_value = response
        with self.assertRaisesRegex(ValueError, "missing criterion"):
            classify_decisions(self.event, "secret", self.config)

    @patch("src.decisions_classify.requests.post")
    def test_refusal_rejected(self, post):
        response = Mock(ok=True)
        response.json.return_value = {"answers": [
            {"type": "refusal", "name": "format_mass"},
            {"type": "predicate", "name": "topic_faith", "probability": 0.1},
        ]}
        post.return_value = response
        with self.assertRaisesRegex(ValueError, "type mismatch for format_mass"):
            classify_decisions(self.event, "secret", self.config)

    @patch("src.decisions_classify.requests.post")
    def test_non_finite_score_rejected(self, post):
        response = Mock(ok=True)
        response.json.return_value = {"answers": [
            {"type": "predicate", "name": "format_mass", "probability": float("nan")},
            {"type": "predicate", "name": "topic_faith", "probability": 0.1},
        ]}
        post.return_value = response
        with self.assertRaisesRegex(ValueError, "invalid probability"):
            classify_decisions(self.event, "secret", self.config)


    @patch("src.decisions_classify.requests.post")
    def test_choice_keeps_all_probabilities(self, post):
        self.config["criteria"] = [{
            "id": "main_format", "type": "choice", "category": "Format",
            "label": "Hauptformat", "description": "Welches Hauptformat?",
            "threshold": 0.65, "weight": 0,
            "options": [
                {"value": "workshop", "description": "Praktische Arbeit"},
                {"value": "vortrag", "description": "Zuhören"},
                {"value": "andere", "description": "Sonstiges"},
            ],
        }]
        response = Mock(ok=True)
        response.json.return_value = {"answers": [{
            "type": "choice", "name": "main_format", "choice": "workshop",
            "confidence": 0.84, "probabilities": [
                {"value": "workshop", "probability": 0.72},
                {"value": "vortrag", "probability": 0.18},
                {"value": "andere", "probability": 0.10},
            ],
        }], "usage": {}}
        post.return_value = response
        result = classify_decisions(self.event, "secret", self.config)
        score = result["criteria_scores"][0]
        self.assertEqual(score["type"], "choice")
        self.assertEqual(score["score"], 0.72)
        self.assertFalse(score["matched"])
        self.assertEqual(len(score["answer"]["probabilities"]), 3)
        self.assertEqual(score["answer"]["probabilities"][1]["probability"], 0.18)
        self.assertEqual(post.call_args.kwargs["json"]["questions"][0]["choices"][0]["value"], "workshop")

    @patch("src.decisions_classify.requests.post")
    def test_choice_missing_distribution_fails(self, post):
        self.config["criteria"] = [{
            "id": "main_format", "type": "choice", "category": "Format",
            "label": "Hauptformat", "description": "Welches Hauptformat?",
            "threshold": 0.65, "weight": 0,
            "options": [{"value": "workshop"}, {"value": "vortrag"}],
        }]
        response = Mock(ok=True)
        response.json.return_value = {"answers": [{
            "type": "choice", "name": "main_format", "choice": "workshop",
            "confidence": 0.6, "probabilities": [{"value": "workshop", "probability": 0.6}],
        }]}
        post.return_value = response
        with self.assertRaisesRegex(ValueError, "all option probabilities"):
            classify_decisions(self.event, "secret", self.config)

    @patch("src.decisions_classify.requests.post")
    def test_score_keeps_all_levels(self, post):
        self.config["criteria"] = [{
            "id": "faith_strength", "type": "score", "category": "Thema",
            "label": "Glaubensbezug", "description": "Wie stark?",
            "threshold": 0.65, "weight": 0,
            "options": [{"label": "kein"}, {"label": "etwas"}, {"label": "stark"}],
        }]
        response = Mock(ok=True)
        response.json.return_value = {"answers": [{
            "type": "score", "name": "faith_strength", "score": 1.4,
            "confidence": 0.72, "probabilities": [
                {"value": 0, "label": "kein", "probability": 0.1},
                {"value": 1, "label": "etwas", "probability": 0.4},
                {"value": 2, "label": "stark", "probability": 0.5},
            ],
        }]}
        post.return_value = response
        result = classify_decisions(self.event, "secret", self.config)
        score = result["criteria_scores"][0]
        self.assertEqual(score["type"], "score")
        self.assertEqual(score["score"], 0.7)
        self.assertFalse(score["matched"])
        self.assertEqual(len(score["answer"]["probabilities"]), 3)

    def test_missing_configuration_rejected(self):
        with self.assertRaisesRegex(ValueError, "requires enabled Criteria"):
            classify_decisions(self.event, "secret", {"criteria": []})
