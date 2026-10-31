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
3. **GitHub-Actions-Pipeline auf dem temporären Branch prüfen**: `.github/workflows/check.yml` startet automatisch bei Push auf `feature/**` sowie bei `pull_request`. Einen bereits ausgelösten passenden CI-Lauf verwenden und dessen Tests, Build und Logs kontrollieren; kein zusätzlicher manueller Start erforderlich. Push- und PR-Läufe desselben Quellbranches teilen eine Concurrency-Gruppe; neuere Runs brechen ältere ab. Abgebrochene Vorgänger nicht als CI-Fehler behandeln, sondern den letzten vollständigen Check für den aktuellen Commit prüfen. Fehlgeschlagene Runs eigenständig auswerten und auf demselben Branch nachbessern; erneut starten, bis die Pipeline erfolgreich ist.
4. Eine grüne Pipeline allein reicht bei Änderungen am Klassifizierungs- oder Datenfluss nicht: Auch tatsächlichen Ergebnisfluss (echte Events, Gemini-Klassifizierungen, Google-Sheet-Schreibzugriff) anhand von Logs und Ergebnisdaten validieren. Bei reinen UI-Änderungen ohne Änderung am Klassifizierungs- oder Datenfluss reichen eine erfolgreiche PR-CI (Tests und Dashboard-Build) sowie Codeprüfung; Live-OAuth-/Sheets-End-to-End-Tests sind dafür keine Merge-Voraussetzung. Bei reinen Dokumentationsänderungen bestehende Implementierung und Quellen prüfen; ein kostenpflichtiger Klassifizierungslauf ist dafür nicht nötig. Keine Fehler ignorieren oder durch Dummy-Daten kaschieren.
5. **Erst danach** PR erstellen bzw. fertigstellen und **ausschließlich per Squash-Merge** auf `main` übernehmen. Bei roten Checks oder unbelegter Integration nicht mergen.
6. Kann die Pipeline wegen fehlender GitHub-Rechte, externer Quoten oder fehlender Secrets nicht selbst gestartet oder erfolgreich validiert werden, Blocker dokumentieren und **nicht mergen**; niemals Erfolg behaupten.
7. Nach dem Merge den Branch bereinigen, soweit Berechtigungen dies zulassen. Details: [docs/agent-workflow.md](docs/agent-workflow.md).

## GitHub Pages: Nur main darf deployen
- Das GitHub-Environment `github-pages` erlaubt **nur** Deployments von `main`. Diese Einschränkung weder ändern noch umgehen.
- Auf Feature-/Fix-Branches ausschließlich Build und Tests durchführen. Fehlgeschlagene Pages-Deployments auf Nicht-main-Branches sind durch die Environment-Regel erklärbar.
- Geprüften Code per Squash-PR nach `main` übernehmen; danach das reale Pages-Deployment, Google OAuth und den Sheet-Zugriff validieren. Browser-E2E vor Veröffentlichung nicht behaupten. Bei Folgefehlern erneuten temporären Fix-Branch verwenden.

## Dokumentation ist Teil jeder Aufgabe (verbindlich)
- **Bei jeder Code-, Konfigurations-, Workflow- oder Architekturänderung gleichzeitig die betroffenen Dokumentationsstellen prüfen und aktualisieren.** Dokumentation ist Bestandteil der Definition of Done, kein optionaler Nachtrag.
- Dokumentiere neue Funktionen, Datenfelder, Schnittstellen, Betriebsabläufe, Einschränkungen und Entscheidungen dort, wo sie hingehören (README als Einstieg; docs/ für Details). Bestehende widersprüchliche oder überholte Aussagen im selben PR korrigieren.
- Beschreibe konfigurierbare Werte und Laufgrenzen **als Konfiguration**, nicht als starre Zahlen. Verweise auf die maßgebliche Quelle (z. B. `Config` im Google Sheet, `Tags` für die Tag-Liste). Nur stabile technische Grenzen aus dem Code dürfen ausdrücklich als solche benannt werden.
- Nach jeder Aufgabe prüfen, ob `AGENTS.md`, `README.md`, `docs/concept.md`, `docs/architecture.md`, `docs/domain.md`, `docs/development.md`, `docs/dashboard.md`, `docs/setup.md` oder `docs/agent-workflow.md` betroffen sind. Unveränderte Dokumente müssen nicht künstlich bearbeitet werden.
- Änderungen und Dokumentationsupdates in **demselben Feature-/Fix-Branch und PR** committen. Vor Merge auf widerspruchsfreie, aktuelle Angaben prüfen; bei nicht verifizierten Aussagen Unsicherheit transparent benennen.
- Keine Secrets, personenbezogenen Zugangsdaten, temporären Token oder vertraulichen Logs dokumentieren.

## Eigenständig bis zum Abschluss arbeiten (kein Pingpong)
- **GitHub-Checks und PRs eigenständig abwickeln:** Nach einem Code-Fix die zugehörigen GitHub-Actions-Runs und Job-Logs selbst abrufen, den letzten vollständigen CI-Lauf für den aktuellen Commit prüfen und Fehler eigenständig beheben. Sind die vorgeschriebenen Prüfungen erfolgreich und keine kritischen oder ungeprüften Auswirkungen vorhanden, den Pull Request ohne zusätzliche Aufforderung selbst per Squash-Merge in `main` zusammenführen. Den Nutzer nicht auffordern, einen erfolgreichen Check zu melden, Logs zu schicken oder selbst den Merge-Button zu drücken. Merge-Erfolg und gegebenenfalls weiterhin offene Live-Prüfungen klar berichten.
- **Standard: selbst erledigen statt Aufgaben an den Nutzer zurückgeben.** Vorhandene GitHub-, CI-, Google-Sheets- und andere autorisierte Werkzeuge aktiv verwenden, um Implementierung, Tests, Fehlerbehebung, Dokumentation und zulässige Integrationsprüfungen eigenständig abzuschließen.
- **Keine unnötigen Rückfragen oder Zwischenfreigaben.** Bereits bekannte Projektangaben nicht erneut erfragen. Keine bloßen Statusmeldungen als Abschluss ausgeben und den Nutzer nicht auffordern, selbst CI-Checks, Logs oder erreichbare Daten zu prüfen.
- **Bis zum belastbaren Endzustand weiterarbeiten:** Änderungen umsetzen, passende Tests hinzufügen, CI-Logs auswerten, Fehler beheben, Ergebnisdaten kontrollieren und den in diesem Dokument vorgeschriebenen PR-/Squash-Merge-Prozess eigenständig durchführen, sofern alle Voraussetzungen belegt sind.
- **Bei echten Blockern exakt sagen, was der Nutzer tun muss:** konkrete Oberfläche/URL, präzise Aktion, warum nur der Nutzer sie ausführen kann und welches Ergebnis anschließend vorliegen soll. Keine vagen Anweisungen wie „bitte prüfen“ oder „Testlauf machen“.
- **Nicht auf Verdacht abschließen oder mergen:** fehlende Zugriffsrechte, Secrets, kostenpflichtige API-Aktionen, externe Limits oder nicht durchführbare Browser-/Live-Tests offen als Blocker benennen. CI-Erfolg nicht als bestandenen End-to-End-Test darstellen.
- **Keine asynchronen Versprechen:** Arbeit innerhalb der aktiven Bearbeitung durchführen; falls eine externe Prüfung noch läuft und nicht abgeschlossen werden kann, den genauen offenen Zustand und die nächste erforderliche Aktion nennen, statt spätere eigenständige Nachlieferung zu versprechen.
