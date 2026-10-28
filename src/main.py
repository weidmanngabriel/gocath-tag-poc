"""Manual GoCath tagging based on Google Sheet settings."""
import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from .scrape import fetch_events
from .classify import classify, choose_model
from .config import settings, run_count, log_run
from .sheets import publish

SHEET_ID = "1HRyxPjLz2-WUEelplO1YAaO7gCYDyU_77DgUqEtGQ1w"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    key = os.environ["GOCATH_GEMINI_CLASSIFIER_KEY"]
    credentials = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", SHEET_ID)
    doc, config = settings(credentials, sheet_id)
    limit = config["max_events_per_run"]
    if args.limit is not None:
        limit = min(limit, max(1, args.limit))
    limit = min(limit, max(0, config["monthly_limit"] - run_count(doc)))
    if not limit:
        print("Monatslimit erreicht; keine Klassifizierung.")
        return
    start = datetime.now(timezone.utc).isoformat()
    run_id = os.environ.get("GITHUB_RUN_ID", start)
    model = choose_model(key, config["gemini_model"] or os.environ.get("GEMINI_MODEL"))
    events = fetch_events(limit)
    if config["changed_only"]:
        previous = doc.sheet1.get_all_values()
        descriptions = {r[0]: r[2] for r in previous[1:] if len(r) > 6 and r[6] == "ok"}
        events = [event for event in events if descriptions.get(event["url"]) != event["description"]]
    print(f"Zu klassifizieren: {len(events)}, Modell: {model}", flush=True)
    results = []
    try:
        for event in events:
            tags = classify(event, key, model, config["tags"], config["additional_tags_enabled"],
                            config["gemini_prompt"], config["gemini_temperature"], config["max_additional_tags"])
            results.append({"event": event, "tags": tags, "status": "ok"})
        Path("output").mkdir(exist_ok=True)
        Path("output/results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        if results:
            publish(results, credentials, sheet_id)
        log_run(doc, run_id, start, "success", len(results), model)
        print(f"{len(results)} erfolgreich klassifiziert und ins Sheet übertragen.", flush=True)
    except Exception as exc:
        log_run(doc, run_id, start, "failed", 0, type(exc).__name__)
        raise

if __name__ == "__main__":
    main()
