"""Regression tests for append-only criterion history."""
import unittest
from unittest.mock import Mock
from src.config import save_classification_details


class ClassificationDetailsTests(unittest.TestCase):
    def test_stores_all_scores_even_below_threshold(self):
        worksheet = Mock()
        doc = Mock()
        doc.worksheet.return_value = worksheet
        results = [{
            "event": {"url": "https://example.test/foo", "title": "Fußballturnier"},
            "criteria_scores": [
                {"id": "topic_liturgy", "category": "Thema", "label": "Liturgie",
                 "score": 0.01, "matched": False, "evidence": ""},
                {"id": "context_catholic", "category": "Kontext", "label": "Katholischer Veranstalter",
                 "score": 0.12, "matched": False, "evidence": ""},
            ],
            "relevance_score": 0.18, "relevance_status": "likely_not_relevant",
        }]
        save_classification_details(doc, "26", results, "test-model", "2026-10-31")
        rows = worksheet.append_rows.call_args.args[0]
        self.assertEqual(len(rows), 2)
        self.assertEqual([r[8] for r in rows], [0.01, 0.12])
        self.assertEqual([r[9] for r in rows], ["false", "false"])
        self.assertEqual({r[11] for r in rows}, {"likely_not_relevant"})
        worksheet.append_rows.assert_called_once()

    def test_empty_results_do_not_append(self):
        doc = Mock()
        save_classification_details(doc, "27", [], "model", "date")
        doc.worksheet.assert_not_called()
