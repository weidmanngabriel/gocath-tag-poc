# Entwicklung und CI

## Lokale Tests
Python-Version und Abhängigkeiten siehe GitHub-Actions-Workflows und `requirements.txt`. Python-Tests: `python -m unittest discover -s tests -v`; Dashboard: im Ordner `web/` `npm install && npm run build`.

## Integration und Konfiguration
Runner: `python -m src.main`; optional `--limit N`, begrenzt durch die im Google Sheet unter `Config` gesetzten Limits. Benötigte Umgebungsvariablen: `GOCATH_GEMINI_CLASSIFIER_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`; optional `GEMINI_MODEL`, `GOOGLE_SHEET_ID`. Die verwendeten Werte für Eventzahl, Limits, Prompt, Tags und Preise werden **zur Laufzeit** aus `Config` und `Tags` gelesen. Keine festen Testmengen in der Dokumentation voraussetzen.

Die Klassifizierung wird nur manuell über `.github/workflows/tag-events.yml` gestartet. `.github/workflows/check.yml` prüft Tests und Dashboard-Build auf relevanten Branches/PRs. Pages-Deployment läuft ausschließlich von `main`.

Vor dem Squash-Merge echte GitHub-Actions-Logs und erfolgreiche Google-Sheet-Schreibzugriffe prüfen. Nicht jede Änderung benötigt einen neuen Gemini-Live-Lauf: Bei reinen Dokumentationsänderungen sind Faktenprüfung und relevante technische Checks ausreichend; für Änderungen am Klassifizierungs-/Datenfluss ist der Live-Test verbindlich. Den jeweils tatsächlichen Prüfumfang im PR offenlegen.

## Dokumentationspflicht
Jede neue oder geänderte Funktion muss im selben Branch die dazugehörige Dokumentation aktualisieren. Konfigurierbare Werte abstrakt beschreiben und auf die maßgebliche Quelle verweisen, damit Dokumente bei Änderungen im Sheet nicht veralten. Details: [agent-workflow.md](agent-workflow.md).
