"""RC configuration reader for model prices and Criteria; no legacy tagging dependencies."""
import json
import gspread
from google.oauth2.service_account import Credentials

def settings(credentials_json, sheet_id):
    info=json.loads(credentials_json)
    creds=Credentials.from_service_account_info(info,scopes=["https://www.googleapis.com/auth/spreadsheets"])
    doc=gspread.authorize(creds).open_by_key(sheet_id)
    rows=doc.worksheet("Config").get_all_values()
    config={r[0]:r[1] for r in rows[1:] if len(r)>1 and r[0]}
    try:
        criteria_rows = doc.worksheet("Criteria").get_all_values()
    except gspread.WorksheetNotFound:
        criteria_rows = []
    criteria = []
    for r in criteria_rows[1:]:
        if len(r) < 7 or not r[0].strip() or r[4].strip().lower() != "true":
            continue
        question_type = (r[7].strip().lower() if len(r) > 7 and r[7].strip() else "predicate")
        if question_type not in ("predicate", "choice", "score"):
            raise ValueError("Invalid question type in Criteria: " + r[0])
        options = json.loads(r[8]) if len(r) > 8 and r[8].strip() else []
        if question_type == "choice" and not (isinstance(options, list) and 2 <= len(options) <= 255):
            raise ValueError("Choice requires 2–255 options: " + r[0])
        if question_type == "score" and not (isinstance(options, list) and 2 <= len(options) <= 10):
            raise ValueError("Score requires 2–10 levels: " + r[0])
        if question_type != "predicate":
            if not all(isinstance(o, dict) and isinstance(o.get("value" if question_type == "choice" else "label"), str)
                       and o.get("value" if question_type == "choice" else "label") for o in options):
                raise ValueError("Invalid question options: " + r[0])
            keys = [o["value" if question_type == "choice" else "label"] for o in options]
            if len(set(keys)) != len(keys):
                raise ValueError("Duplicate question options: " + r[0])
        weight = float(r[5] or 0)
        if question_type != "predicate" and weight != 0:
            raise ValueError("Only predicate questions can influence relevance: " + r[0])
        criteria.append({"id": r[0].strip(), "category": r[1].strip(), "label": r[2].strip(),
            "description": r[3].strip(), "weight": weight, "threshold": float(r[6] or 0.65),
            "type": question_type, "options": options})
    return doc, {
        "rc_model": config.get("rc_model", "gpt-6-luna").strip(),
        "rc_input_per_million_usd": config.get("rc_input_per_million_usd", "0.10"),
        "rc_cached_input_per_million_usd": config.get("rc_cached_input_per_million_usd", "0.01"),
        "rc_cache_write_per_million_usd": config.get("rc_cache_write_per_million_usd", "0.125"),
        "rc_cache_write_12h_per_million_usd": config.get("rc_cache_write_12h_per_million_usd", "0.25"),
        "rc_output_per_million_usd": config.get("rc_output_per_million_usd", "0"),
        "tag_prompt": config.get("gemini_prompt", "").strip(),
        "tag_model": config.get("tag_model", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
        "tag_limit": max(0, min(8, int(config.get("max_additional_tags", "8")))) if config.get("additional_tags_enabled", "true").lower() == "true" else 0,
        "criteria": criteria,
    }
