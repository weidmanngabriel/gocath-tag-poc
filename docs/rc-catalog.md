# Öffentlicher RC-Katalog – erster manueller Betrieb

Issue: #37. Dieser Workflow besitzt **absichtlich keinen stündlichen oder täglichen Trigger**.

## Datenfluss
- `src/rc_import.py` lädt den öffentlichen Kalender `regnumchristi.eu/demnaechst` einschließlich verlinkter Paginierung; ein plausibles Mindestmaß an Veranstaltungen wird vorausgesetzt.
- `src/rc_catalog.py` hält pro `vid` einen dauerhaften Datensatz mit zwei Hashes, klassifizierten Einzelscores, Kosten und aktiver Fragebogenversion.
- Die `rc-data`-Git-Branch speichert `catalog.json` (interner State) und `public.json` (öffentliche Daten). Der interne State enthält **keine API-Keys**.
- Das öffentliche Frontend liegt nach Pages-Deployment unter `/gocath-tag-poc/rc/` und liest `public.json` vom öffentlichen Datenbranch. Es benötigt keine Google-Anmeldung.

## Erstinitialisierung – ausschließlich manuell
1. Im Standardbranch den Workflow **RC Catalog** öffnen.
2. Erst den Modus `publish-questions` ausführen: Er veröffentlicht einen Snapshot des aktuellen Google-Sheet-Fragebogens als aktive Version. **Keine KI-Kosten.**
3. Danach `delta` mit konservativem Limit (z. B. `max_paid=10`) starten. Das klassifiziert nur fehlende oder inhaltlich veränderte Events. Folge-Runs setzen den Bestand fort.
4. Bei Änderungen am Fragebogen `publish-questions` auslösen. Das löst **keine Massenklassifizierung** aus; neue und inhaltlich geänderte Events nutzen den neuen Fragebogen.
5. Eine vollständige Neubewertung ist getrennt: `reclassify` und `confirm=YES`, mit Kostenlimit. Anschließend `continue` wiederholt ausführen, bis die Kampagne abgeschlossen ist.

## Sicherheit und Einschränkungen
- Kein Zeitplan aktiv. Der Katalog bleibt ohne manuelle Runs unverändert.
- Bei API-Fehlern bleiben bisherige Scores erhalten; die Klassifizierung wird im nächsten Delta-Lauf erneut versucht. Frühere Scores müssen bei geändertem Event als möglicherweise veraltet gelesen werden.
- Pro Lauf höchstens 100 kostenpflichtige KI-Anfragen; Standard 25.
- Änderungen an reinen Darstellungsfeldern erzeugen keinen neuen KI-Aufruf.
- Fehlt ein bereits bekannter Event dreimal bei vollständigen Abrufen, wird er als inaktiv markiert statt gelöscht.
- Der HTML-Importer ist abhängig vom Markup der fremden Website; vor aktivem stündlichem Betrieb sind Live-Erfassung, Pagination, Karteninhalte und Kosten zu prüfen.
- Der Workflow benötigt Repository-Einstellung `Actions: Read and write permissions`, damit er den Datenbranch anlegen und aktualisieren kann.
- GitHub Pages muss aus dem aktuellen `main` bauen. Die Datenbranch ist öffentlich; keine personenbezogenen oder geheimen Informationen hinzufügen.
- Die technische Erzeugung des Katalogs ist nicht gleichbedeutend mit redaktionell verifizierten Bewertungen.
