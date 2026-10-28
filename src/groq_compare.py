"""Read-only comparison of Gemini and Groq on identical GoCath events."""
import argparse
import json
import os
import statistics
import time
from pathlib import Path
import requests
from .scrape import fetch_events
from .config import settings
from .classify import DEFAULT_PROMPT, clean, filter_duplicate_synonyms

GEMINI_MODEL = "gemini-3.5-flash-lite"
GROQ_MODEL = "openai/gpt-oss-20b"

def instruction(config):
    tags = config["tags"]
    count = config["max_additional_tags"] if config["additional_tags_enabled"] else 0
    return ((config["gemini_prompt"] or DEFAULT_PROMPT) + "\n\n"
        + "Zulässige Standard-Tags (nur diese Werte): " + ", ".join(tags)
        + "\nMaximal " + str(count) + " zusätzliche freie deutsche Suchbegriffe."
        + "\nSynonyme der Standard-Tags: " + json.dumps(config["tag_synonyms"], ensure_ascii=False)
        + "\nIst ein Standard-Tag ausgewählt, gib seine Synonyme NICHT als zusätzliche Tags zurück."
        + "\nDie Antwort muss ein JSON-Objekt mit standard_tags, additional_tags, reason sein.")

def invoke(provider, event, config, secrets):
    system = instruction(config)
    event_text = json.dumps(event, ensure_ascii=False)
    if provider == "gemini":
        url = "https://generativelanguage.googleapis.com/v1beta/models/" + GEMINI_MODEL + ":generateContent"
        headers = {"x-goog-api-key": secrets["gemini"]}
        payload = {"systemInstruction": {"parts": [{"text": system}]},
                   "contents": [{"parts": [{"text": event_text}]}],
                   "generationConfig": {"responseMimeType": "application/json",
                     "temperature": float(config["gemini_temperature"]),
                     "thinkingConfig": {"thinkingLevel": "minimal"}}}
    else:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": "Bearer " + secrets["groq"]}
        payload = {"model": GROQ_MODEL, "messages": [{"role":"system","content":system},
                   {"role":"user","content":event_text}],
                   "response_format":{"type":"json_object"},
                   "reasoning_effort":"low",
                   "temperature":float(config["gemini_temperature"])}
    started = time.perf_counter()
    out = {"provider":provider,"model":GEMINI_MODEL if provider=="gemini" else GROQ_MODEL,
           "status":"error","http_status":None,"retry_after_seconds":None,"seconds":None,
           "input_tokens":0,"output_tokens":0,"standard_tags":[],"additional_tags":[],"reason":""}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=(10,65))
        out["http_status"] = response.status_code
        if response.status_code == 429:
            try:
                out["retry_after_seconds"] = max(0, min(120, float(response.headers.get("Retry-After", ""))))
            except (ValueError, TypeError):
                pass
        if not response.ok:
            out["status"] = "http_error"
        else:
            body = response.json()
            if provider=="gemini":
                usage=body.get("usageMetadata",{})
                out["input_tokens"]=usage.get("promptTokenCount",0)
                out["output_tokens"]=usage.get("candidatesTokenCount",0)
                answer="".join(p.get("text","") for p in body["candidates"][0]["content"]["parts"])
            else:
                usage=body.get("usage",{})
                out["input_tokens"]=usage.get("prompt_tokens",0)
                out["output_tokens"]=usage.get("completion_tokens",0)
                answer=body["choices"][0]["message"]["content"]
            parsed=clean(json.loads(answer),config["tags"])
            parsed["additional_tags"]=parsed["additional_tags"][:config["max_additional_tags"] if config["additional_tags_enabled"] else 0]
            out.update(filter_duplicate_synonyms(parsed,config["tag_synonyms"]))
            out["status"]="ok"
    except (requests.RequestException,KeyError,IndexError,ValueError,TypeError) as exc:
        out["status"]=type(exc).__name__
    finally:
        out["seconds"]=round(time.perf_counter()-started,3)
        print("[groq-compare] provider={} status={} http={} seconds={}".format(provider,out["status"],out["http_status"],out["seconds"]),flush=True)
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--limit",type=int,default=10)
    args=parser.parse_args()
    _,config=settings(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],os.environ.get("GOOGLE_SHEET_ID","1HRyxPjLz2-WUEelplO1YAaO7gCYDyU_77DgUqEtGQ1w"))
    events=fetch_events(max(1,min(args.limit,10)))
    secrets={"groq":os.environ["GROQ_API_KEY"],"gemini":os.environ["GOCATH_GEMINI_CLASSIFIER_KEY"]}
    results=[]
    for i,event in enumerate(events,1):
        for provider in (("gemini","groq") if i%2 else ("groq","gemini")):
            row=invoke(provider,event,config,secrets)
            row["event_index"]=i
            results.append(row)
    Path("output").mkdir(exist_ok=True)
    Path("output/groq-comparison.json").write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding="utf-8")
    for provider in ("gemini","groq"):
        rows=[r for r in results if r["provider"]==provider]
        ok=[r for r in rows if r["status"]=="ok"]
        durations=[r["seconds"] for r in ok]
        print("[groq-summary] provider={} success={}/{} median={} total={}".format(provider,len(ok),len(rows),round(statistics.median(durations),3) if durations else "n/a",round(sum(r["seconds"] for r in rows),3)),flush=True)
    for i in range(1,len(events)+1):
        pair={r["provider"]:r for r in results if r["event_index"]==i}
        if all(pair[p]["status"]=="ok" for p in ("gemini","groq")):
            print("[groq-tags] event={} exact_match={} intersection={}".format(i,
                  set(pair["gemini"]["standard_tags"])==set(pair["groq"]["standard_tags"]),
                  len(set(pair["gemini"]["standard_tags"])&set(pair["groq"]["standard_tags"]))),flush=True)

if __name__=="__main__":
    main()
