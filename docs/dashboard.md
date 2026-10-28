# GoCath Tagging Dashboard – einfacher POC

- **Dashboard:** statisches TypeScript/Vite auf GitHub Pages, Google Identity Services OAuth im Browser.
- **Google Sheet:** bestehendes Dokument mit vier relevanten Tabs: `Config` (Schlüssel/Wert), `Tags` (Tag/aktiviert), `Runs` (fortlaufende Run-ID, Zeit und Status), `ResultsHistory` (Ergebnis jeder Veranstaltung je Run-ID). Das bisherige `Tabellenblatt1` dient weiter als letzte Ergebnisansicht.
- **Runner:** Python über GitHub Actions, nur manuell per `workflow_dispatch`; liest Einstellungen, zulässige Tags und Gemini-Prompt vor jedem Lauf aus dem Sheet. Datenquelle bleibt ausschließlich die öffentliche GoCath-Webseite.
- **Experiment:** Standardlimit 10 Veranstaltungen. Wiederholte Läufe verarbeiten dieselben ersten zehn Links der Seite, sofern die Reihenfolge unverändert bleibt. Es gibt bewusst keine starke Duplikatsperre oder produktive Konsistenzlogik. Für den Vergleich nutzt man `ResultsHistory` nach Run-ID.

## Konfiguration
Die Werte `max_events_per_run`, `monthly_limit`, `changed_only`, `additional_tags_enabled`, `gemini_prompt`, `gemini_model`, `gemini_temperature`, `max_additional_tags` liegen in `Config`. Prompt ist freier Text und wird mit der aktuellen Liste aktiver Tags und der JSON-Anweisung ergänzt. Die API-Schlüssel stehen **nicht** im Sheet.

Für den Vergleich verschiedener Parameter `changed_only=false` belassen. Durch `true` werden unveränderte Events übersprungen.

## OAuth & Hosting
1. Google Cloud Console → **OAuth client** vom Typ **Web application** erstellen; unter Authorized JavaScript origins `https://weidmanngabriel.github.io` hinterlegen.
2. Unter OAuth Consent Screen gegebenenfalls Testnutzer freischalten. Sheets-Berechtigungen werden für die gewünschten Nutzer individuell erteilt.
3. Im GitHub-Repository unter **Settings → Secrets and variables → Actions → Variables** die **öffentliche** Variable `VITE_GOOGLE_CLIENT_ID` setzen.
4. Unter **Settings → Pages** GitHub Actions als Quelle wählen. `Deploy dashboard to Pages` stellt `web/dist` bereit.
5. Dashboard öffnen: `https://weidmanngabriel.github.io/gocath-tag-poc/`. Bei Google anmelden und Konfiguration speichern.

Die Browser-Anwendung nutzt den Google Sheets OAuth Scope; der Zugriffs-Token wird ausschließlich im Arbeitsspeicher gehalten. Nur Google-Accounts mit Sheet-Rechten können auf die Daten zugreifen. Die Pages-Seite selbst ist öffentlich erreichbar.

## Release
Auf temporärem Branch entwickeln, CI prüfen, Live-OAuth und Runner validieren, danach erst Squash-Merge auf main. Bei fehlender OAuth-Konfiguration kein vollständiger E2E-Nachweis.
