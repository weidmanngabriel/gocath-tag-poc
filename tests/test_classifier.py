import unittest
from unittest.mock import Mock, patch
from src.classify import GeminiAPIError, classify, build_instruction, OUTPUT_CONTRACT

class ClassifierTests(unittest.TestCase):
    @patch("src.classify.requests.post")
    def test_safe_http_error(self, post):
        post.return_value = Mock(status_code=403, ok=False)
        with self.assertRaisesRegex(GeminiAPIError, "HTTP 403"):
            classify({"title": "Test"}, "private-secret", "gemini-2.5-flash-lite")

    @patch("src.classify.requests.post")
    def test_valid_response(self, post):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {"candidates":[{"content":{"parts":[{"text":'{"standard_tags":["Gebet"],"additional_tags":[],"reason":"Titel"}'}]}}]}
        post.return_value = response
        result = classify({"title": "Gebet"}, "private-secret", "gemini-2.5-flash-lite")
        self.assertEqual(result["standard_tags"], ["Gebet"])

    def test_technical_contract_precedes_editable_prompt(self):
        result = build_instruction("Custom rules.", ["Anbetung"], 8, {})
        self.assertTrue(result.startswith(OUTPUT_CONTRACT))
        self.assertLess(result.index("TECHNISCHES AUSGABEFORMAT"), result.index("Custom rules."))
        self.assertIn("Array von Strings", result)
        self.assertIn("Zulässige Standard-Tags", result)
