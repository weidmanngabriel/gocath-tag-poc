# GoCath Tagging POC — Coding-Agent-Einstieg

## Grenzen
- Öffentliche GoCath-Veranstaltungen lesen; keine produktiven GoCath-Schreibzugriffe.
- Nur das vereinbarte Test-Google-Sheet beschreiben.
- Keine zusätzliche Webrecherche, keine erfundenen Veranstaltungen.
- API-Schlüssel und Service-Account-Zugangsdaten niemals ausgeben, committen oder als Artefakt hochladen.
- Vor Änderungen [Konzept](docs/concept.md), [Architektur](docs/architecture.md), [Fachregeln](docs/domain.md), [Entwicklung](docs/development.md), [Arbeitsablauf](docs/agent-workflow.md) beachten.
- Tests durchführen, technische Annahmen offen dokumentieren, relevante docs aktualisieren.

## Verbindlicher Branch-, Test- und Merge-Prozess
1. **Nie einen Fix direkt auf `main` entwickeln.** Immer einen temporären Branch (`fix/*` oder `feature/*`) von aktuellem `main` anlegen.
2. Ursache mithilfe von GitHub-Actions-Logs untersuchen; reproduzierbaren Fix mit Tests einchecken.
3. **GitHub-Actions-Pipeline auf dem temporären Branch selbst starten**, beobachten und Logs kontrollieren. Fehlgeschlagene Runs eigenständig auswerten und auf demselben Branch nachbessern; erneut starten, bis die Pipeline erfolgreich ist.
4. Eine grüne Pipeline allein reicht nicht: Auch tatsächlichen Ergebnisfluss (echte Events, Gemini-Klassifizierungen, Google-Sheet-Schreibzugriff) anhand von Logs und Ergebnisdaten validieren. Keine Fehler ignorieren oder durch Dummy-Daten kaschieren.
5. **Erst danach** PR erstellen bzw. fertigstellen und **ausschließlich per Squash-Merge** auf `main` übernehmen. Bei roten Checks oder unbelegter Integration nicht mergen.
6. Kann die Pipeline wegen fehlender GitHub-Rechte, externer Quoten oder fehlender Secrets nicht selbst gestartet oder erfolgreich validiert werden, Blocker dokumentieren und **nicht mergen**; niemals Erfolg behaupten.
7. Nach dem Merge den Branch bereinigen, soweit Berechtigungen dies zulassen. Details: [docs/agent-workflow.md](docs/agent-workflow.md).

## GitHub Pages: Nur main darf deployen
- Das GitHub-Environment `github-pages` erlaubt **nur** Deployments von `main`. Diese Einschränkung weder ändern noch umgehen.
- Auf Feature-/Fix-Branches ausschließlich Build und Tests durchführen. Fehlgeschlagene Pages-Deployments auf Nicht-main-Branches sind durch die Environment-Regel erklärbar.
- Geprüften Code per Squash-PR nach `main` übernehmen; danach das reale Pages-Deployment, Google OAuth und den Sheet-Zugriff validieren. Browser-E2E vor Veröffentlichung nicht behaupten. Bei Folgefehlern erneuten temporären Fix-Branch verwenden.
