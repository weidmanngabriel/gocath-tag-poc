# GoCath Tagging Dashboard – einfacher POC

- **Dashboard:** statisches TypeScript/Vite auf GitHub Pages, Google Identity Services OAuth im Browser.
- **Google Sheet:** bestehendes Dokument mit vier relevanten Tabs: `Config` (Schlüssel/Wert), `Tags` (Tag/aktiviert), `Runs` (fortlaufende Run-ID, Zeit und Status), `ResultsHistory` (Ergebnis jeder Veranstaltung je Run-ID). Das bisherige `Tabellenblatt1` dient weiter als letzte Ergebnisansicht.
- **Runner:** Python über GitHub Actions, nur manuell per `workflow_dispatch`; liest Einstellungen, zulässige Tags und Gemini-Prompt vor jedem Lauf aus dem Sheet. Datenquelle bleibt ausschließlich die öffentliche GoCath-Webseite.
- **Experiment:** Die Zahl verarbeiteter Veranstaltungen wird durch die Einstellungen in `Config` und die technischen Runner-Grenzen bestimmt. Wiederholte Läufe verarbeiten bei unveränderter Quellreihenfolge und deaktiviertem Änderungsfilter dieselben ersten Links. Es gibt bewusst keine starke Duplikatsperre oder produktive Konsistenzlogik. Für den Vergleich nutzt man `ResultsHistory` nach Run-ID.

## Konfiguration
Die Werte `max_events_per_run`, `monthly_limit`, `changed_only`, `additional_tags_enabled`, `gemini_prompt`, `gemini_model`, `gemini_temperature`, `max_additional_tags` liegen in `Config`. Prompt ist freier Text und wird mit der aktuellen Liste aktiver Tags und der JSON-Anweisung ergänzt. Die API-Schlüssel stehen **nicht** im Sheet.

Für den Vergleich verschiedener Parameter `changed_only=false` belassen. Durch `true` werden unveränderte Events übersprungen.

## OAuth & Hosting
1. Google Cloud Console → **OAuth client** vom Typ **Web application** erstellen; unter Authorized JavaScript origins `https://weidmanngabriel.github.io` hinterlegen.
2. Unter OAuth Consent Screen gegebenenfalls Testnutzer freischalten. Sheets-Berechtigungen werden für die gewünschten Nutzer individuell erteilt.
3. Im GitHub-Repository unter **Settings → Secrets and variables → Actions → Variables** die **öffentliche** Variable `VITE_GOOGLE_CLIENT_ID` setzen.
4. Unter **Settings → Pages** GitHub Actions als Quelle wählen. `Deploy dashboard to Pages` stellt `web/dist` bereit.
5. Dashboard öffnen: `https://weidmanngabriel.github.io/gocath-tag-poc/`. Bei Google anmelden und Konfiguration speichern.

Die Browser-Anwendung nutzt den Google Sheets OAuth Scope; der kurzlebige Zugriffs-Token wird für Reloads innerhalb desselben Browser-Tabs in sessionStorage gehalten und nach Ablauf verworfen. Kein Refresh-Token wird gespeichert. Nur Google-Accounts mit Sheet-Rechten können auf die Daten zugreifen. Die Pages-Seite selbst ist öffentlich erreichbar.

## Release
Auf temporärem Branch entwickeln, CI prüfen, Live-OAuth und Runner validieren, danach erst Squash-Merge auf main. Bei fehlender OAuth-Konfiguration kein vollständiger E2E-Nachweis.

### Pages-Branchschutz

Das `github-pages`-Environment gestattet nur `main` als Deployment-Branch. **Kein Preview-Deployment von Feature-Branches**. Stattdessen auf dem temporären Branch CI (`npm run build`, Python-Tests) ausführen, anschließend den geprüften PR per Squash auf `main` übernehmen und dort das automatisch ausgelöste Deployment prüfen. Erst auf der live veröffentlichten Seite kann die OAuth-/Sheets-Integration vollständig getestet werden. Die Deployment-Branch-Regel nicht umgehen.

## Gemini-Verbrauch und Kostenschätzung

Bei jeder erfolgreichen Gemini-Antwort liest der Runner `usageMetadata` (Input-/Output-/Thinking-/Gesamt-Tokens). Die Werte werden pro Veranstaltung in `ResultsHistory` und als Summe in `Runs` gespeichert. Das Dashboard zeigt beide Ebenen an. Alte Läufe haben diese Felder nicht und werden nicht rückwirkend geschätzt.

Die **Kosten sind keine echte Abrechnung**. Im Tabellenblatt `Config` sind `cost_input_per_million_usd` und `cost_output_per_million_usd` editierbar (USD je Million Tokens). Beide Felder leer lassen, wenn keine verlässlichen Modellpreise vorliegen; dann bleibt das Kostenfeld leer. Für einen Tarif die aktuellen Preise von https://ai.google.dev/gemini-api/docs/pricing übernehmen. Output-Preis umfasst bei Gemini auch Thinking-Tokens. Die Zahl berücksichtigt nicht zwingend Sondertarife, Caching, Fehlversuche oder Modell-Preflight-Aufrufe. Ob tatsächlich Kosten entstehen, hängt außerdem vom Google-Tarif ab. API-Schlüssel bleiben ausschließlich in GitHub Secrets.

## Google-Sitzung beim Neuladen

Ein einmal erteilter OAuth-Token wird mit Ablaufzeit im Tab-spezifischen `sessionStorage` zwischengespeichert, sodass ein Neuladen der Seite nicht sofort eine erneute Anmeldung erfordert. Nach Tokenablauf, nach Schließen des Tabs oder bei einer 401-Antwort ist eine neue Google-Autorisierung nötig. Bewusst keine dauerhafte Speicherung per `localStorage` und kein eigener Backend-Refresh-Service.

## Tag-Synonyme und Ergebnis-Suche

Das Tabellenblatt `Tags` enthält nun die dritte Spalte `synonyms` (Komma-getrennte Begriffe je Standard-Tag). Beispiel: `Heilige Messe` → `Hl. Messe, Gottesdienst`. In der Dashboard-Tag-Verwaltung lassen sich die Synonyme bearbeiten. Beim nächsten manuellen Klassifizierungslauf werden Synonyme in den Gemini-Systemprompt übernommen; der Runner entfernt redundant erzeugte freie Tags, wenn der zugehörige Standard-Tag ausgewählt ist.

Im Dashboard unter **Ergebnisse nach Run-ID** filtert das Suchfeld ausschließlich die gerade gewählte Run-ID. Durchsucht werden Veranstaltungstitel, Standard-Tags, freie Tags, Begründung und die Synonyme der tatsächlich gewählten Standard-Tags. Die Suche beginnt ab drei Zeichen je Suchwort und kombiniert Teilwortsuche (Contains) mit höchstens einem eingefügten, entfernten oder ersetzten Buchstaben gegenüber einem Wortabschnitt (Levenshtein-Distanz ≤ 1). So finden `Anbettung` und `nbet` den Tag `Anbetung`. Groß-/Kleinschreibung wird ignoriert. Mehrere Suchwörter müssen jeweils irgendwo in den durchsuchten Begriffen vorkommen. Nicht gefundene Veranstaltungen werden als möglicher Hinweis auf fehlende Tags oder Synonyme angezeigt. Die Suchfunktion ist clientseitig und verändert weder die gespeicherten Run-Ergebnisse noch die KI-Zuordnungen. Neue Synonyme lassen sich damit unmittelbar auch auf alten Läufen erproben.

## Klassifizierungsanbieter

Im Sheet `Config` wählt `classifier_provider` zwischen `groq` (Standard) und `gemini`. Das Dashboard stellt dafür ein Dropdown bereit. `groq` verwendet das Modell `openai/gpt-oss-20b` mit `GROQ_API_KEY` aus GitHub Secrets; `gemini` verwendet die vorhandene Gemini-Modellauswahl und den Key `GOCATH_GEMINI_CLASSIFIER_KEY`. Der manuelle Runner verwendet je Lauf ausschließlich den gewählten Anbieter; kein stiller Fallback. Standard-Tags, Synonyme und Promptregeln werden für beide Anbieter aus dem Sheet gelesen. Gemini-Preise im Sheet werden nicht auf Groq-Kosten übertragen; für Groq bleibt die Kostenschätzung leer. Das gewählte Modell wird in Runs/ResultsHistory dokumentiert.

### Groq Free-Tier-Drosselung

Bei `openai/gpt-oss-20b` kann trotz ausreichendem Anfragekontingent das Tokenlimit pro Minute erreicht werden (derzeit laut Kontolimit 8.000 TPM). Der reguläre Runner hält deshalb mindestens 15 Sekunden Abstand zwischen Starts von Groq-Anfragen. Bei HTTP 429 und temporären Serverfehlern wartet er zusätzlich begrenzt und wiederholt maximal viermal; wenn die individuellen Prompts mehr Tokens benötigen, kann das Limit dennoch erreicht werden. Das konkrete Kontingent kann sich ändern. Beim Benchmark-Modus wird absichtlich ohne Drosselung gemessen.

## Alternative Veranstaltungsquelle

Über `Config.event_source` und das Dashboard-Dropdown kann zwischen `gocath` (Standard; `https://gocath.org/de/finde`) und `regnum_christi` (`https://www.regnumchristi.eu/demnaechst/`) gewählt werden. Die gewählte Quelle wird beim nächsten manuellen Klassifizierungslauf abgerufen; dieselben Tag-Regeln und die aktive KI-Anbieterauswahl gelten für beide. Die Regnum-Christi-Seite verwendet Kalenderlinks mit `?vid=...`. Verändert sich deren HTML, muss der Parser aktualisiert werden; es gibt keinen stillen Wechsel zur GoCath-Quelle. Der Abruf ist lesend. Achtung: Regnum Christi kann im Kalender auch vergangene Termine anzeigen; die Korrektheit der Quelleninhalte und die Kalendersortierung müssen beim Live-Test geprüft werden.

**Parser-Korrektur:** Regnum-Christi-Termine werden aus den Kalendereinträgen der Übersichtsseite extrahiert, da die `vid`-URLs beim Abruf kein separat auswertbares Veranstaltungs-Markup lieferten. Kalenderinhalt und Datumsfilter müssen im Live-Test geprüft werden.
