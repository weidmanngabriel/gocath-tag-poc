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

Die Browser-Anwendung nutzt den Google Sheets OAuth Scope; der kurzlebige Zugriffs-Token wird für Reloads innerhalb desselben Browser-Tabs in `sessionStorage` gehalten. Bei ausdrücklichem Opt-in wird er bis zum Ablauf zusätzlich in `localStorage` für weitere Tabs und Deployments wiederverwendet. Kein Refresh-Token wird gespeichert. Nur Google-Accounts mit Sheet-Rechten können auf die Daten zugreifen. Die Pages-Seite selbst ist öffentlich erreichbar.

## Release
Auf temporärem Branch entwickeln und die automatisch per `pull_request` beziehungsweise Push auf `feature/**` ausgelöste CI prüfen. Bei reinen UI-Änderungen ohne Eingriff in den Klassifizierungs- oder Datenfluss genügen grüne Tests, Dashboard-Build und Codeprüfung für den Squash-Merge; Live-OAuth- und Runner-Tests sind dafür nicht verpflichtend. Bei Änderungen am Klassifizierungs- oder Datenfluss bleibt die Integrationsprüfung Pflicht. Bei fehlender OAuth-Konfiguration kein vollständiger E2E-Nachweis.

### Pages-Branchschutz

Das `github-pages`-Environment gestattet nur `main` als Deployment-Branch. **Kein Preview-Deployment von Feature-Branches**. Stattdessen auf dem temporären Branch CI (`npm run build`, Python-Tests) ausführen, anschließend den geprüften PR per Squash auf `main` übernehmen und dort das automatisch ausgelöste Deployment prüfen. Erst auf der live veröffentlichten Seite kann die OAuth-/Sheets-Integration vollständig getestet werden. Die Deployment-Branch-Regel nicht umgehen.

## Gemini-Verbrauch und Kostenschätzung

Bei jeder erfolgreichen Gemini-Antwort liest der Runner `usageMetadata` (Input-/Output-/Thinking-/Gesamt-Tokens). Die Werte werden pro Veranstaltung in `ResultsHistory` und als Summe in `Runs` gespeichert. Das Dashboard zeigt beide Ebenen an. Alte Läufe haben diese Felder nicht und werden nicht rückwirkend geschätzt.

Die **Kosten sind keine echte Abrechnung**. Im Tabellenblatt `Config` sind `cost_input_per_million_usd` und `cost_output_per_million_usd` editierbar (USD je Million Tokens). Beide Felder leer lassen, wenn keine verlässlichen Modellpreise vorliegen; dann bleibt das Kostenfeld leer. Für einen Tarif die aktuellen Preise von https://ai.google.dev/gemini-api/docs/pricing übernehmen. Output-Preis umfasst bei Gemini auch Thinking-Tokens. Die Zahl berücksichtigt nicht zwingend Sondertarife, Caching, Fehlversuche oder Modell-Preflight-Aufrufe. Ob tatsächlich Kosten entstehen, hängt außerdem vom Google-Tarif ab. API-Schlüssel bleiben ausschließlich in GitHub Secrets.

## Google-Sitzung beim Neuladen

Ohne Opt-in liegt der Google Access-Token ausschließlich im Tab-spezifischen `sessionStorage`. Wer auf dem Login-Bildschirm **„Für die Restlaufzeit des Google-Tokens auf diesem Gerät angemeldet bleiben“** markiert, speichert den vorhandenen, befristeten Token zusätzlich im `localStorage`. Er funktioniert dann auch in neuen Tabs und nach Pages-Deployments, sofern er noch gültig ist. Der Token ist für denselben OAuth-Client und Scope gebunden und wird bei Ablauf, ungültigen Daten, HTTP 401 oder per Button **„Auf diesem Gerät abmelden“** lokal entfernt. **Kein Refresh-Token und kein dauerhaftes Login:** Googles browserbasierter Token-Flow erfordert nach Ablauf erneut eine Nutzeraktion.

**Sicherheit:** `localStorage` kann von JavaScript mit derselben GitHub-Pages-Origin gelesen werden, einschließlich anderer Seiten unter `weidmanngabriel.github.io`. Da der Token Schreibzugriff auf das berechtigte Sheet bietet, die Option nur in einem vertrauenswürdigen Browser auf eigenem Gerät aktivieren. Für echte dauerhafte Anmeldung wäre ein eigener Backend-Code-Flow mit sicherem Refresh-Token-Speicher nötig. GitHub Pages allein kann dies nicht leisten.

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

Die Ergebnisansicht zeigt nun responsive Veranstaltungskarten statt einer breiten, horizontal scrollbar Tabelle. Filter für Run-ID, Relevanzstatus, nachgewiesene Treffer in einem Bereich sowie die bestehende Suche stehen oberhalb der Liste. Jede Veranstaltung hat eine aufklappbare Detailansicht; alle Einzelbewertungen werden alphabetisch nach Kategorie gruppiert und innerhalb der Kategorie nach Score absteigend sortiert. Niedrige Scores werden nicht versteckt; der Kategorie-Filter beeinflusst ausschließlich die Ergebnisliste und nicht den gespeicherten Datenbestand. Historische Läufe ohne Kriterienscores bleiben sichtbar und erscheinen als „Nicht bewertet“.


## Begründungen und Detailansicht

Die historische Begründung befindet sich jetzt im aufklappbaren Veranstaltungsdetail statt in einem separaten Dialog. Dort sind außerdem Legacy-Tags, ein Link zur Originalveranstaltung und sämtliche Kriterienscores einschließlich aller Decisions-Antwortverteilungen sichtbar.


## Anbieterabhängige Konfigurationsfelder

Das Dropdown `classifier_provider` steuert die sichtbaren Einstellungen: Gemini-Modell nur bei Gemini, Temperatur bei Gemini und Groq, OpenAI Reasoning-Stufe nur bei OpenAI. Preisfelder erscheinen nur bei Anbietern, für die eine Kostenschätzung berechnet wird (Gemini und OpenAI). Gemeinsame Einstellungen und der bearbeitbare Klassifizierungs-Prompt gelten für alle Anbieter und bleiben sichtbar. Versteckte Felder bleiben beim Speichern unverändert im Sheet erhalten. Die technischen Schlüssel bleiben aus Kompatibilitätsgründen erhalten, obwohl die UI neutralere Bezeichnungen verwendet. Preisfelder sind derzeit anbieterübergreifend und müssen bei Anbieterwechsel kontrolliert werden.

Konfigurationswerte mit festen Auswahlmöglichkeiten werden als Dropdown dargestellt: Ja/Nein-Schalter (`changed_only`, `additional_tags_enabled`), Temperatur-Presets, Anzahl zusätzlicher Tags (0–8), Anbieter, Quelle und OpenAI-Reasoning. Beliebige Limits, Preise, Modellkennungen und der Klassifizierungs-Prompt bleiben Freitextfelder. Der OpenAI-Provider wurde im PR-Branch mit einer echten Veranstaltung erfolgreich gegen das Test-Sheet validiert (Run-ID 21, Modell `gpt-6-luna`).

## Kriterienbewertung und Ergebnisübersicht (PR #27)
- Im Tab `Kriterien` werden vorhandene Merkmalsbeschreibungen, Aktivierung, Gewichte und Anzeigeschwellen nach dem Verlassen eines Felds beziehungsweise sofort bei Checkbox-Auswahl direkt in `Criteria` gespeichert. Fehler werden angezeigt; es gibt keinen globalen Speichern-Button für diese Felder.
- `ClassificationDetails` speichert für jeden OpenAI-Lauf je Event **sämtliche** Kriterien-Scores, auch niedrige Werte. Keine Veranstaltung wird wegen geringer Relevanz herausgefiltert. Die Run-Ansicht zeigt pro Event den abgeleiteten Relevanzstatus und aufklappbar alle Einzelbewertungen.
- `ResultsHistory` und `Tabellenblatt1` behalten die Legacy-Tag-Felder; die neue Datenstruktur ergänzt sie. Kriterien sind aktuell nur mit OpenAI integriert, Gemini/Groq bleiben ohne neue Scores.
- Die neuen Kriterienbewertungen werden zunächst durch die Modellantwort geschätzt und per fest definierter Regel gewichtet. Die Ergebnisse sind nicht als kalibrierte Wahrscheinlichkeiten oder finale Eignungsentscheidung zu interpretieren.
- Bei Datenflussänderungen ist nach grüner CI ein echter Klassifizierungslauf von `feature/criteria-classification-dashboard` mit `mode=classify` nötig. Erwartet werden neue Zeilen in `Runs`, `ResultsHistory` und `ClassificationDetails`. Ein erfolgreicher Build allein reicht nicht. GitHub Pages wird erst von `main` veröffentlicht.

## Entscheidungen statt Textgenerierung
OpenAI-Läufe verwenden jetzt die Decisions API. Der Ergebnis-Tab zeigt die Einzelwerte wie bisher; Freitext-Zusatzbegriffe und individuelle Textbegründungen sind bei diesen Läufen nicht verfügbar. Legacy-Tags werden begrenzt aus passenden Formatmerkmalen abgeleitet. Gemini und Groq funktionieren weiterhin wie zuvor. Die geschätzten OpenAI-Decisions-Kosten basieren auf Eingabetokens (derzeit 0,10 USD pro Million, Cache-Vorteile unberücksichtigt), nicht auf den alten frei konfigurierten Responses-Preisen. Nach dem CI-Build ist ein Live-Lauf notwendig, bevor diese Umstellung als produktiv geprüft gilt.

## Fragebogeneditor und Verteilungen
Im Tab **Kriterien** ersetzt ein Karteneditor die bisherige breite Kriterien-Tabelle. Fragen haben bearbeitbare Titel, Bereiche, Beschreibungen und die Typen `predicate`, `choice` und `score`. Für Auswahlfragen und Skalen wird je Antwort eine Regel über eine Zeile `Antwort | Wähle diese Antwort, wenn …` festgelegt. Neue Fragen lassen sich hinzufügen. Felder speichern auf Blur bzw. Change direkt in den bestehenden Sheet-Tab `Criteria`. `choice`/`score` verwenden Gewicht 0, da ihre Ergebnisse aktuell nicht direkt in den Relevanzstatus eingehen.

Im Ergebnisdetail zeigt das Dashboard für `choice` und `score` die komplette Antwortverteilung als beschriftete Balken sowie den gewählten Wert beziehungsweise Mittelwert und die separat gemeldete Konfidenz. `ClassificationDetails!N:O` enthält `question_type` und `answer_json`; alte Zeilen ohne diese Werte bleiben sichtbar. Alle Antwortmöglichkeiten einschließlich niedriger Wahrscheinlichkeiten bleiben gespeichert. Fehlende Wahrscheinlichkeitsverteilungen sind ein Klassifizierungsfehler, keine Einladung zum Weglassen.

## Gruppierter Fragebogen und Ergebnis-Karten

Die Kategorien aus `Criteria.category` erzeugen dynamisch eigene Untertabs. Tabs und Fragen werden mit deutscher Sortierung alphabetisch sortiert. Es werden **keine Zeilen im Google Sheet umsortiert**: Jedes Eingabefeld behält seine ursprüngliche reale Zeilennummer, sodass Autosave immer die richtige Frage aktualisiert. Neu hinzugefügte Fragen erscheinen nach erneutem Laden in ihrem jeweiligen Kategorie-Tab. Die Fragetypen werden in lesbaren Namen angezeigt, nicht nur als technische Metadaten.

Die Ergebnisansicht ersetzt die breite Tabelle durch Veranstaltungskarten mit Status, Relevanzwert und den wichtigsten nachgewiesenen Merkmalen. Eine zweite, aufklappbare Ebene zeigt alle Kriterien nach Kategorie und Score. Die Suche und Filter wirken nur auf die aktuelle Run-ID; alle Events bleiben im Sheet erhalten. Bei `choice` und `score` werden sämtliche Antwortwahrscheinlichkeiten weiterhin angezeigt.

## Auswahl ist kein positiver Treffer

`choice` und `score` sind typisierte Ergebnisse, keine binären Merkmalsnachweise. Die bisherige Darstellung (z. B. „Hauptformat: 98 %“ als grüner Treffer) war irreführend: 98 % ist die Modellwahrscheinlichkeit der gewählten Alternative (auch wenn diese „Sonstiges“ lautet), **keine** Relevanz des Formats und kein katholischer Relevanzbeitrag. Die Ergebnis-Karten zeigen jetzt ausdrücklich „Hauptformat: Sonstiges · 98 % Modellanteil“ als neutrale Auswahl. Nur `predicate`-Fragen zählen als Treffer; auch alte gespeicherte Zeilen mit `choice.matched=true` werden bei der Anzeige korrigiert, ohne historische Daten zu überschreiben. Die vollständige Auswahlverteilung bleibt unter „Alle Bewertungen“ sichtbar. Das künftig gespeicherte `matched`-Feld wird nur für `predicate` gesetzt. Die abgeleitete katholische Relevanz bleibt davon unabhängig.

## Bedeutung der Relevanzbewertung

Die Relevanzbewertung beschreibt ausschließlich, wie eindeutig die Veranstaltung aus ihrem Beschreibungstext als katholisch relevant eingeordnet und automatisch klassifiziert werden kann. Hohe Werte belegen keine hohe sprachliche oder werbliche Textqualität und erlauben keine Aussage über Attraktivität oder tatsächliche Teilnahme. Eine Bewertung der Textqualität wäre eine unabhängige Kennzahl.

## Klarstellung auf der öffentlichen RC-Seite

Auf `/rc/` steht oberhalb der Veranstaltungsfilter ein sichtbarer Hinweis, dass hohe Relevanz- und Kriterienwerte nur Hinweise für automatische katholische Relevanzeinordnung und Klassifizierung widerspiegeln. Es handelt sich nicht um eine Bewertung der sprachlichen oder werblichen Textqualität oder eine Prognose tatsächlicher Teilnahme. Die ausführlichere Erklärung steht außerdem unter „Mehr dazu erfahren“.

## Regnum-Christi-Katalog: Corporate Design
Die öffentlich erreichbare RC-Ansicht unter `/rc/` verwendet ausschließlich die Regnum-Christi-Kennzeichnung in Kopfzeile und Dokumenttitel. Die Oberflächenfarben orientieren sich am [offiziellen Regnum-Christi-Handbuch](https://regnumchristi.org/wp-content/uploads/2023/08/Manual-Identidad-Visual-Regnum-Christi_-version-junio-2019.pdf): institutionelles dunkles Rot (`#910803`) als Akzent, Weiß und neutrale Grautöne als Hauptflächen. Die Darstellung der Daten sowie Suche, Filter und Klassifizierung sind davon unabhängig. Die GoCath-Quellnamen, technischen Schnittstellen und das Haupt-Dashboard bleiben unverändert.

### RC-Logo und Fragebogen-Veröffentlichung
Im RC-Katalog wird die offizielle horizontale Regnum-Christi-Logo-Grafik von der RC-Brand-Center-Domain verwendet. Kann die externe Datei nicht geladen werden, erscheint der Textname. Der Tab „Bewertungskriterien“ zeigt die Revision und Zahl der aktiven Fragen des veröffentlichten Snapshots aus `rc-data/public.json`. `publish-questions` liest die aktiven Kriterien aus `Criteria`, protokolliert Revision und Anzahl und bricht bei einem leeren Fragenkatalog ab. Änderungen an den veröffentlichten Kriterien aktualisieren keine bereits bestehenden Klassifizierungsergebnisse; diese behalten ihre bisherige `questionnaire_revision` bis zur erneuten Klassifizierung. Die Fehlermeldung der Decisions-Antwortvalidierung nennt bei falschen Namen/Typen das konkrete Feld, ohne Veranstaltungsinhalte zu protokollieren.

### RC-Veranstaltungskarten: Treffer statt Gesamtrelevanz
Die öffentliche RC-Ansicht zeigt auf jeder Veranstaltungskarte **sämtliche** KI-Kriterien mit `matched=true` prominent an (also individuelle Predicate-Werte mindestens auf Höhe der veröffentlichten `display_threshold`). Es gibt keine Begrenzung auf vier Treffer. Die aggregierte Relevanzanzeige, der Relevanzfilter und die Sortierung nach Relevanz entfallen ausschließlich aus dem RC-Frontend. Nicht getroffene Kriterien und deren vollständige Einzelwerte bleiben im aufklappbaren Detail sichtbar. Bei fehlenden Treffern erscheint ein Hinweis. Die intern gespeicherte Relevanz und Klassifizierung für mögliche spätere Zulassungslogik bleiben unverändert. Neue Klassifizierungsfragen/Schwellenwerte wirken erst bei erneuter Klassifizierung auf bereits gespeicherte Treffer.

### RC-Treffergruppen und Farbgebung
Treffer werden nach `category` in Format, Thema, Zielgruppe, Kontext und gegebenenfalls weitere Bereiche gegliedert. Pro Bereich erscheinen zunächst die zwei höchsten Treffer; weitere Treffer lassen sich mit „+ N weitere“ öffnen. Die Detailansicht zeigt weiterhin alle Kriterien. Grün markiert Treffer ab 80 %, Gelb Treffer von der individuellen Schwelle bis unter 80 %, Rot Werte unterhalb ihrer individuellen Schwelle und Grau fehlende Werte. Das ist keine neue Gesamtbewertung und ändert keine Klassifizierung oder Grenzwerte im Sheet.

### Kompakte mobile RC-Trefferanzeige
Die bisherigen separaten Gruppenkarten werden als kompakte Zeilen mit schmaler Bereichsbeschriftung und flexiblen Treffer-Chips dargestellt. Pro Bereich erscheinen die beiden stärksten Treffer; `+N` blendet die übrigen Treffer direkt in derselben Zeile ein. Die Farben und Schwellenwerte bleiben unverändert. Die vollständigen Einzelbewertungen bleiben separat aufklappbar.
