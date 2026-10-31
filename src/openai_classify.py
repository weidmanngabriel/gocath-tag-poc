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
    criteria = config.get("criteria", [])
    if criteria:
        instructions += ("\nBewerte zusätzlich JEDES Kriterium anhand der Veranstaltungsdaten. "
                         "score ist ein Schätzwert zwischen 0 und 1. "
                         "Bei fehlenden Belegen niedrige Werte verwenden; nicht erfinden. "
                         "Zielgruppen bewerten nach Eignung, spezielle Geschlechtergruppen "
                         "nur bei ausdrücklicher Ausrichtung. evidence ist eine kurze "
                         "Textstelle oder leer. Gib genau eine Bewertung pro ID zurück.\n"
                         + json.dumps([{"id": c["id"], "description": c["description"]} for c in criteria], ensure_ascii=False))
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
                    "reason": {"type": "string"},
                    "criteria_scores": {"type": "array", "items": {"type": "object",
                        "additionalProperties": False,
                        "properties": {"id": {"type": "string"}, "score": {"type": "number"}, "evidence": {"type": "string"}},
                        "required": ["id", "score", "evidence"]}}
                },
                "required": ["standard_tags", "additional_tags", "reason", "criteria_scores"]
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
    parsed = json.loads("".join(contents))
    tags = clean(parsed, config["tags"])
    configured = {c["id"]: c for c in criteria}
    scores = {}
    for item in parsed.get("criteria_scores", []):
        if not isinstance(item, dict) or item.get("id") not in configured:
            continue
        try:
            score = max(0.0, min(1.0, float(item["score"])))
        except (TypeError, ValueError, KeyError):
            continue
        scores[item["id"]] = {"score": round(score, 4), "evidence": str(item.get("evidence", ""))[:240]}
    tags["criteria_scores"] = [dict(id=c["id"], category=c["category"], label=c["label"],
        score=scores.get(c["id"], {}).get("score", 0.0),
        evidence=scores.get(c["id"], {}).get("evidence", ""),
        matched=scores.get(c["id"], {}).get("score", 0.0) >= c["threshold"])
        for c in criteria]
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
