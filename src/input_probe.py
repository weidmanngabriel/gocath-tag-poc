"""Read-only factorial comparison of Decisions input changes.

Five arms on identical event data:
baseline, cleaning only, central instructions only, both, and URL omission.
No writes to Google Sheets; source URLs and numerical diagnostics only.
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


VARIANTS = ("baseline", "clean_only", "rules_only", "combined", "optimized")


def event_variants(source, original):
    """All variants use the same raw source snapshot; do not re-fetch a page."""
    baseline = {**original, "description": original["description"][:5500]}
    cleaned = ({**original, "description": clean_event_text(original["description"])[:5500]}
               if source == "gocath" else baseline)
    return {
        "baseline": (baseline, False, False),
        "clean_only": (cleaned, False, False),
        "rules_only": (baseline, True, False),
        "combined": (cleaned, True, False),
        "optimized": (cleaned, True, True),
    }


def compare_scores(baseline, candidate):
    before = {s["id"]: s for s in baseline}
    after = {s["id"]: s for s in candidate}
    if set(before) != set(after):
        raise ValueError("Comparison answers differ in criterion IDs")
    score_deltas = {key: round(abs(after[key]["score"]-before[key]["score"]), 4)
                    for key in before}
    choices = {
        key: [before[key]["answer"].get("choice"), after[key]["answer"].get("choice")]
        for key in before if before[key]["type"] == "choice"
        and before[key]["answer"].get("choice") != after[key]["answer"].get("choice")
    }
    return {
        "mean_abs_score_change": round(sum(score_deltas.values())/len(score_deltas), 4),
        "max_score_change": max(score_deltas.values()),
        "large_changes": {key: value for key, value in score_deltas.items() if value >= 0.2},
        "choice_changed": choices,
    }


def summarize(results):
    summary = {}
    for variant in VARIANTS[1:]:
        before = sum(item["variants"]["baseline"]["tokens"] for item in results)
        after = sum(item["variants"][variant]["tokens"] for item in results)
        summary[variant] = {
            "input_tokens_before": before,
            "input_tokens_after": after,
            "saved_input_tokens": before-after,
            "saved_percent": round(100*(1-after/before), 2) if before else None,
            "relevance_changed_count": sum(
                item["variants"][variant]["relevance"] != item["variants"]["baseline"]["relevance"]
                for item in results),
            "choice_changed_count": sum(bool(item["variants"][variant]["comparison"]["choice_changed"])
                                        for item in results),
            "avg_mean_abs_score_change": round(sum(
                item["variants"][variant]["comparison"]["mean_abs_score_change"] for item in results
            )/len(results), 4) if results else None,
        }
    return summary


def compare(limit=5, source="both"):
    if limit < 1 or limit > 10:
        raise ValueError("Probe limit must be 1–10")
    doc, cfg = settings(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],
                        os.environ["GOOGLE_SHEET_ID"])
    del doc  # Read-only config. Never publish any results.
    if source == "configured":
        source = cfg["event_source"]
    if source not in ("both", "gocath", "regnum_christi"):
        raise ValueError("Invalid comparison source")
    pairs = []
    if source in ("both", "gocath"):
        pairs.extend(("gocath", e) for e in fetch_gocath(limit, clean=False, truncate=False))
    if source in ("both", "regnum_christi"):
        pairs.extend(("regnum_christi", e) for e in fetch_regnum(limit))
    api_key = os.environ["GOCATH_OPENAI"]
    results = []
    for number, (event_source, original) in enumerate(pairs, start=1):
        variants = event_variants(event_source, original)
        evaluated = {}
        # Alternate order to avoid always calling the baseline first.
        order = VARIANTS if number % 2 else tuple(reversed(VARIANTS))
        for variant in order:
            event, compact, strip_url = variants[variant]
            usage = {}
            scores = classify_decisions(event, api_key, cfg, usage_sink=usage,
                                        compact=compact, strip_url=strip_url)["criteria_scores"]
            if not usage.get("input_tokens"):
                raise ValueError("Provider did not return input_tokens: " + variant)
            evaluated[variant] = {"scores": scores, "tokens": usage["input_tokens"],
                                  "relevance": relevant(scores, cfg["criteria"])}
        baseline = evaluated["baseline"]["scores"]
        output_variants = {}
        for variant in VARIANTS:
            value = evaluated[variant]
            output_variants[variant] = {
                "tokens": value["tokens"],
                "relevance": value["relevance"],
                "comparison": compare_scores(baseline, value["scores"])
            }
        results.append({
            "event_number": number,
            "event_source": event_source,
            "source_url": original["url"],
            "description_chars_before": len(variants["baseline"][0]["description"]),
            "description_chars_cleaned": len(variants["clean_only"][0]["description"]),
            "variants": output_variants,
        })
        print("[input-probe] event=" + str(number) + "/" + str(len(pairs))
              + " tokens=" + json.dumps({k: v["tokens"] for k, v in output_variants.items()})
              + " relevance_changed=" + json.dumps({
                  k: v["relevance"] != output_variants["baseline"]["relevance"]
                  for k, v in output_variants.items() if k != "baseline"
              }), flush=True)
    summary = {"source": source, "events": len(results),
               "variants": summarize(results), "events_detail": results}
    Path("output").mkdir(exist_ok=True)
    Path("output/input-probe.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[input-probe] SUMMARY "
          + json.dumps({k: v for k, v in summary.items() if k != "events_detail"}), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--source", choices=("both", "configured", "gocath", "regnum_christi"),
                        default="both")
    args = parser.parse_args()
    compare(args.limit, args.source)
