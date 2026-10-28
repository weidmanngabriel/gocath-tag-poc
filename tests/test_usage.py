import unittest
from unittest.mock import Mock, patch
from src.classify import classify

class UsageTests(unittest.TestCase):
    @patch("src.classify.requests.post")
    def test_usage_metadata_saved(self, post):
        response = Mock(ok=True, status_code=200)
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"standard_tags":["Gebet"],"additional_tags":[],"reason":"Test"}'}]}}],
            "usageMetadata": {
                "promptTokenCount": 230,
                "candidatesTokenCount": 35,
                "thoughtsTokenCount": 12,
                "totalTokenCount": 277,
            },
        }
        post.return_value = response
        usage = {}
        classified = classify({"title": "Gebet"}, "fake-key", "model", ["Gebet"], usage_sink=usage)
        self.assertEqual(classified["standard_tags"], ["Gebet"])
        self.assertEqual(usage["input_tokens"], 230)
        self.assertEqual(usage["thinking_tokens"], 12)
        self.assertEqual(usage["total_tokens"], 277)
