# GoCath Auto Event Tagging – POC

Eine minimale TypeScript-Oberfläche für **manuelle** GoCath-Klassifizierungen. Öffentliche GoCath-Veranstaltungen werden über GitHub Actions gelesen, durch den in `Config.classifier_provider` gewählten Anbieter klassifiziert und in ein Google Sheet geschrieben.

- `web/`: Vite/TypeScript Dashboard für Google OAuth, Konfiguration und Vergleich der historischen Tag-Zuordnungen
- `src/`: Python Runner, Gemini-Modell und Google-Sheets-Anbindung
- `.github/workflows/tag-events.yml`: ausschließlich manueller Klassifizierungstrigger
- `.github/workflows/pages.yml`: GitHub-Pages-Auslieferung des Dashboards
- `.github/workflows/check.yml`: Python-Tests und TypeScript-Build

**Veranstaltungen pro Testlauf sind konfigurierbar** (Wert `max_events_per_run` und weitere Limits im Google Sheet `Config`). Jeder Lauf bekommt die nächste freie numerische Run-ID aus `Runs`. Die Ergebnisse werden unverändert in `ResultsHistory` gespeichert und lassen sich im Dashboard nach Lauf vergleichen. Das bisherige erste Blatt zeigt weiter die letzten Tags je Event.

**Prompt & KI-Parameter:** `gemini_prompt`, `gemini_model` (optional), `gemini_temperature`, `max_additional_tags` sowie aktivierte Tags aus `Tags` werden beim Runner-Start direkt aus Google Sheets geladen.

**Dokumentation:** Agenten starten mit [AGENTS.md](AGENTS.md); [Konzept](docs/concept.md), [Architektur](docs/architecture.md), [Fachregeln](docs/domain.md), [Entwicklung](docs/development.md), [Dashboard](docs/dashboard.md), [Einrichtung](docs/setup.md) und [Agenten-Workflow](docs/agent-workflow.md). Die öffentliche GitHub-Actions-Variable `VITE_GOOGLE_CLIENT_ID` und der autorisierte Pages-Origin werden für den Google-Login benötigt. Einrichtung und Fehlerdiagnose stehen in `docs/setup.md`. API-Keys und Service-Account-JSON bleiben ausschließlich GitHub Secrets.

**Tests:** `python -m unittest discover -s tests -v` und in `web/`: `npm install && npm run build`.

**Neue Kriterien (PR #27):** `Criteria` enthält bearbeitbare Merkmale (Format, Thema, Zielgruppe, Kontext) und Relevanzgewichte. Bei OpenAI werden pro Event alle Scores einschließlich der niedrigen Werte in `ClassificationDetails` append-only gespeichert. Die Relevanz wird regelbasiert abgeleitet, **nicht** zum Ausschluss verwendet. Die Dashboard-Seite zeigt je Run die vollständigen Scores; Änderungen an vorhandenen Kriterien/Einstellungen werden beim Verlassen des Feldes automatisch gespeichert. Die alten Standard-Tags bleiben zur Kompatibilität erhalten. Gemini und Groq erzeugen noch keine neuen Kriterienscores.

**Aktueller Zustand:** Standard-Tag-Aktivierung und Synonyme sind im Sheet `Tags` pflegbar; Run-Historie, Token- und Kostenschätzung sowie Contains-/Fuzzy-Suche stehen im Dashboard bereit. Der Runner wird ausschließlich manuell gestartet. Die maßgeblichen aktuellen Einstellungen stehen im Google Sheet, nicht in dieser README.

**KI-Anbieter:** Der aktive Klassifizierungsanbieter ist im Dashboard unter `classifier_provider` zwischen OpenAI, Groq und Gemini auswählbar. Der aktuelle Wert steht ausschließlich im Sheet. Beide API-Keys liegen ausschließlich in GitHub Secrets; die Klassifizierung bleibt manuell und schreibt nur ins Test-Sheet.

## OpenAI Decisions API
Für `classifier_provider=openai` verwendet der Runner nun `POST /v1/decisions` mit `gpt-6-luna` und genau einer `predicate`-Frage je aktivem Kriterium aus `Criteria`. Alle Wahrscheinlichkeiten werden auch bei niedrigen Werten in `ClassificationDetails` gespeichert; die katholische Relevanz bleibt eine separate nachvollziehbare Code-Regel, ohne automatische Ausschlüsse. `gemini` und `groq` nutzen weiterhin ihren bisherigen Ablauf.

Die Decisions API erzeugt **keinen Freitext**: `additional_tags` ist bei neuen OpenAI-Läufen leer, die Legacy-Standard-Tags werden nur noch über definierte Format-Aliase aus erfolgreichen Kriterienzuordnungen abgeleitet; `reason` erklärt dies allgemein statt einer KI-Begründung. Historische Daten bleiben erhalten. Die Preise für OpenAI-Decisions werden als ungekürzte Eingabetokens mit 0,10 USD pro Million und ohne Outputkosten geschätzt; mögliche Cache-Abschläge sind nicht berücksichtigt. Eine echte Live-API-Ausführung muss nach grüner CI mit dem manuellen Workflow validiert werden.
