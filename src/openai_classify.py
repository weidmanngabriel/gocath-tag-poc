"""OpenAI GPT-6 Luna classifier using the Responses API."""
import json
import requests
from .classify import build_instruction, clean, filter_duplicate_synonyms

MODEL = "gpt-6-luna"
EFFORTS = ("none", "low", "medium", "high")

def classify_openai(event, api_key, config, usage_sink=None):
    effort = config["openai_reasoning_effort"]
    if effort not in EFFORTS:
        raise ValueError("Invalid OpenAI reasoning effort")
    count = config["max_additional_tags"] if config["additional_tags_enabled"] else 0
    instructions = build_instruction(config["gemini_prompt"], config["tags"], count, config["tag_synonyms"])
    payload = {
        "model": MODEL,
        "instructions": instructions,
        "input": [{"role": "user", "content": json.dumps(event, ensure_ascii=False)}],
        "reasoning": {"effort": effort},
        "text": {"format": {"type": "json_schema", "name": "gocath_tags",
            "strict": True, "schema": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "standard_tags": {"type": "array", "items": {"type": "string"}},
                    "additional_tags": {"type": "array", "items": {"type": "string"}},
                    "reason": {"type": "string"}
                },
                "required": ["standard_tags", "additional_tags", "reason"]
            }}}
    }
    response = requests.post("https://api.openai.com/v1/responses",
        headers={"Authorization": "Bearer " + api_key}, json=payload, timeout=(10,90))
    if not response.ok:
        raise RuntimeError("OpenAI Responses API HTTP " + str(response.status_code))
    body = response.json()
    if body.get("status") != "completed":
        raise RuntimeError("OpenAI response not completed: " + str(body.get("status")))
    contents = [part.get("text", "") for item in body.get("output", [])
        for part in item.get("content", []) if part.get("type") == "output_text"]
    if not contents:
        raise RuntimeError("OpenAI response contains no output_text")
    tags = clean(json.loads("".join(contents)), config["tags"])
    tags["additional_tags"] = tags["additional_tags"][:count]
    usage = body.get("usage") or {}
    output_details = usage.get("output_tokens_details") or {}
    input_details = usage.get("input_tokens_details") or {}
    if usage_sink is not None:
        usage_sink.update({
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "thinking_tokens": output_details.get("reasoning_tokens", 0),
            "cached_tokens": input_details.get("cached_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        })
    return filter_duplicate_synonyms(tags, config["tag_synonyms"])
