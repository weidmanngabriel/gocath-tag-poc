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
        with self.assertRaisesRegex(ValueError, "unexpected name or type"):
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

    def test_missing_configuration_rejected(self):
        with self.assertRaisesRegex(ValueError, "requires enabled Criteria"):
            classify_decisions(self.event, "secret", {"criteria": []})
