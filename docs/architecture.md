# Architektur

## Datenfluss
Manuell gestarteter GitHub-Actions-Workflow (`workflow_dispatch`) → Python/requests/BeautifulSoup → öffentliche GoCath-Veranstaltungslinks und Detailseiten → gewählter KI-Anbieter (OpenAI, Gemini oder Groq) → kontrollierte Standard-Tags und optional zusätzliche freie Tags → Google Sheets API (Service Account) → Ergebnisartefakt.

Das Google Sheet ist der einzige externe Schreibort. Im Test-Sheet sind `Config` (Parameter und Kostenpreise), `Tags` (aktivierte Standard-Tags und Synonyme), `Runs` (Laufstatus und Token-/Kostensummen), `ResultsHistory` (historische Ergebnisse je Run) sowie `Criteria` (Merkmalskatalog), `ClassificationDetails` (vollständige Merkmalsbewertungen pro Event/Run) und `Tabellenblatt1` (aktuelle Ergebnisse) maßgeblich. Einstellungen und Mengenlimits werden aus `Config` gelesen, nicht aus der Dokumentation.

## Dashboard
Statische TypeScript/Vite-Seite auf GitHub Pages, mit Google Identity Services OAuth für direkten Zugriff auf das Google Sheet. Kurzlebige Access-Tokens werden standardmäßig tabbezogen in `sessionStorage` gehalten. Mit ausdrücklicher Auswahl „Auf diesem Gerät angemeldet bleiben“ wird derselbe Token zusätzlich bis zum Ablauf in `localStorage` gespeichert, um ihn nach Deployment und Tabwechsel im selben Browser wiederzuverwenden. Es gibt keinen Refresh-Token; nach Ablauf ist erneut eine Nutzeraktion erforderlich. Das Dashboard bearbeitet mit Feld-Autosave Konfiguration, Kriterien, Tag-Aktivierung und Synonyme und zeigt Run-Ergebnisse und Gemini-Nutzungsmetriken. Die clientseitige Run-Suche arbeitet ab einer Mindestlänge mit Contains und maximal einem Zeichenfehler pro Wortabschnitt und berücksichtigt Synonyme tatsächlich gewählter Tags; Details: [dashboard.md](dashboard.md).

Es gibt keinen eigenen Backend-Service und keine automatische Klassifizierung. HTML-Änderungen der öffentlichen Quellseiten oder externe API-Quoten können Testläufe beeinträchtigen. Keine externe Webrecherche und keine produktiven GoCath-Schreibzugriffe.

## Decisions API
Bei OpenAI ruft der Runner die Decisions API `POST /v1/decisions` (Modell `gpt-6-luna`) statt der Responses API auf. Ein Request enthält sämtliche aktivierten Kriterien aus `Criteria` als benannte `predicate`-Fragen und die Veranstaltungsdaten als `input_json`. Der Rückgabewert `answers[].probability` wird vollständig in `ClassificationDetails` gespeichert. Die bestehende gewichtete Relevanzberechnung im Python-Code bleibt unabhängig vom Modell. Die API generiert keine Freitext-Suchbegriffe; `additional_tags` wird nicht mehr für neue OpenAI-Läufe befüllt. Die anderen Anbieter bleiben unverändert.

## Konfigurierbarer Decisions-Fragebogen
Der Sheet-Tab `Criteria` speichert die editierbare Fragedefinition einschließlich Fragetyp und JSON-Optionen. Die statische Web-App bearbeitet diese Werte direkt über die Sheets-API. `src/config.py` lädt sie vor jedem manuellen Runner-Lauf, `src/decisions_classify.py` erzeugt typisierte Fragen und prüft vollständig die gelieferten Verteilungen. Das Append-only-Log `ClassificationDetails` ergänzt die bislang 13 Felder um den Fragetyp und die typisierte Antwort als JSON. Nur `predicate` wirkt auf die bestehende Relevanzheuristik.
