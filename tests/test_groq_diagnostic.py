import contextlib
import io
import unittest
from unittest.mock import patch
from src.groq_compare import invoke

class GroqDiagnosticTests(unittest.TestCase):
    def test_invalid_answer_is_logged_without_event_description(self):
        class Response:
            status_code = 200
            ok = True
            headers = {}
            def json(self):
                return {"usage": {}, "choices": [{"message": {"content": 'INVALID EVENT DESCRIPTION: Private event details'}}]}
        event = {"title": "Private event", "description": "Private event details", "url": "https://example.org"}
        config = {"tags": ["Anbetung"], "max_additional_tags": 8,
                  "additional_tags_enabled": True, "gemini_prompt": "Classify.",
                  "gemini_temperature": 0.1, "tag_synonyms": {}}
        output = io.StringIO()
        with patch("src.groq_compare.requests.post", return_value=Response()), contextlib.redirect_stdout(output):
            result = invoke("groq", event, config, {"groq": "secret-value"})
        self.assertEqual(result["status"], "JSONDecodeError")
        self.assertIn("[groq-invalid-output]", output.getvalue())
        self.assertIn("[REDACTED]", output.getvalue())
        self.assertNotIn("Private event details", output.getvalue())
        self.assertNotIn("secret-value", output.getvalue())
