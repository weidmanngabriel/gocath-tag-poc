"""Read-only A/B comparison of two fixed models on identical public events."""
import argparse
import csv
import json
import os
import statistics
import time
from pathlib import Path

import requests
from .classify import DEFAULT_PROMPT, clean, filter_duplicate_synonyms
from .config import settings
from .scrape import fetch_events

MODELS = (("gemini", "gemini-3.5-flash-lite"), ("gemma", "gemma-4-26b-a4b-it"))
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"

def instruction(config):
    tags = config["tags"]
    count = config["max_additional_tags"] if config["additional_tags_enabled"] else 0
    synonyms = {tag: config["tag_synonyms"].get(tag, []) for tag in tags if config["tag_synonyms"].get(tag)}
    return ("\n\n".join([config["gemini_prompt"] or DEFAULT_PROMPT,
        "Zulässige Standard-Tags (nur diese Werte): " + ", ".join(tags),
        "Maximal {} zusätzliche freie deutsche Suchbegriffe.".format(count),
        "Synonyme der Standard-Tags: " + json.dumps(synonyms, ensure_ascii=False),
        "Ist ein Standard-Tag ausgewählt, gib seine Synonyme NICHT als zusätzliche Tags zurück.",
        "Antworte ausschließlich als JSON-Objekt mit standard_tags, additional_tags, reason."]))

def request_model(key, model, event, config):
    payload = {"systemInstruction": {"parts": [{"text": instruction(config)}]},
               "contents": [{"parts": [{"text": json.dumps(event, ensure_ascii=False)}]}],
               "generationConfig": {"responseMimeType": "application/json",
                                    "thinkingConfig": {"thinkingLevel": "minimal"}}}
    if model.startswith("gemini-"):
        # Align with the production model's configurable temperature.
        payload["generationConfig"]["temperature"] = float(config["gemini_temperature"])
    started = time.perf_counter()
    result = {"model": model, "seconds": None, "status": "error",
              "http_status": None, "input_tokens": 0, "output_tokens": 0,
              "thinking_tokens": 0, "standard_tags": [], "additional_tags": [], "reason": ""}
    try:
        response = requests.post(ENDPOINT.format(model), headers={"x-goog-api-key": key},
                                 json=payload, timeout=(10, 65))
        result["http_status"] = response.status_code
        if not response.ok:
            result["status"] = "http_error"
            return result
        body = response.json()
        usage = body.get("usageMetadata", {})
        for field, keyname in (("input_tokens", "promptTokenCount"),
                               ("output_tokens", "candidatesTokenCount"),
                               ("thinking_tokens", "thoughtsTokenCount")):
            result[field] = int(usage.get(keyname, 0))
        parts = body["candidates"][0]["content"]["parts"]
        answer = "".join(part.get("text", "") for part in parts)
        data = clean(json.loads(answer), config["tags"])
        data["additional_tags"] = data["additional_tags"][:(config["max_additional_tags"] if config["additional_tags_enabled"] else 0)]
        data = filter_duplicate_synonyms(data, config["tag_synonyms"])
        result.update(data)
        result["status"] = "ok"
    except (requests.RequestException, KeyError, ValueError, TypeError, IndexError) as exc:
        result["status"] = type(exc).__name__
    finally:
        result["seconds"] = round(time.perf_counter() - started, 3)
        print("[benchmark] model={} status={} http={} seconds={}".format(
            model, result["status"], result["http_status"], result["seconds"]), flush=True)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    _, config = settings(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],
                         os.environ.get("GOOGLE_SHEET_ID", "1HRyxPjLz2-WUEelplO1YAaO7gCYDyU_77DgUqEtGQ1w"))
    events = fetch_events(max(1, min(10, args.limit)))
    output = Path("output")
    output.mkdir(exist_ok=True)
    rows = []
    for idx, event in enumerate(events, 1):
        for provider, model in MODELS:
            r = request_model(os.environ["GOCATH_GEMINI_CLASSIFIER_KEY"], model, event, config)
            r["event_index"] = idx
            r["event_url"] = event["url"]
            r["provider"] = provider
            rows.append(r)
    (output / "ab-results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    cols = ["event_index","provider","model","status","http_status","seconds","input_tokens",
            "output_tokens","thinking_tokens","standard_tags","additional_tags","reason"]
    with (output / "ab-results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "standard_tags": ", ".join(row["standard_tags"]),
                             "additional_tags": ", ".join(row["additional_tags"])})
    for provider, model in MODELS:
        sample = [r for r in rows if r["model"] == model]
        ok = [r for r in sample if r["status"] == "ok"]
        print("[summary] {} completed={}/{} avg_seconds={} median_seconds={} total_seconds={}".format(
            model, len(ok), len(sample), round(statistics.mean(r["seconds"] for r in ok), 3) if ok else "n/a",
            round(statistics.median(r["seconds"] for r in ok), 3) if ok else "n/a",
            round(sum(r["seconds"] for r in sample), 3)), flush=True)
    pairs = [(rows[i], rows[i+1]) for i in range(0, len(rows), 2)]
    for a, b in pairs:
        if a["status"] == b["status"] == "ok":
            overlap = len(set(a["standard_tags"]) & set(b["standard_tags"]))
            print("[compare] event={} exact_match={} overlap={}".format(
                a["event_index"], set(a["standard_tags"]) == set(b["standard_tags"]), overlap), flush=True)

if __name__ == "__main__":
    main()
