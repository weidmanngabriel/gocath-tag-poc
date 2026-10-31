# Konzept

GoCath testet die Suchqualität öffentlicher Veranstaltungen anhand kontrollierter Standard-Tags und optionaler zusätzlicher freier Suchbegriffe. Das System dient der manuellen Evaluation; es schreibt keine Tags in produktive GoCath-Systeme.

Die Anzahl zu klassifizierender Veranstaltungen je Lauf, monatliche Limits, die Verarbeitung unveränderter Veranstaltungen sowie Modell, Prompt und Tag-Regeln sind über das Google Sheet konfigurierbar. **Aktuelle Werte niemals aus diesem Dokument ableiten**, sondern aus `Config` und `Tags` lesen.

Jeder manuelle Lauf erhält eine Run-ID. Ergebnisse werden zur Qualitätsprüfung und zum Vergleich historisch im Test-Sheet gespeichert. Ein Dashboard ermöglicht die Auswahl eines Runs sowie die Suche über Tags und zugeordnete Synonyme.


## RC-Katalog: Versionierte, zustandsbasierte Klassifizierung
Der RC-Katalog verwendet je Veranstaltung ausschließlich die letzte erfolgreiche Klassifizierung. Die aktuelle Fragebogenkonfiguration wird bei jedem Workflow-Start aus Google Sheets geladen und für alle Chargen desselben Runs eingefroren. Die Konfiguration erhält einen Änderungszeitpunkt und zwei Fingerprints: die vollständige Anzeigeversion und die semantische Klassifizierungsversion.

`delta` klassifiziert neue oder inhaltlich geänderte Veranstaltungen, aber **nicht** allein wegen einer geänderten Fragebogenkonfiguration. `reclassify` klassifiziert nur Veranstaltungen, deren letzte Klassifizierung eine ältere semantische Konfigurationsversion hat oder deren Veranstaltungsinhalt geändert wurde. Bereits aktuelle Bewertungen werden übersprungen. Der manuelle Veröffentlichungsschritt sowie `continue` und kampagnenbasierte Warteschlangen entfallen. Die letzte erfolgreiche Bewertung bleibt bei Fehlern erhalten.

Die alte GoCath-Tagging-POC-Strecke mit Google-Sheet-`ResultsHistory` ist davon organisatorisch und technisch zu unterscheiden; für den RC-Katalog liegen der aktuelle Zustand und die aggregierten Laufmetriken dauerhaft im `rc-data`-Branch.
