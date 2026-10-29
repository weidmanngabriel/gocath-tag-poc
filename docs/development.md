# Entwicklung und CI

## Lokale Tests
Python-Version und Abhängigkeiten siehe GitHub-Actions-Workflows und `requirements.txt`. Python-Tests: `python -m unittest discover -s tests -v`; Dashboard: im Ordner `web/` `npm install && npm run build`.

## Integration und Konfiguration
Runner: `python -m src.main`; optional `--limit N`, begrenzt durch die im Google Sheet unter `Config` gesetzten Limits. Benötigte Umgebungsvariablen: `GOCATH_GEMINI_CLASSIFIER_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`; optional `GEMINI_MODEL`, `GOOGLE_SHEET_ID`. Die verwendeten Werte für Eventzahl, Limits, Prompt, Tags und Preise werden **zur Laufzeit** aus `Config` und `Tags` gelesen. Keine festen Testmengen in der Dokumentation voraussetzen.

Die Klassifizierung wird nur manuell über `.github/workflows/tag-events.yml` gestartet. `.github/workflows/check.yml` prüft Tests und Dashboard-Build auf relevanten Branches/PRs. Pages-Deployment läuft ausschließlich von `main`.

Vor dem Squash-Merge die GitHub-Actions-Checks des PR prüfen. `.github/workflows/check.yml` startet automatisch bei Push auf `feature/**` sowie bei `pull_request`; ein passender grüner PR-Lauf muss nicht manuell wiederholt werden. Echte Google-Sheet-Schreibzugriffe sind bei Änderungen am Klassifizierungs- oder Datenfluss zu prüfen. Bei reinen UI-Änderungen ohne Änderung dieses Datenflusses genügen grüne CI-Tests, Dashboard-Build und Codeprüfung; ein Live-OAuth-/Sheets-End-to-End-Test ist keine Merge-Voraussetzung. Nicht jede Änderung benötigt einen neuen Gemini-Live-Lauf: Bei reinen Dokumentationsänderungen sind Faktenprüfung und relevante technische Checks ausreichend; für Änderungen am Klassifizierungs-/Datenfluss ist der Live-Test verbindlich. Den jeweils tatsächlichen Prüfumfang im PR offenlegen.

## Dokumentationspflicht
Jede neue oder geänderte Funktion muss im selben Branch die dazugehörige Dokumentation aktualisieren. Konfigurierbare Werte abstrakt beschreiben und auf die maßgebliche Quelle verweisen, damit Dokumente bei Änderungen im Sheet nicht veralten. Details: [agent-workflow.md](agent-workflow.md).

## Laufzeitdiagnose

Der manuelle Runner protokolliert mit dem Präfix `[timing]` monotone Laufzeiten in Sekunden: Konfiguration/Authentifizierung, Modellauswahl, Webseitenabrufe (ohne URL-Inhalt), jede Gemini-Anfrage mit HTTP-Status/Versuch, etwaige Retry-Wartezeiten, Dauer je Klassifizierung, Google-Sheet-Publikation, History- und Run-Schreibvorgänge und Gesamtlaufzeit. Diese Messungen verändern Modell, Request-Reihenfolge, Retry-Verhalten und Verarbeitung nicht. Der Ablauf vor dem Start des Python-Prozesses (Runner-Start, Paketinstallation, Tests) bleibt über GitHub-Actions-Schrittzeiten nachvollziehbar. Keine API-Schlüssel, Prompts oder Eventtexte in Diagnose-Logs ausgeben.

## Isolierter Gemini-Latenztest

Im bestehenden manuellen GitHub-Actions-Workflow `tag-events.yml` mit dem Modus `latency` werden für die fest gepinnte Modell-ID `gemini-3.5-flash-lite` drei Paare von Anfragen ausgeführt: ein minimaler Prompt (`OK`) und derselbe vollständige GoCath-Prompt mit derselben öffentlich gelesenen Veranstaltung. Reihenfolge der beiden Fälle wechselt je Runde. Für beide wird `thinkingLevel=minimal` gesetzt. Die Messung umfasst HTTP-Status, verstrichene Zeit bis zu den Response-Headern (`requests.Response.elapsed`, Annäherung an TTFB), Gesamtdauer inkl. Response-Body und Tokens. Die Antworten selbst werden nicht geloggt. Ergebnisartefakt: `output/latency-probe.json`. **Es gibt keine Schreibzugriffe in Google Sheets und keine Änderungen an Produktivklassifizierung, Modellkonfiguration oder Retry-Verhalten.** Ein fehlgeschlagener API-Aufruf wird ausgewiesen und nicht als schnelle erfolgreiche Antwort interpretiert. Die Messung trennt nicht DNS-, TCP- und TLS-Zeiten; `elapsed` ist kein reines Modell-Timing.

## Groq-Vergleich (manuell, read-only)

`tag-events.yml` bietet den Modus `compare-groq` auf dem Test-Branch. Jeweils dieselben öffentlichen Veranstaltungen werden mit `gemini-3.5-flash-lite` (`thinkingLevel=minimal`) und `openai/gpt-oss-20b` auf Groq (`reasoning_effort=low`) klassifiziert. Das ist ein Vergleich mit geringem Reasoning, kein vollständig identisches Thinking-Niveau. Die Reihenfolge wechselt pro Veranstaltung. Es gibt keine Schreibzugriffe auf Sheets und keine Änderung des regulären Modells. Das Secret `GROQ_API_KEY` wird ausschließlich als Authorization-Header verwendet, nie geloggt. `output/groq-comparison.json` hält Ergebnis-Tags, HTTP-Status, Sekunden und Tokenverbrauch fest. Keine unvalidierten Fehlantworten als Erfolg zählen. Tag-Übereinstimmung zwischen Modellen beweist keine fachliche Richtigkeit.

## Groq-Rate-Limits

Der reguläre Groq-Runner behandelt HTTP 429 sowie vorübergehende 5xx-Fehler durch maximal vier Versuche pro Veranstaltung. Er berücksichtigt einen numerischen `Retry-After`-Header (begrenzt auf 120 Sekunden) und wartet ansonsten gestaffelt 10, 20, 30 Sekunden. HTTP-Fehler werden nur als Statuscode protokolliert; Secrets und Antworttexte nicht. Bei dauerhaftem Fehler bricht der Lauf ab und behauptet keine erfolgreiche Klassifizierung. Nicht erneut versuchen bei anderen HTTP-Fehlern.
