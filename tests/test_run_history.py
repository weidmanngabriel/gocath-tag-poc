import unittest
from unittest.mock import Mock
from src.config import next_run_id, save_history

class RunHistoryTests(unittest.TestCase):
    def test_sequential_ids(self):
        doc = Mock()
        doc.worksheet.return_value.get_all_values.return_value = [
            ["run_id", "started_at"], ["1", "a"], ["3", "b"], ["old-format", "c"]
        ]
        self.assertEqual(next_run_id(doc), "4")

    def test_history_preserves_multiple_runs(self):
        doc = Mock()
        records = [{
            "event": {"url": "https://gocath.org/de/event/test", "title": "Test"},
            "tags": {"standard_tags": ["Gebet"], "additional_tags": ["Stille"], "reason": "Beschreibung"}
        }]
        save_history(doc, "2", records, "gemini-flash-lite-latest", "Prompt A", "2026-10-28T10:00:00Z")
        args, kwargs = doc.worksheet.return_value.append_rows.call_args
        self.assertEqual(args[0][0][0], "2")
        self.assertEqual(args[0][0][7], "Prompt A")
