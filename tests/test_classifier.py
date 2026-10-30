import unittest
from unittest.mock import Mock, patch
from src.classify import GeminiAPIError, classify, clean

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

    def test_single_standard_tag_string_is_normalized(self):
        result = clean({"standard_tags": "Anbetung", "additional_tags": ["Nachtgebet"], "reason": "Belegt"}, ["Anbetung", "Gebet"])
        self.assertEqual(result["standard_tags"], ["Anbetung"])
        self.assertEqual(result["additional_tags"], ["Nachtgebet"])

    def test_unknown_scalar_standard_tag_is_discarded(self):
        result = clean({"standard_tags": "Nicht vorhanden", "additional_tags": [], "reason": ""}, ["Anbetung"])
        self.assertEqual(result["standard_tags"], [])
