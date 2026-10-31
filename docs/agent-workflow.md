# Verbindlicher Agenten-Workflow

1. Vor der Implementierung Anforderungen, docs und aktuelle Runs/Logs prüfen.
2. Pro Änderung einen temporären Branch von `main` erstellen; `main` nie direkt beschreiben.
3. Tests und CI auf dem Branch prüfen. `.github/workflows/check.yml` wird bei Push auf `feature/**` und bei `pull_request` automatisch ausgelöst. Bereits laufende PR-Checks verwenden, ihren Abschluss und Status prüfen; kein zusätzlicher manueller Start erforderlich. `check.yml` nutzt eine gemeinsame Concurrency-Gruppe pro Quellbranch für Push- und PR-Checks (`github.head_ref || github.ref_name`) und bricht ältere laufende Checks desselben Branches automatisch ab. Ein abgebrochener Vorgänger-Run ist kein Fehler; nur den letzten Lauf des aktuellen Commits für das Merge-Gate werten. Andere Branches und manuell gestartete Klassifizierungsläufe bleiben davon unberührt. Bei Fehlern: Logs lesen → Ursache fixen → erneut ausführen.
4. Prüfungen nach Änderungsart: Änderungen am Klassifizierungs- oder Datenfluss mit echten Veranstaltungen, KI-Klassifizierung und Google Sheets validieren; Unit-Tests allein reichen dafür nicht. Bei reinen UI-Änderungen ohne Änderung dieses Datenflusses genügen erfolgreiche PR-CI (Tests und Dashboard-Build) und Codeprüfung für den Merge. Live-OAuth- oder Sheets-End-to-End-Tests sind dann keine Pflicht.
5. Bei fehlenden Zugriffsrechten, Quota- oder Secret-Problemen keine Scheinlösungen und **kein Merge**. Klar dokumentieren, welche externe Maßnahme nötig ist.
6. Nach grünem Runner und fachlicher Prüfung einen PR **per Squash-Merge** in `main` übernehmen. Niemals Merge/Rebase-Merge oder Direktcommit.
7. Dokumentation und Entscheidungen aktuell halten; Branch aufräumen, soweit möglich.

## Abschlusskriterium: Dokumentation aktuell

8. **Jede Aufgabe umfasst eine Dokumentationsprüfung.** Geänderte Funktionen, Tabellen, Konfigurationsschlüssel, Workflows, Architektur, Einschränkungen und Betriebsanweisungen im selben Branch dokumentieren; veraltete Aussagen korrigieren. Dokumentation und Implementierung müssen beim Merge übereinstimmen.
9. **Konfigurierbare Werte nicht als feststehende Projektzahlen wiedergeben.** Auf `Config`, `Tags` oder den jeweiligen Code als Quelle verweisen, statt Beispielwerte zu kanonisieren. Beispiele ausdrücklich als Beispiele kennzeichnen.
10. Vor Abschluss prüfen, dass Einstiegspunkte (`README.md`, `AGENTS.md`) und vertiefende Dokumente konsistent sind. Im PR knapp angeben, welche Dokumentation aktualisiert wurde; falls nichts betroffen ist, begründen.
11. Nur verifizierte Zustände als erledigt dokumentieren. Fehlende Live-Tests, ausstehende Deployments und externe Blocker klar festhalten.
