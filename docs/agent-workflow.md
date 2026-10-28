# Verbindlicher Agenten-Workflow

1. Vor der Implementierung Anforderungen, docs und aktuelle Runs/Logs prüfen.
2. Pro Änderung einen temporären Branch von `main` erstellen; `main` nie direkt beschreiben.
3. Tests und CI auf dem Branch ausführen; Github Actions **selbst** starten und auf Abschluss prüfen. Bei Fehlern: Logs lesen → Ursache fixen → erneut ausführen.
4. Integration gegen echte Veranstaltungen, Gemini und Google Sheets validieren. Prüfen, ob im Sheet erfolgreiche neue Tag-Zuordnungen vorliegen; reine Unit-Tests sind unzureichend.
5. Bei fehlenden Zugriffsrechten, Quota- oder Secret-Problemen keine Scheinlösungen und **kein Merge**. Klar dokumentieren, welche externe Maßnahme nötig ist.
6. Nach grünem Runner und fachlicher Prüfung einen PR **per Squash-Merge** in `main` übernehmen. Niemals Merge/Rebase-Merge oder Direktcommit.
7. Dokumentation und Entscheidungen aktuell halten; Branch aufräumen, soweit möglich.
