import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.groq_compare import invoke

class GroqDiagnosticTests(unittest.TestCase):
    def test_invalid_response_generates_artifact_without_credentials(self):
        class Response:
            status_code = 200
            ok = True
            headers = {}
            def json(self):
                return {"usage": {}, "choices": [{"message": {"content": "INVALID RESPONSE"}}]}
        event={"title":"Test event","description":"Public event","url":"https://example.org"}
        config={"tags":["Anbetung"],"max_additional_tags":8,"additional_tags_enabled":True,"gemini_prompt":"Classify.","gemini_temperature":0.1,"tag_synonyms":{}}
        with tempfile.TemporaryDirectory() as temp:
            with patch("src.groq_compare.Path", side_effect=lambda path: Path(temp) / path), patch("src.groq_compare.requests.post", return_value=Response()), contextlib.redirect_stdout(io.StringIO()):
                result=invoke("groq", event, config, {"groq":"secret-value"})
            artifact=json.loads((Path(temp)/"output/failed-groq-request-response.json").read_text())
        self.assertEqual(result["status"],"JSONDecodeError")
        self.assertEqual(artifact["response"]["choices"][0]["message"]["content"],"INVALID RESPONSE")
        self.assertEqual(artifact["request"]["body"]["model"],"openai/gpt-oss-20b")
        self.assertNotIn("secret-value",json.dumps(artifact))
