# Legacy-Bereinigung

Stand 31.10.2026: Das ursprüngliche siebenblättrige Google Sheet ist vollständig als eigene Google-Drive-Kopie gesichert. Im Original verbleiben ausschließlich `Config` (RC-Modell und Kostensätze) und `Criteria` (aktiver Fragebogen).

Der produktive Workflow `.github/workflows/rc-catalog.yml` nutzt `src/rc_runtime.py`, `src/rc_import.py`, `src/decisions_classify.py` und `src/config.py`. Der alte Tagging-Workflow, der manuelle Runner, die historischen Provider- und Diagnosemodule sowie ihre ausschließlich dazugehörigen Tests wurden entfernt.

Das öffentliche `/rc/` bleibt unabhängig vom Google-Login. Der OAuth-basierte Editor der Startseite bearbeitet nur `Criteria`. Die alten Event-/History-Tabellen wurden ausschließlich aus dem Original-Sheet entfernt, nicht aus dem Backup.

Für Änderung des Fragebogens gilt: `delta` reagiert auf neue und geänderte Events; semantische Änderungen erfordern bewusstes `reclassify`. Der Modell- und Preisblock bleibt vorerst in `Config`, weil der RC-Workflow ihn während des Starts liest.
