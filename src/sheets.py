"""Write results to the explicitly configured test Google Sheet."""
import json
import gspread
from google.oauth2.service_account import Credentials

HEADERS = ["Event-URL", "Titel", "Beschreibung", "Standard-Tags", "Zusätzliche Tags", "Begründung", "Status"]

def publish(results, json_credentials, sheet_id):
    credentials = Credentials.from_service_account_info(json.loads(json_credentials),
        scopes=["https://www.googleapis.com/auth/spreadsheets"])
    ws = gspread.authorize(credentials).open_by_key(sheet_id).sheet1
    existing = ws.get_all_values()
    if not existing or not any(any(str(v).strip() for v in row) for row in existing):
        ws.update(range_name="A1:G1", values=[HEADERS])
        existing = [HEADERS]
    if existing[0] != HEADERS:
        raise ValueError("Das Zielblatt ist nicht leer und hat andere Spalten. Keine Änderungen vorgenommen.")
    by_url = {row[0]: i for i, row in enumerate(existing, start=1) if i > 1 and row}
    append = []
    for item in results:
        e = item["event"]
        tags = item["tags"]
        values = [e["url"], e["title"], e["description"], ", ".join(tags["standard_tags"]),
            ", ".join(tags["additional_tags"]), tags["reason"], item["status"]]
        row = by_url.get(e["url"])
        if row:
            ws.update(range_name=f"A{row}:G{row}", values=[values])
        else:
            append.append(values)
    if append:
        ws.append_rows(append, value_input_option="RAW")
