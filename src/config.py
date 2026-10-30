"""Minimal Google Sheets configuration reader for the manually triggered POC."""
import json
import gspread
from google.oauth2.service_account import Credentials
from .tags import STANDARD_TAGS

def settings(credentials_json, sheet_id):
    info=json.loads(credentials_json)
    creds=Credentials.from_service_account_info(info,scopes=["https://www.googleapis.com/auth/spreadsheets"])
    doc=gspread.authorize(creds).open_by_key(sheet_id)
    rows=doc.worksheet("Config").get_all_values()
    config={r[0]:r[1] for r in rows[1:] if len(r)>1 and r[0]}
    tag_rows=doc.worksheet("Tags").get_all_values()
    tags=[r[0] for r in tag_rows[1:] if len(r)>1 and r[1].lower()=="true" and r[0]]
    return doc, {
        "max_events_per_run":max(1,min(50,int(config.get("max_events_per_run","2")))),
        "monthly_limit":max(0,int(config.get("monthly_limit","100"))),
        "changed_only":config.get("changed_only","false").lower()=="true",
        "additional_tags_enabled":config.get("additional_tags_enabled","true").lower()=="true",
        "gemini_prompt":config.get("gemini_prompt", "").strip(),
        "openai_reasoning_effort":config.get("openai_reasoning_effort", "low").strip().lower() or "low",
        "gemini_model":config.get("gemini_model", "").strip(),
        "classifier_provider": config.get("classifier_provider", "groq").strip().lower(),
        "event_source": config.get("event_source", "gocath").strip().lower(),
        "gemini_temperature":max(0.0,min(1.0,float(config.get("gemini_temperature", "0.1")))),
        "max_additional_tags":max(0,min(8,int(config.get("max_additional_tags", "8")))),
        "cost_input_per_million_usd": config.get("cost_input_per_million_usd", ""),
        "cost_output_per_million_usd": config.get("cost_output_per_million_usd", ""),
        "tags":tags or STANDARD_TAGS,
        "tag_synonyms": {r[0]: [v.strip() for v in r[2].split(",") if v.strip()] for r in tag_rows[1:] if len(r)>2 and len(r)>1 and r[1].lower()=="true" and r[0]}
    }

def run_count(doc):
    rows=doc.worksheet("Runs").get_all_values()
    from datetime import datetime,timezone
    month=datetime.now(timezone.utc).strftime("%Y-%m")
    return sum(int(r[4]) for r in rows[1:] if len(r)>4 and r[1].startswith(month) and r[3]=="success" and r[4].isdigit())

def log_run(doc, run_id, start, status, classified, details, metrics=None):
    from datetime import datetime,timezone
    m = metrics or {}
    doc.worksheet("Runs").append_row([run_id,start,datetime.now(timezone.utc).isoformat(),status,classified,details,m.get("input_tokens",0),m.get("output_tokens",0),m.get("thinking_tokens",0),m.get("total_tokens",0),m.get("estimated_cost_usd","")],value_input_option="RAW")

def next_run_id(doc):
    """Sequential POC run IDs; no parallel executions are scheduled."""
    rows=doc.worksheet("Runs").get_all_values()
    ids=[int(row[0]) for row in rows[1:] if row and row[0].isdigit()]
    return str(max(ids, default=0)+1)

def save_history(doc, run_id, results, model, prompt, classified_at):
    rows=[
      [run_id, x["event"]["url"], x["event"]["title"],
       ", ".join(x["tags"]["standard_tags"]), ", ".join(x["tags"]["additional_tags"]),
       x["tags"]["reason"], model, prompt, classified_at,
       x.get("usage",{}).get("input_tokens",0), x.get("usage",{}).get("output_tokens",0), x.get("usage",{}).get("thinking_tokens",0), x.get("usage",{}).get("total_tokens",0), x.get("estimated_cost_usd","")]
      for x in results
    ]
    if rows:
        doc.worksheet("ResultsHistory").append_rows(rows, value_input_option="RAW")
