# Entwicklung und CI

Python 3.12, Installation über requirements.txt. Lokal: `python -m unittest discover -s tests -v`. Integration: `python -m src.main --limit 20` mit Umgebungsvariablen `GOCATH_GEMINI_CLASSIFIER_KEY` und `GOOGLE_SERVICE_ACCOUNT_JSON`. Optional `GEMINI_MODEL`, `GOOGLE_SHEET_ID`. Keine Secrets in Repository, Logs oder Artefakten.

Workflow wird manuell via `workflow_dispatch` oder zum Test auf `fix/**` per Push gestartet. Fixes ausschließlich auf temporärem Branch. Runner und echte Sheet-Ergebnisse müssen erfolgreich sein, ehe Squash-Merge erfolgen darf. Bei externen Sperren nicht mergen.

Run #1 (2026-10-28): HTML-Extraktion 20/20 erfolgreich; Gemini 0/20 mit HTTPError. Ursache anhand bisheriger Logs nicht entscheidbar, weil HTTP-Status nicht protokolliert wurde. Diagnose und Schutz gegen Schreiben vollständig fehlgeschlagener Klassifizierungen ergänzt.
