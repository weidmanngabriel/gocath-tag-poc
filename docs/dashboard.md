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
Auf temporärem Branch entwickeln und die automatisch per `pull_request` beziehungsweise Push auf `feature/**` ausgelöste CI prüfen. Bei reinen UI-Änderungen ohne Eingriff in den Klassifizierungs- oder Datenfluss genügen grüne Tests, Dashboard-Build und Codeprüfung für den Squash-Merge; Live-OAuth- und Runner-Tests sind dafür nicht verpflichtend. Bei Änderungen am Klassifizierungs- oder Datenfluss bleibt die Integrationsprüfung Pflicht. Bei fehlender OAuth-Konfiguration kein vollständiger E2E-Nachweis.

### Pages-Branchschutz

Das `github-pages`-Environment gestattet nur `main` als Deployment-Branch. **Kein Preview-Deployment von Feature-Branches**. Stattdessen auf dem temporären Branch CI (`npm run build`, Python-Tests) ausführen, anschließend den geprüften PR per Squash auf `main` übernehmen und dort das automatisch ausgelöste Deployment prüfen. Erst auf der live veröffentlichten Seite kann die OAuth-/Sheets-Integration vollständig getestet werden. Die Deployment-Branch-Regel nicht umgehen.

## Gemini-Verbrauch und Kostenschätzung

Bei jeder erfolgreichen Gemini-Antwort liest der Runner `usageMetadata` (Input-/Output-/Thinking-/Gesamt-Tokens). Die Werte werden pro Veranstaltung in `ResultsHistory` und als Summe in `Runs` gespeichert. Das Dashboard zeigt beide Ebenen an. Alte Läufe haben diese Felder nicht und werden nicht rückwirkend geschätzt.

Die **Kosten sind keine echte Abrechnung**. Im Tabellenblatt `Config` sind `cost_input_per_million_usd` und `cost_output_per_million_usd` editierbar (USD je Million Tokens). Beide Felder leer lassen, wenn keine verlässlichen Modellpreise vorliegen; dann bleibt das Kostenfeld leer. Für einen Tarif die aktuellen Preise von https://ai.google.dev/gemini-api/docs/pricing übernehmen. Output-Preis umfasst bei Gemini auch Thinking-Tokens. Die Zahl berücksichtigt nicht zwingend Sondertarife, Caching, Fehlversuche oder Modell-Preflight-Aufrufe. Ob tatsächlich Kosten entstehen, hängt außerdem vom Google-Tarif ab. API-Schlüssel bleiben ausschließlich in GitHub Secrets.

## Google-Sitzung beim Neuladen

Ein einmal erteilter OAuth-Token wird mit Ablaufzeit im Tab-spezifischen `sessionStorage` zwischengespeichert, sodass ein Neuladen der Seite nicht sofort eine erneute Anmeldung erfordert. Nach Tokenablauf, nach Schließen des Tabs oder bei einer 401-Antwort ist eine neue Google-Autorisierung nötig. Bewusst keine dauerhafte Speicherung per `localStorage` und kein eigener Backend-Refresh-Service.

## Tag-Synonyme und Ergebnis-Suche

Das Tabellenblatt `Tags` enthält nun die dritte Spalte `synonyms` (Komma-getrennte Begriffe je Standard-Tag). Beispiel: `Heilige Messe` → `Hl. Messe, Gottesdienst`. In der Dashboard-Tag-Verwaltung lassen sich die Synonyme bearbeiten. Beim nächsten manuellen Klassifizierungslauf werden Synonyme in den Gemini-Systemprompt übernommen; der Runner entfernt redundant erzeugte freie Tags, wenn der zugehörige Standard-Tag ausgewählt ist.

Im Dashboard unter **Ergebnisse nach Run-ID** filtert das Suchfeld ausschließlich die gerade gewählte Run-ID. Durchsucht werden Veranstaltungstitel, Standard-Tags, freie Tags, Begründung und die Synonyme der tatsächlich gewählten Standard-Tags. Die Suche beginnt ab drei Zeichen je Suchwort. Für drei- und vierstellige Suchbegriffe gilt nur exakte Teilwortsuche (Contains), um häufige Fehltreffer wie `ehe` zu vermeiden. Ab fünf Zeichen ist zusätzlich höchstens ein eingefügter, entfernter oder ersetzter Buchstabe gegenüber einem Wortabschnitt erlaubt (Levenshtein-Distanz ≤ 1). So finden `Anbettung` und `nbet` den Tag `Anbetung`. Groß-/Kleinschreibung wird ignoriert. Mehrere Suchwörter müssen jeweils irgendwo in den durchsuchten Begriffen vorkommen. Nicht gefundene Veranstaltungen werden als möglicher Hinweis auf fehlende Tags oder Synonyme angezeigt. Die Suchfunktion ist clientseitig und verändert weder die gespeicherten Run-Ergebnisse noch die KI-Zuordnungen. Neue Synonyme lassen sich damit unmittelbar auch auf alten Läufen erproben.

## Klassifizierungsanbieter

Im Sheet `Config` wählt `classifier_provider` zwischen `groq` (Standard) und `gemini`. Das Dashboard stellt dafür ein Dropdown bereit. `groq` verwendet das Modell `openai/gpt-oss-20b` mit `GROQ_API_KEY` aus GitHub Secrets; `gemini` verwendet die vorhandene Gemini-Modellauswahl und den Key `GOCATH_GEMINI_CLASSIFIER_KEY`. Der manuelle Runner verwendet je Lauf ausschließlich den gewählten Anbieter; kein stiller Fallback. Standard-Tags, Synonyme und Promptregeln werden für beide Anbieter aus dem Sheet gelesen. Gemini-Preise im Sheet werden nicht auf Groq-Kosten übertragen; für Groq bleibt die Kostenschätzung leer. Das gewählte Modell wird in Runs/ResultsHistory dokumentiert.

### Groq Free-Tier-Drosselung

Bei `openai/gpt-oss-20b` kann trotz ausreichendem Anfragekontingent das Tokenlimit pro Minute erreicht werden (derzeit laut Kontolimit 8.000 TPM). Der reguläre Runner hält deshalb mindestens 15 Sekunden Abstand zwischen Starts von Groq-Anfragen. Bei HTTP 429 und temporären Serverfehlern wartet er zusätzlich begrenzt und wiederholt maximal viermal; wenn die individuellen Prompts mehr Tokens benötigen, kann das Limit dennoch erreicht werden. Das konkrete Kontingent kann sich ändern. Beim Benchmark-Modus wird absichtlich ohne Drosselung gemessen.

## Alternative Veranstaltungsquelle

Über `Config.event_source` und das Dashboard-Dropdown kann zwischen `gocath` (Standard; `https://gocath.org/de/finde`) und `regnum_christi` (`https://www.regnumchristi.eu/demnaechst/`) gewählt werden. Die gewählte Quelle wird beim nächsten manuellen Klassifizierungslauf abgerufen; dieselben Tag-Regeln und die aktive KI-Anbieterauswahl gelten für beide. Die Regnum-Christi-Seite verwendet Kalenderlinks mit `?vid=...`. Verändert sich deren HTML, muss der Parser aktualisiert werden; es gibt keinen stillen Wechsel zur GoCath-Quelle. Der Abruf ist lesend. Achtung: Regnum Christi kann im Kalender auch vergangene Termine anzeigen; die Korrektheit der Quelleninhalte und die Kalendersortierung müssen beim Live-Test geprüft werden.

**Parser-Korrektur:** Regnum-Christi-Termine werden aus den Kalendereinträgen der Übersichtsseite extrahiert, da die `vid`-URLs beim Abruf kein separat auswertbares Veranstaltungs-Markup lieferten. Kalenderinhalt und Datumsfilter müssen im Live-Test geprüft werden.

## Standard-Tags löschen und Tabs

Die Navigation teilt das Dashboard in **Konfiguration**, **Standard-Tags**, **Metriken**, **Ergebnisse** und **Läufe**. Alle Bereiche bleiben in derselben Ansicht; die Tabs wechseln nur den sichtbaren Bereich.

In **Standard-Tags** entfernt die Schaltfläche **Löschen** einen Eintrag zunächst nur aus dem Formular (nach Bestätigung). Erst **Tags speichern** übernimmt die verbleibende Liste in das Google Sheet `Tags` und leert die dadurch frei gewordenen alten Zeilen einschließlich der Synonyme. Vorheriges Neuladen verwirft ungespeicherte Löschungen. Mindestens ein Standard-Tag muss verbleiben. Die Löschung verändert historische Klassifizierungen nicht; neue Läufe verwenden die aktuelle aktive Tag-Liste aus dem Sheet.

## Mobile Darstellung der Konfiguration

Bei schmalen Ansichten (bis 760 px) erscheinen Eingaben und Dropdowns im Bereich **Konfiguration** unter der jeweiligen Beschriftung und nutzen die verfügbare Kartenbreite. Lange technische Schlüssel brechen um, statt das Layout horizontal zu erweitern. Desktop-Layouts bleiben unverändert.

## Mobile Ergebnisdarstellung

Die Ergebnisse eines ausgewählten Runs nutzen auf Smartphones die verfügbare Bildschirmbreite. Die Ergebnistabelle bleibt auch mobil eine Tabelle mit horizontaler Scrollmöglichkeit innerhalb der Karte. Die Tabellenzellen haben begrenzte Breiten und umbrechende Texte; Suchfeld und Tabellencontainer nutzen die volle verfügbare Kartenbreite. Die Suchfunktion und die Daten bleiben unverändert. Auf größeren Bildschirmen bleibt die Tabelle bestehen.

Mobil sind die ersten beiden Ergebnisspalten schmaler als bisher (Veranstaltung und Standard-Tags); weitere Tags und Begründung erhalten relativ mehr Platz in der horizontal scrollbar Tabelle.

## Begründungen im Dialog

In der Ergebnis-Tabelle zeigt die Spalte Begründung nur einen Button „Anzeigen“. Dieser öffnet einen Dialog mit der vollständigen KI-Begründung und einem Schließen-Button. Die zusätzlichen Tags erhalten dadurch mehr Tabellenbreite. Auf kleinen Displays bleibt die Tabelle horizontal scrollbar; Klassifizierung und gespeicherte Daten ändern sich nicht.

## Anbieterabhängige Konfigurationsfelder

Das Dropdown `classifier_provider` steuert die sichtbaren Einstellungen: Gemini-Modell nur bei Gemini, Temperatur bei Gemini und Groq, OpenAI Reasoning-Stufe nur bei OpenAI. Preisfelder erscheinen nur bei Anbietern, für die eine Kostenschätzung berechnet wird (Gemini und OpenAI). Gemeinsame Einstellungen und der bearbeitbare Klassifizierungs-Prompt gelten für alle Anbieter und bleiben sichtbar. Versteckte Felder bleiben beim Speichern unverändert im Sheet erhalten. Die technischen Schlüssel bleiben aus Kompatibilitätsgründen erhalten, obwohl die UI neutralere Bezeichnungen verwendet. Preisfelder sind derzeit anbieterübergreifend und müssen bei Anbieterwechsel kontrolliert werden.

Konfigurationswerte mit festen Auswahlmöglichkeiten werden als Dropdown dargestellt: Ja/Nein-Schalter (`changed_only`, `additional_tags_enabled`), Temperatur-Presets, Anzahl zusätzlicher Tags (0–8), Anbieter, Quelle und OpenAI-Reasoning. Beliebige Limits, Preise, Modellkennungen und der Klassifizierungs-Prompt bleiben Freitextfelder. Der OpenAI-Provider wurde im PR-Branch mit einer echten Veranstaltung erfolgreich gegen das Test-Sheet validiert (Run-ID 21, Modell `gpt-6-luna`).

## Kriterienbewertung und Ergebnisübersicht (PR #27)
- Im Tab `Kriterien` werden vorhandene Merkmalsbeschreibungen, Aktivierung, Gewichte und Anzeigeschwellen nach dem Verlassen eines Felds beziehungsweise sofort bei Checkbox-Auswahl direkt in `Criteria` gespeichert. Fehler werden angezeigt; es gibt keinen globalen Speichern-Button für diese Felder.
- `ClassificationDetails` speichert für jeden OpenAI-Lauf je Event **sämtliche** Kriterien-Scores, auch niedrige Werte. Keine Veranstaltung wird wegen geringer Relevanz herausgefiltert. Die Run-Ansicht zeigt pro Event den abgeleiteten Relevanzstatus und aufklappbar alle Einzelbewertungen.
- `ResultsHistory` und `Tabellenblatt1` behalten die Legacy-Tag-Felder; die neue Datenstruktur ergänzt sie. Kriterien sind aktuell nur mit OpenAI integriert, Gemini/Groq bleiben ohne neue Scores.
- Die neuen Kriterienbewertungen werden zunächst durch die Modellantwort geschätzt und per fest definierter Regel gewichtet. Die Ergebnisse sind nicht als kalibrierte Wahrscheinlichkeiten oder finale Eignungsentscheidung zu interpretieren.
- Bei Datenflussänderungen ist nach grüner CI ein echter Klassifizierungslauf von `feature/criteria-classification-dashboard` mit `mode=classify` nötig. Erwartet werden neue Zeilen in `Runs`, `ResultsHistory` und `ClassificationDetails`. Ein erfolgreicher Build allein reicht nicht. GitHub Pages wird erst von `main` veröffentlicht.
