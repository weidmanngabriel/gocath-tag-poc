# Entwicklung und CI

## Lokale Tests
Python-Version und Abhängigkeiten siehe GitHub-Actions-Workflows und `requirements.txt`. Python-Tests: `python -m unittest discover -s tests -v`; Dashboard: im Ordner `web/` `npm install && npm run build`.

## Integration und Konfiguration
Runner: `python -m src.main`; optional `--limit N`, begrenzt durch die im Google Sheet unter `Config` gesetzten Limits. Benötigte Umgebungsvariablen: `GOCATH_GEMINI_CLASSIFIER_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`; optional `GEMINI_MODEL`, `GOOGLE_SHEET_ID`. Die verwendeten Werte für Eventzahl, Limits, Prompt, Tags und Preise werden **zur Laufzeit** aus `Config` und `Tags` gelesen. Keine festen Testmengen in der Dokumentation voraussetzen.

Die Klassifizierung wird nur manuell über `.github/workflows/tag-events.yml` gestartet. `.github/workflows/check.yml` prüft Tests und Dashboard-Build auf relevanten Branches/PRs. Pages-Deployment läuft ausschließlich von `main`.

Vor dem Squash-Merge echte GitHub-Actions-Logs und erfolgreiche Google-Sheet-Schreibzugriffe prüfen. Nicht jede Änderung benötigt einen neuen Gemini-Live-Lauf: Bei reinen Dokumentationsänderungen sind Faktenprüfung und relevante technische Checks ausreichend; für Änderungen am Klassifizierungs-/Datenfluss ist der Live-Test verbindlich. Den jeweils tatsächlichen Prüfumfang im PR offenlegen.

## Dokumentationspflicht
Jede neue oder geänderte Funktion muss im selben Branch die dazugehörige Dokumentation aktualisieren. Konfigurierbare Werte abstrakt beschreiben und auf die maßgebliche Quelle verweisen, damit Dokumente bei Änderungen im Sheet nicht veralten. Details: [agent-workflow.md](agent-workflow.md).

## Laufzeitdiagnose

Der manuelle Runner protokolliert mit dem Präfix `[timing]` monotone Laufzeiten in Sekunden: Konfiguration/Authentifizierung, Modellauswahl, Webseitenabrufe (ohne URL-Inhalt), jede Gemini-Anfrage mit HTTP-Status/Versuch, etwaige Retry-Wartezeiten, Dauer je Klassifizierung, Google-Sheet-Publikation, History- und Run-Schreibvorgänge und Gesamtlaufzeit. Diese Messungen verändern Modell, Request-Reihenfolge, Retry-Verhalten und Verarbeitung nicht. Der Ablauf vor dem Start des Python-Prozesses (Runner-Start, Paketinstallation, Tests) bleibt über GitHub-Actions-Schrittzeiten nachvollziehbar. Keine API-Schlüssel, Prompts oder Eventtexte in Diagnose-Logs ausgeben.

## Manueller A/B-Vergleich von Gemini und Gemma

Der bestehende manuelle Workflow `.github/workflows/tag-events.yml` bietet den optionalen Modus `compare`; dieser klassifiziert dieselben öffentlichen Veranstaltungen mit den fest gepinnten Modellen `gemini-3.5-flash-lite` und `gemma-4-26b-a4b-it`, jeweils mit `thinkingLevel=minimal` (Gemma: Thinking aus). Beide erhalten dieselben aktiven Tags, Synonyme, Prompt-Regeln und Eventdaten; die API-Aufrufe sind seriell. JSON-Validierung, HTTP-Status, Dauer, Tokenverbrauch und Tag-Ergebnisse werden in den GitHub-Actions-Artefakten `ab-results.json` und `ab-results.csv` gespeichert. **Es werden keine Ergebnisse in das Google Sheet geschrieben und das Produktionsmodell wird nicht verändert.** Das Sheet wird ausschließlich zur Übernahme der aktuellen Einstellungen gelesen. Nicht erfolgreiche Requests und unparsebare JSON-Antworten bleiben als Fehler erkennbar; kein stiller Fallback. Zum Start im GitHub-Actions-Dialog den Feature-Branch und Modus `compare` wählen; `classify` bleibt der Standard. Die Tag-Übereinstimmung ist nur ein Vergleich zwischen Modellen, kein Beweis für fachliche Richtigkeit.
