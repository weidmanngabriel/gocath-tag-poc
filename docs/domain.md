# Fachregeln

- Das kontrollierte Standard-Tag-Vokabular ist im Google Sheet `Tags` konfigurierbar (Tag, aktiviert, kommagetrennte Synonyme). `src/tags.py` stellt nur ein Fallback-Vokabular bereit, wenn keine aktivierten Sheet-Tags gelesen werden.
- Die KI darf ausschließlich aktivierte Standard-Tags auswählen. Optional kann sie zusätzliche freie Suchbegriffe liefern; deren Aktivierung und Obergrenze werden in `Config` gesteuert und vom Runner technisch begrenzt. Zusätzliche Begriffe werden nicht automatisch zu Standard-Tags.
- Synonyme unterstützen die Interpretation der Standard-Tags. Wird ein Standard-Tag gewählt, entfernt der Runner dessen Synonyme aus den zusätzlich generierten Tags. Synonyme werden nur als Suchbegriffe des gewählten Tags berücksichtigt.
- Keine nicht belegten Zusatzangebote aus Gewohnheit behaupten (z. B. Beichte bei jeder Messe).
- Event-URL dient als stabiler Schlüssel der aktuellen Ansicht; `ResultsHistory` bewahrt die Ergebnisse je Run-ID auf.
- Nur öffentlich verfügbare Veranstaltungsinformationen verarbeiten; eine kurze Begründung zu den Tags speichern.
