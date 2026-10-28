# Einrichtung – GoCath Tagging Dashboard POC

## 1. Google Cloud OAuth-Webclient

- Öffne https://console.cloud.google.com/apis/credentials und wähle das Google Cloud Projekt mit der aktivierten Google Sheets API.
- Konfiguriere gegebenenfalls den Google Auth Platform OAuth-Zustimmungsbildschirm: Anzeigename, Support-E-Mail und bei externem Testbetrieb die Google-Accounts als **Test users**.
- Erstelle **Create credentials → OAuth client ID → Web application**.
- Unter **Authorized JavaScript origins** trage `https://weidmanngabriel.github.io` ein (ohne Pfad und ohne Slash am Ende).
- Kopiere **Client ID**. Ein Client-Secret gehört nicht in den Browser und wird hier nicht verwendet.
- Die Google-Accounts brauchen vom Eigentümer **Bearbeiterrechte** für https://docs.google.com/spreadsheets/d/1HRyxPjLz2-WUEelplO1YAaO7gCYDyU_77DgUqEtGQ1w/edit.
- Beim ersten Einloggen erscheint die Einwilligung für Sheets-Zugriff.

## 2. GitHub-Projekt vorbereiten

- Öffne https://github.com/weidmanngabriel/gocath-tag-poc/settings/variables/actions
- Lege eine **Repository variable** namens `VITE_GOOGLE_CLIENT_ID` mit dem Wert der Google OAuth Web-Client-ID an (kein Secret).
- Vorhandene GitHub **Actions secrets** `GOOGLE_SERVICE_ACCOUNT_JSON` und `GOCATH_GEMINI_CLASSIFIER_KEY` beibehalten.
- Öffne https://github.com/weidmanngabriel/gocath-tag-poc/settings/pages und wähle als Build and deployment source **GitHub Actions**.

## 3. Deployment

Nach validiertem Squash-Merge auf `main` GitHub Actions → **Deploy dashboard to Pages** → **Run workflow**. Alternativ wird die Aktion beim Push auf main automatisch zum **Deployment** ausgelöst; **nicht** die Klassifizierung.

Die Dashboard-URL ist https://weidmanngabriel.github.io/gocath-tag-poc/ . Im Dashboard **Mit Google anmelden** klicken. Konfigurationswert oder Tag ändern, speichern, Browser neu laden und Änderung prüfen.

## 4. Manuelle Klassifizierung

GitHub Actions → **GoCath Tagging POC** → **Run workflow**. Die Einstellungen werden direkt aus dem Sheet gelesen. Kein automatischer Klassifizierungstrigger.

Sheet-Tabs:
- `Config`: max_events_per_run (konfigurierbares Laufmaximum), monthly_limit, changed_only (für Vergleichsversuche `false`), additional_tags_enabled, gemini_prompt (mehrzeilig), gemini_model (leer = automatische Modellauswahl), gemini_temperature (0 bis 1), max_additional_tags (technisch begrenzt) sowie optionale USD-Preise pro Million Input-/Output-Tokens zur Kostenschätzung.
- `Tags`: Standard-Tags aktivieren/deaktivieren oder ergänzen; Synonyme kommagetrennt in der dritten Spalte verwalten.
- `Runs`: fortlaufende numerische Run-IDs, Metadaten, Token-Verbrauch und optionale geschätzte Kosten.
- `ResultsHistory`: Klassifizierungen einschließlich Tokenverbrauch bleiben für Run-Vergleich und Ergebnis-Suche erhalten.
- `Tabellenblatt1`: jeweils aktuelle Ergebnisse pro Veranstaltung.

## Fehlerdiagnose

- **OAuth origin mismatch**: exakten GitHub Pages Origin in den Authorized JavaScript origins prüfen (nur Domain, kein Repository-Pfad).
- **403 in Sheets**: Google-Account als Bearbeiter zum Dokument einladen; Consent-Screen Testnutzer freigeben.
- **Im Dashboard fehlt der Login-Client**: `VITE_GOOGLE_CLIENT_ID` als GitHub **Variable** setzen und Pages-Workflow erneut ausführen.
- **Gemini-Fehler**: GitHub-Actions-Laufprotokoll prüfen; Modell-ID leer lassen, um erreichbare Flash-Modelle automatisch auszuwählen.

Das Dashboard selbst ist auf GitHub Pages öffentlich abrufbar; der Sheet-Inhalt erfordert Google-Authentifizierung mit entsprechenden Rechten. Der POC hat keinen Backend-Service und keine produktive Datenkonsistenzgarantie.

## Verbindliche GitHub-Pages-Deploymentregel

Das GitHub-Environment `github-pages` erlaubt **ausschließlich Deployments vom Branch `main`**. Dies ist eine beabsichtigte Repository-Einstellung und darf nicht zum Testen gelockert werden. Ein Deployment aus einem Feature- oder Fix-Branch scheitert bereits an der Environment-Regel; es ist kein Beweis für einen fehlerhaften Dashboard-Build.

**Ablauf:** Auf temporärem Branch TypeScript-Build und Python-Tests per CI prüfen → PR erstellen → per Squash nach `main` mergen → die Pages-Deployment-Pipeline auf `main` prüfen → Login und Google-Sheets-Zugriff live prüfen. Die Live-OAuth-Prüfung kann deshalb erst **nach** der ersten Veröffentlichung erfolgen. Probleme danach wieder auf einem separaten Branch korrigieren und per Squash übernehmen.
