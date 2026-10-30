import unittest
from src.main import retryable_groq_response


class GroqRetryTests(unittest.TestCase):
    def test_malformed_success_response_is_retryable(self):
        for status in ("ValueError", "KeyError", "IndexError", "TypeError"):
            with self.subTest(status=status):
                self.assertTrue(retryable_groq_response({"http_status": 200, "status": status}))

    def test_transient_server_errors_are_retryable(self):
        for code in (429, 500, 502, 503, 504):
            self.assertTrue(retryable_groq_response({"http_status": code, "status": "http_error"}))

    def test_permanent_and_unexpected_errors_are_not_retryable(self):
        for code, status in ((400, "http_error"), (401, "http_error"), (403, "http_error"), (200, "ok"), (200, "http_error")):
            with self.subTest(code=code, status=status):
                self.assertFalse(retryable_groq_response({"http_status": code, "status": status}))
