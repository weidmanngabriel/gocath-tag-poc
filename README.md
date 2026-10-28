# GoCath Auto Event Tagging – POC

Eine minimale TypeScript-Oberfläche für **manuelle** GoCath-Klassifizierungen. Öffentliche GoCath-Veranstaltungen werden über GitHub Actions gelesen, durch Gemini mit konfigurierbarem Prompt klassifiziert und in ein Google Sheet geschrieben.

- `web/`: Vite/TypeScript Dashboard für Google OAuth, Konfiguration und Vergleich der historischen Tag-Zuordnungen
- `src/`: Python Runner, Gemini-Modell und Google-Sheets-Anbindung
- `.github/workflows/tag-events.yml`: ausschließlich manueller Klassifizierungstrigger
- `.github/workflows/pages.yml`: GitHub-Pages-Auslieferung des Dashboards
- `.github/workflows/check.yml`: Python-Tests und TypeScript-Build

**Veranstaltungen pro Testlauf sind konfigurierbar** (Wert `max_events_per_run` und weitere Limits im Google Sheet `Config`). Jeder Lauf bekommt die nächste freie numerische Run-ID aus `Runs`. Die Ergebnisse werden unverändert in `ResultsHistory` gespeichert und lassen sich im Dashboard nach Lauf vergleichen. Das bisherige erste Blatt zeigt weiter die letzten Tags je Event.

**Prompt & KI-Parameter:** `gemini_prompt`, `gemini_model` (optional), `gemini_temperature`, `max_additional_tags` sowie aktivierte Tags aus `Tags` werden beim Runner-Start direkt aus Google Sheets geladen.

**Dokumentation:** Agenten starten mit [AGENTS.md](AGENTS.md); [Konzept](docs/concept.md), [Architektur](docs/architecture.md), [Fachregeln](docs/domain.md), [Entwicklung](docs/development.md), [Dashboard](docs/dashboard.md), [Einrichtung](docs/setup.md) und [Agenten-Workflow](docs/agent-workflow.md). Die öffentliche GitHub-Actions-Variable `VITE_GOOGLE_CLIENT_ID` und der autorisierte Pages-Origin werden für den Google-Login benötigt. Einrichtung und Fehlerdiagnose stehen in `docs/setup.md`. API-Keys und Service-Account-JSON bleiben ausschließlich GitHub Secrets.

**Tests:** `python -m unittest discover -s tests -v` und in `web/`: `npm install && npm run build`.

**Aktueller Zustand:** Standard-Tag-Aktivierung und Synonyme sind im Sheet `Tags` pflegbar; Run-Historie, Token- und Kostenschätzung sowie Contains-/Fuzzy-Suche stehen im Dashboard bereit. Der Runner verwendet Gemini und wird ausschließlich manuell gestartet. Die maßgeblichen aktuellen Einstellungen stehen im Google Sheet, nicht in dieser README.
