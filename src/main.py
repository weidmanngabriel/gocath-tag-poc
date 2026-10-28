import argparse
import json
import os
from pathlib import Path
from .scrape import fetch_events
from .classify import classify, choose_model
from .sheets import publish

DEFAULT_SHEET = "1HRyxPjLz2-WUEelplO1YAaO7gCYDyU_77DgUqEtGQ1w"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    options = parser.parse_args()
    if not 1 <= options.limit <= 50:
        parser.error("limit must be between 1 and 50")
    key = os.environ["GOCATH_GEMINI_CLASSIFIER_KEY"]
    credentials = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    model = choose_model(key, os.environ.get("GEMINI_MODEL"))
    print("Using accessible Gemini model: " + model, flush=True)
    events = fetch_events(options.limit)
    print(f"Gefundene Veranstaltungen: {len(events)}", flush=True)
    results = []
    failures = 0
    for event in events:
        try:
            tags = classify(event, key, model)
            status = "ok"
        except Exception as exc:
            failures += 1
            tags = {"standard_tags": [], "additional_tags": [], "reason": ""}
            status = "error: " + str(exc)[:120]
            print("Gemini-Fehler für " + event["url"] + ": " + status, flush=True)
        results.append({"event": event, "tags": tags, "status": status})
    Path("output").mkdir(exist_ok=True)
    Path("output/results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        # Never overwrite previously successful classifications with empty failures.
        raise RuntimeError(f"{failures}/{len(results)} Klassifizierungen fehlgeschlagen; kein Sheet-Update.")
    publish(results, credentials, os.environ.get("GOOGLE_SHEET_ID", DEFAULT_SHEET))
    print(f"{len(results)} erfolgreich klassifiziert und ins Sheet übertragen.")

if __name__ == "__main__":
    main()
