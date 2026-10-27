# GoCath Tagging POC

Manueller GitHub Actions-Test: Bis zu 20 echte Veranstaltungen von https://gocath.org/de/finde abrufen, mit Gemini klassifizieren und in das Google Sheet **GoCath Auto Event Tagging** schreiben. Keine zusätzliche Webrecherche.

## Starten
1. Repository-Secrets `GOCATH_GEMINI_CLASSIFIER_KEY` und `GOOGLE_SERVICE_ACCOUNT_JSON` (vollständiger JSON-Inhalt) müssen gesetzt sein.
2. Die Google Sheets API muss aktiviert sein; Service-Account-`client_email` benötigt Bearbeiterrechte im Zielsheet.
3. GitHub **Actions → GoCath Tagging POC → Run workflow** auswählen.
4. Ergebnisse im Sheet prüfen; zusätzlich wird `results.json` als Actions-Artefakt hochgeladen.

Der POC verwendet Gemini `gemini-2.5-flash-lite`; Modell per `GEMINI_MODEL` änderbar. Wenn GoCath die öffentliche HTML-Struktur ändert, muss der Scraper angepasst werden. Keine stillen Demo-Daten.

Siehe [Architektur](docs/architecture.md), [Fachregeln](docs/domain.md), [Entwicklung](docs/development.md) und [Tests](docs/testing.md).
