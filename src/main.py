"""Manual GoCath tagging based on Google Sheet settings."""
import argparse
import json
import os
import time
from pathlib import Path
from datetime import datetime, timezone
from .scrape import fetch_events
from .regnum_scrape import fetch_events as fetch_regnum_events
from .classify import classify, choose_model
from .groq_compare import invoke as invoke_groq
from .openai_classify import classify_openai, MODEL as OPENAI_MODEL
from .config import settings, run_count, log_run, next_run_id, save_history
from .sheets import publish

SHEET_ID = "1HRyxPjLz2-WUEelplO1YAaO7gCYDyU_77DgUqEtGQ1w"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    provider_key = None
    credentials = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", SHEET_ID)
    overall_t0 = time.perf_counter()
    t0 = time.perf_counter()
    doc, config = settings(credentials, sheet_id)
    print(f'[timing] config_and_auth={time.perf_counter()-t0:.3f}s',flush=True)
    limit = config["max_events_per_run"]
    if args.limit is not None:
        limit = min(limit, max(1, args.limit))
    limit = min(limit, max(0, config["monthly_limit"] - run_count(doc)))
    if not limit:
        print("Monatslimit erreicht; keine Klassifizierung.")
        return
    start = datetime.now(timezone.utc).isoformat()
    run_id = next_run_id(doc)
    provider = config["classifier_provider"]
    if provider not in ("groq", "gemini", "openai"):
        raise ValueError("Unknown classifier_provider; expected groq, gemini or openai")
    t0 = time.perf_counter()
    if provider == "groq":
        provider_key = os.environ["GROQ_API_KEY"]
        model = "openai/gpt-oss-20b"
    elif provider == "openai":
        provider_key = os.environ["GOCATH_OPENAI"]
        model = OPENAI_MODEL
    else:
        provider_key = os.environ["GOCATH_GEMINI_CLASSIFIER_KEY"]
        model = choose_model(provider_key, config["gemini_model"] or os.environ.get("GEMINI_MODEL"))
    print(f'[timing] model_selection={time.perf_counter()-t0:.3f}s',flush=True)
    t0 = time.perf_counter()
    event_source = config['event_source']
    if event_source not in ('gocath', 'regnum_christi'):
        raise ValueError('Unknown event_source; expected gocath or regnum_christi')
    events = fetch_events(limit) if event_source == 'gocath' else fetch_regnum_events(limit)
    print(f'[source] selected={event_source}',flush=True)
    print(f'[timing] fetch_events={time.perf_counter()-t0:.3f}s count={len(events)}',flush=True)
    if config["changed_only"]:
        previous = doc.sheet1.get_all_values()
        descriptions = {r[0]: r[2] for r in previous[1:] if len(r) > 6 and r[6] == "ok"}
        events = [event for event in events if descriptions.get(event["url"]) != event["description"]]
    print(f"Zu klassifizieren: {len(events)}, Modell: {model}", flush=True)
    results = []
    usage_total = {"input_tokens":0,"output_tokens":0,"thinking_tokens":0,"total_tokens":0}
    def price(tokens, per_million):
        return tokens * float(per_million) / 1_000_000 if per_million else None
    last_groq_request = None
    try:
        for idx,event in enumerate(events,1):
            t0 = time.perf_counter()
            usage = {}
            if provider == "groq":
                for groq_attempt in range(4):
                    if last_groq_request is not None:
                        pause = max(0, 15 - (time.monotonic() - last_groq_request))
                        if pause:
                            print(f"[groq-pacing] wait={pause:.1f}s to respect 8K TPM free-tier budget", flush=True)
                            time.sleep(pause)
                    last_groq_request = time.monotonic()
                    response = invoke_groq("groq", event, config, {"groq": provider_key})
                    if response["status"] == "ok":
                        break
                    if response["http_status"] not in (429, 500, 502, 503, 504) or groq_attempt == 3:
                        raise RuntimeError("Groq classification failed: " + response["status"] + "; HTTP " + str(response["http_status"]))
                    delay = max(10 * (groq_attempt + 1), response.get("retry_after_seconds") or 0)
                    print(f"[groq-retry] http={response['http_status']} attempt={groq_attempt+1} wait={delay}s", flush=True)
                    time.sleep(delay)
                tags = {k: response[k] for k in ("standard_tags", "additional_tags", "reason")}
                usage.update({"input_tokens": response["input_tokens"], "output_tokens": response["output_tokens"], "thinking_tokens": 0,
                              "total_tokens": response["input_tokens"] + response["output_tokens"]})
            elif provider == "openai":
                tags = classify_openai(event, provider_key, config, usage_sink=usage)
            else:
                tags = classify(event, provider_key, model, config["tags"], config["additional_tags_enabled"],
                                config["gemini_prompt"], config["gemini_temperature"], config["max_additional_tags"], usage_sink=usage, synonyms=config["tag_synonyms"])
            print(f'[timing] classify_event={idx}/{len(events)} duration={time.perf_counter()-t0:.3f}s',flush=True)
            for name in usage_total:
                usage_total[name] += usage.get(name, 0)
            input_cost = price(usage.get("input_tokens",0), config["cost_input_per_million_usd"])
            output_cost = price(usage.get("output_tokens",0)+(usage.get("thinking_tokens",0) if provider == "gemini" else 0), config["cost_output_per_million_usd"])
            cost = round(input_cost + output_cost, 8) if provider in ("gemini", "openai") and input_cost is not None and output_cost is not None else ""
            results.append({"event": event, "tags": tags, "usage": usage, "estimated_cost_usd": cost, "status": "ok"})
        Path("output").mkdir(exist_ok=True)
        Path("output/results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        if results:
            t0 = time.perf_counter()
            publish(results, credentials, sheet_id)
            print(f"[timing] publish_sheet={time.perf_counter()-t0:.3f}s",flush=True)
        t0 = time.perf_counter()
        save_history(doc, run_id, results, model, config["gemini_prompt"], start)
        print(f"[timing] save_history={time.perf_counter()-t0:.3f}s",flush=True)
        prices = [row["estimated_cost_usd"] for row in results]
        usage_total["estimated_cost_usd"] = round(sum(prices),8) if all(isinstance(p,(int,float)) for p in prices) else ""
        t0 = time.perf_counter()
        log_run(doc, run_id, start, "success", len(results), model, usage_total)
        print(f"[timing] log_run={time.perf_counter()-t0:.3f}s total={time.perf_counter()-overall_t0:.3f}s",flush=True)
        print(f"{provider} usage:", usage_total, flush=True)
        print(f"{len(results)} erfolgreich klassifiziert und ins Sheet übertragen.", flush=True)
    except Exception as exc:
        log_run(doc, run_id, start, "failed", 0, type(exc).__name__)
        raise

if __name__ == "__main__":
    main()
