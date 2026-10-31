# Fachregeln

- Das kontrollierte Standard-Tag-Vokabular ist im Google Sheet `Tags` konfigurierbar (Tag, aktiviert, kommagetrennte Synonyme). `src/tags.py` stellt nur ein Fallback-Vokabular bereit, wenn keine aktivierten Sheet-Tags gelesen werden.
- Die KI darf ausschließlich aktivierte Standard-Tags auswählen. Optional kann sie zusätzliche freie Suchbegriffe liefern; deren Aktivierung und Obergrenze werden in `Config` gesteuert und vom Runner technisch begrenzt. Zusätzliche Begriffe werden nicht automatisch zu Standard-Tags.
- Synonyme unterstützen die Interpretation der Standard-Tags. Wird ein Standard-Tag gewählt, entfernt der Runner dessen Synonyme aus den zusätzlich generierten Tags. Synonyme werden nur als Suchbegriffe des gewählten Tags berücksichtigt.
- Keine nicht belegten Zusatzangebote aus Gewohnheit behaupten (z. B. Beichte bei jeder Messe).
- Event-URL dient als stabiler Schlüssel der aktuellen Ansicht; `ResultsHistory` bewahrt die Ergebnisse je Run-ID auf.
- Nur öffentlich verfügbare Veranstaltungsinformationen verarbeiten; eine kurze Begründung zu den Tags speichern.

## Strukturierte Merkmale und Relevanz (PR #27)
- `Criteria` enthält die Merkmale `id`, `category`, `label`, `description`, `enabled`, `relevance_weight`, `display_threshold`. Aktivierte Merkmale werden von OpenAI für jedes Event einzeln auf 0–1 bewertet. Es handelt sich um unkalibrierte Modellwerte, nicht um statistisch geprüfte Wahrscheinlichkeiten.
- `ClassificationDetails` protokolliert auch Treffer unterhalb der Anzeigeschwelle append-only mit Run-ID, Event-URL, Merkmal, Score, Kontextbeleg und Relevanzstatus; kein Event wird dadurch ausgeschlossen.
- Relevanz entsteht ausschließlich aus Kriterien mit positivem Gewicht: ein starkes Signal (`score × weight ≥ 0,7`) oder mindestens zwei mittlere (`≥ 0,45`) ergeben `likely_relevant`; mindestens ein schwächeres Signal (`≥ 0,25`) ergibt `review`; sonst `likely_not_relevant`. Die Anzeigezahl ist das größte gewichtete Signal, begrenzt auf 1. Diese Schwellen stehen aktuell im Code und müssen vor produktiver Filterung empirisch geprüft werden.
- Zielgruppenmerkmale dürfen nicht automatisch geschlechtsspezifische Eignung voraussetzen. Kontext ist unabhängig von Inhalt; ein Sportangebot einer katholischen Jugendgruppe kann relevant sein.
- Die alten `Tags` bleiben vorerst für Abwärtskompatibilität bestehen. Bei Gemini und Groq lautet der neue Bewertungsstatus mangels Kriterienausgabe `not_evaluated`.
