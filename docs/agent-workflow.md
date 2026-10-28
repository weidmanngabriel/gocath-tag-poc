# Verbindlicher Agenten-Workflow

1. Vor der Implementierung Anforderungen, docs und aktuelle Runs/Logs prüfen.
2. Pro Änderung einen temporären Branch von `main` erstellen; `main` nie direkt beschreiben.
3. Tests und CI auf dem Branch ausführen; Github Actions **selbst** starten und auf Abschluss prüfen. Bei Fehlern: Logs lesen → Ursache fixen → erneut ausführen.
4. Integration gegen echte Veranstaltungen, Gemini und Google Sheets validieren. Prüfen, ob im Sheet erfolgreiche neue Tag-Zuordnungen vorliegen; reine Unit-Tests sind unzureichend.
5. Bei fehlenden Zugriffsrechten, Quota- oder Secret-Problemen keine Scheinlösungen und **kein Merge**. Klar dokumentieren, welche externe Maßnahme nötig ist.
6. Nach grünem Runner und fachlicher Prüfung einen PR **per Squash-Merge** in `main` übernehmen. Niemals Merge/Rebase-Merge oder Direktcommit.
7. Dokumentation und Entscheidungen aktuell halten; Branch aufräumen, soweit möglich.

## Abschlusskriterium: Dokumentation aktuell

8. **Jede Aufgabe umfasst eine Dokumentationsprüfung.** Geänderte Funktionen, Tabellen, Konfigurationsschlüssel, Workflows, Architektur, Einschränkungen und Betriebsanweisungen im selben Branch dokumentieren; veraltete Aussagen korrigieren. Dokumentation und Implementierung müssen beim Merge übereinstimmen.
9. **Konfigurierbare Werte nicht als feststehende Projektzahlen wiedergeben.** Auf `Config`, `Tags` oder den jeweiligen Code als Quelle verweisen, statt Beispielwerte zu kanonisieren. Beispiele ausdrücklich als Beispiele kennzeichnen.
10. Vor Abschluss prüfen, dass Einstiegspunkte (`README.md`, `AGENTS.md`) und vertiefende Dokumente konsistent sind. Im PR knapp angeben, welche Dokumentation aktualisiert wurde; falls nichts betroffen ist, begründen.
11. Nur verifizierte Zustände als erledigt dokumentieren. Fehlende Live-Tests, ausstehende Deployments und externe Blocker klar festhalten.
