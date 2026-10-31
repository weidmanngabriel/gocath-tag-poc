"""Read-only, paired before/after token and classification comparison.

Run manually in GitHub Actions mode compare-input; never writes Sheets.
Only numeric diagnostics are stored, no event text or API credentials.
"""
import argparse
import json
import os
from pathlib import Path

from .config import settings
from .decisions_classify import classify_decisions
from .regnum_scrape import fetch_events as fetch_regnum
from .scrape import clean_event_text, fetch_events as fetch_gocath


def relevant(scores, criteria):
    weights = {c["id"]: c["weight"] for c in criteria}
    signals = sorted((r["score"] * weights.get(r["id"], 0)
                      for r in scores if weights.get(r["id"], 0) > 0), reverse=True)
    return ("likely_relevant" if any(x >= 0.7 for x in signals)
            or sum(x >= 0.45 for x in signals) >= 2
            else "review" if any(x >= 0.25 for x in signals)
            else "likely_not_relevant")


def compare(limit=10):
    if limit < 1 or limit > 10:
        raise ValueError("Probe limit must be 1–10")
    doc, cfg = settings(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],
                        os.environ["GOOGLE_SHEET_ID"])
    del doc  # Only read settings; never write into Sheets.
    provider = cfg["event_source"]
    if provider == "gocath":
        original = fetch_gocath(limit, clean=False)
        optimized = [{**event, "description": clean_event_text(event["description"])}
                     for event in original]
    elif provider == "regnum_christi":
        original = fetch_regnum(limit)
        optimized = original
    else:
        raise ValueError("Unknown event source")
    api_key = os.environ["GOCATH_OPENAI"]
    results = []
    for number, (before, after) in enumerate(zip(original, optimized), start=1):
        old_usage, new_usage = {}, {}
        old = classify_decisions(before, api_key, cfg, usage_sink=old_usage, compact=False)
        new = classify_decisions(after, api_key, cfg, usage_sink=new_usage)
        by_old = {x["id"]: x for x in old["criteria_scores"]}
        by_new = {x["id"]: x for x in new["criteria_scores"]}
        if set(by_old) != set(by_new):
            raise ValueError("A/B answers differ in criterion IDs")
        changes = {key: round(abs(by_new[key]["score"] - by_old[key]["score"]), 4)
                   for key in by_old}
        selected_changes = {
            key: [by_old[key]["answer"].get("choice"), by_new[key]["answer"].get("choice")]
            for key in by_old if by_old[key]["type"] == "choice"
            and by_old[key]["answer"].get("choice") != by_new[key]["answer"].get("choice")
        }
        results.append({
            "event_number": number,
            "source_url": before["url"],  # Stable public source reference, no event description.
            "description_chars_before": len(before["description"]),
            "description_chars_after": len(after["description"]),
            "tokens_before": old_usage.get("input_tokens", 0),
            "tokens_after": new_usage.get("input_tokens", 0),
            "relevance_before": relevant(old["criteria_scores"], cfg["criteria"]),
            "relevance_after": relevant(new["criteria_scores"], cfg["criteria"]),
            "mean_abs_score_change": round(sum(changes.values()) / len(changes), 4),
            "max_score_change": max(changes.values()),
            "large_changes": {key: value for key, value in changes.items() if value >= 0.2},
            "choice_changed": selected_changes,
        })
        print(f"[input-probe] event={number}/{len(original)} old_tokens={old_usage.get('input_tokens',0)} "
              f"new_tokens={new_usage.get('input_tokens',0)} "
              f"relevance_changed={results[-1]['relevance_before'] != results[-1]['relevance_after']}",
              flush=True)
    old_total = sum(x["tokens_before"] for x in results)
    new_total = sum(x["tokens_after"] for x in results)
    summary = {
        "source": provider, "events": len(results),
        "input_tokens_before": old_total, "input_tokens_after": new_total,
        "saved_input_tokens": old_total - new_total,
        "saved_percent": round(100 * (1 - new_total / old_total), 2) if old_total else None,
        "changed_relevance_count": sum(x["relevance_before"] != x["relevance_after"] for x in results),
        "changed_choice_count": sum(bool(x["choice_changed"]) for x in results),
        "avg_mean_abs_score_change": round(sum(x["mean_abs_score_change"] for x in results) / len(results), 4),
        "events_detail": results,
    }
    Path("output").mkdir(exist_ok=True)
    Path("output/input-probe.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                               encoding="utf-8")
    print("[input-probe] SUMMARY " + json.dumps({k:v for k,v in summary.items() if k!="events_detail"}),
          flush=True)
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=10)
    args = p.parse_args()
    compare(args.limit)
