# Architektur
GitHub Actions workflow_dispatch → Python requests/BeautifulSoup → öffentliche GoCath-Veranstaltungslinks & Detailseiten → Gemini Developer API → kontrollierte Tags und freie Suchbegriffe → Google Sheets API (Service Account) → JSON-Artefakt.

Das Google Sheet ist alleiniger externer Schreibort. Deduplizierung erfolgt per Veranstaltungs-URL. HTML-Seitenstruktur ist nicht garantiert; beim Fehlen von Links wird der Lauf mit Fehler abgebrochen. Keine externe Webrecherche.
