# Konzept

GoCath testet die Suchqualität öffentlicher Veranstaltungen anhand kontrollierter Standard-Tags und optionaler zusätzlicher freier Suchbegriffe. Das System dient der manuellen Evaluation; es schreibt keine Tags in produktive GoCath-Systeme.

Die Anzahl zu klassifizierender Veranstaltungen je Lauf, monatliche Limits, die Verarbeitung unveränderter Veranstaltungen sowie Modell, Prompt und Tag-Regeln sind über das Google Sheet konfigurierbar. **Aktuelle Werte niemals aus diesem Dokument ableiten**, sondern aus `Config` und `Tags` lesen.

Jeder manuelle Lauf erhält eine Run-ID. Ergebnisse werden zur Qualitätsprüfung und zum Vergleich historisch im Test-Sheet gespeichert. Ein Dashboard ermöglicht die Auswahl eines Runs sowie die Suche über Tags und zugeordnete Synonyme.
