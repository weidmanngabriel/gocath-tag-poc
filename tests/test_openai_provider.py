import unittest
from unittest.mock import Mock, patch
from src.openai_classify import classify_openai, MODEL

class OpenAIProviderTests(unittest.TestCase):
    def config(self):
        return {"openai_reasoning_effort":"medium","max_additional_tags":8,
                "additional_tags_enabled":True,"gemini_prompt":"Classify",
                "tags":["Anbetung"],"tag_synonyms":{}}

    @patch("src.openai_classify.requests.post")
    def test_valid_response_and_reasoning_usage(self, post):
        response=Mock(ok=True)
        response.json.return_value={"status":"completed","output":[{"content":[{"type":"output_text","text":'{"standard_tags":["Anbetung"],"additional_tags":[],"reason":"Belegt"}'}]}],
            "usage":{"input_tokens":100,"output_tokens":30,"total_tokens":130,
                "input_tokens_details":{"cached_tokens":25},
                "output_tokens_details":{"reasoning_tokens":10}}}
        post.return_value=response
        usage={}
        result=classify_openai({"title":"Anbetung"},"dummy",self.config(),usage_sink=usage)
        self.assertEqual(result["standard_tags"],["Anbetung"])
        self.assertEqual(usage["thinking_tokens"],10)
        self.assertEqual(usage["cached_tokens"],25)
        self.assertEqual(post.call_args.kwargs["json"]["model"],MODEL)
        self.assertEqual(post.call_args.kwargs["json"]["reasoning"]["effort"],"medium")

    def test_invalid_effort(self):
        config=self.config()
        config["openai_reasoning_effort"]="invalid"
        with self.assertRaises(ValueError):
            classify_openai({"title":"Test"},"dummy",config)
