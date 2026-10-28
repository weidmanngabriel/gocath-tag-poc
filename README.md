# GoCath Auto Event Tagging – POC

Eine minimale TypeScript-Oberfläche für **manuelle** GoCath-Klassifizierungen. Öffentliche GoCath-Veranstaltungen werden über GitHub Actions gelesen, durch Gemini mit konfigurierbarem Prompt klassifiziert und in ein Google Sheet geschrieben.

- `web/`: Vite/TypeScript Dashboard für Google OAuth, Konfiguration und Vergleich der historischen Tag-Zuordnungen
- `src/`: Python Runner, Gemini-Modell und Google-Sheets-Anbindung
- `.github/workflows/tag-events.yml`: ausschließlich manueller Klassifizierungstrigger
- `.github/workflows/pages.yml`: GitHub-Pages-Auslieferung des Dashboards
- `.github/workflows/check.yml`: Python-Tests und TypeScript-Build

**Pro Testlauf 10 Veranstaltungen** (Wert `max_events_per_run` im Google Sheet `Config`). Jeder Lauf bekommt die nächste freie numerische Run-ID aus `Runs`. Die Ergebnisse werden unverändert in `ResultsHistory` gespeichert und lassen sich im Dashboard nach Lauf vergleichen. Das bisherige erste Blatt zeigt weiter die letzten Tags je Event.

**Prompt & KI-Parameter:** `gemini_prompt`, `gemini_model` (optional), `gemini_temperature`, `max_additional_tags` sowie aktivierte Tags aus `Tags` werden beim Runner-Start direkt aus Google Sheets geladen.

**Einrichtung:** [docs/dashboard.md](docs/dashboard.md). Für die Google-Anmeldung fehlt bis zur Einrichtung die öffentliche GitHub-Actions-Variable `VITE_GOOGLE_CLIENT_ID`; OAuth muss den Pages-Origin autorisieren. API-Keys und Service-Account-JSON bleiben ausschließlich GitHub Secrets.

**Tests:** `python -m unittest discover -s tests -v` und in `web/`: `npm install && npm run build`.
