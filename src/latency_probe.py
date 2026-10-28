"""Read-only paired latency probe for a pinned Gemini model."""
import argparse
import json
import os
import statistics
import time
from pathlib import Path
import requests
from .scrape import fetch_events
from .classify import DEFAULT_PROMPT
from .config import settings

MODEL = "gemini-3.5-flash-lite"
URL = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent"

def probe(api_key, label, payload, index):
    t0 = time.perf_counter()
    report = {"case": label, "round": index, "model": MODEL}
    try:
        with requests.post(URL, headers={"x-goog-api-key": api_key}, json=payload,
                           timeout=(10, 65), stream=True) as response:
            # requests.elapsed measures time until response headers: approximate TTFB.
            report["ttfb_seconds"] = round(response.elapsed.total_seconds(), 3)
            report["http_status"] = response.status_code
            body = response.content
            report["response_bytes"] = len(body)
            report["duration_seconds"] = round(time.perf_counter()-t0, 3)
            if response.ok:
                data = response.json()
                usage = data.get("usageMetadata", {})
                report["input_tokens"] = usage.get("promptTokenCount", 0)
                report["output_tokens"] = usage.get("candidatesTokenCount", 0)
                report["thinking_tokens"] = usage.get("thoughtsTokenCount", 0)
                report["status"] = "ok"
            else:
                report["status"] = "http_error"
    except requests.RequestException as exc:
        report.update({"status": type(exc).__name__, "duration_seconds": round(time.perf_counter()-t0,3)})
    print("[latency] " + json.dumps(report, ensure_ascii=False), flush=True)
    return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()
    _, config = settings(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],
                         os.environ.get("GOOGLE_SHEET_ID", "1HRyxPjLz2-WUEelplO1YAaO7gCYDyU_77DgUqEtGQ1w"))
    events = fetch_events(1)
    event = events[0]
    tags = config["tags"]
    synonyms = {k:v for k,v in config["tag_synonyms"].items() if k in tags}
    instruction = ((config["gemini_prompt"] or DEFAULT_PROMPT) + "\n\n" +
                   "Zulässige Standard-Tags (nur diese Werte): " + ", ".join(tags) +
                   "\nMaximal " + str(config["max_additional_tags"] if config["additional_tags_enabled"] else 0) +
                   " zusätzliche freie deutsche Suchbegriffe." +
                   "\nSynonyme der Standard-Tags: " + json.dumps(synonyms, ensure_ascii=False) +
                   "\nIst ein Standard-Tag ausgewählt, gib seine Synonyme NICHT als zusätzliche Tags zurück." +
                   "\nDie Antwort muss ein JSON-Objekt mit standard_tags, additional_tags, reason sein.")
    common = {"thinkingConfig": {"thinkingLevel": "minimal"}, "maxOutputTokens": 512}
    minimal = {"contents":[{"parts":[{"text":"Antworte ausschließlich mit OK."}]}],
               "generationConfig":dict(common)}
    full = {"systemInstruction":{"parts":[{"text": instruction}]},
            "contents":[{"parts":[{"text": json.dumps(event, ensure_ascii=False)}]}],
            "generationConfig":{**common,"responseMimeType":"application/json",
                                "temperature":float(config["gemini_temperature"])}}
    results=[]
    for i in range(1, max(1,min(5,args.rounds))+1):
        # Alternate first case to reduce timing/order bias.
        cases = [("minimal",minimal),("gocath",full)] if i%2 else [("gocath",full),("minimal",minimal)]
        for label,payload in cases:
            results.append(probe(os.environ["GOCATH_GEMINI_CLASSIFIER_KEY"],label,payload,i))
    out=Path("output");out.mkdir(exist_ok=True)
    (out/"latency-probe.json").write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding="utf-8")
    for label in ("minimal","gocath"):
        rs=[r for r in results if r["case"]==label]
        good=[r["duration_seconds"] for r in rs if r["status"]=="ok"]
        print("[latency-summary] case={} successful={}/{} median_seconds={}".format(
            label,len(good),len(rs),round(statistics.median(good),3) if good else "n/a"),flush=True)

if __name__=="__main__":
    main()
