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

## Kalibrierung aus Live-Lauf 26
- Der echte Live-Lauf 26 hat zehn Events mit je 23 Einzelbewertungen erfolgreich in `ClassificationDetails` gespeichert. Er hat auch gezeigt, dass ein Fußballturnier trotz kaum religiöser Inhalte durch ein übergewichtiges Herkunftssignal als `likely_relevant` erschien.
- Deshalb wurden die Gewichte für `context_catholic` und `context_church` im Sheet `Criteria` auf jeweils `0.5` gesenkt und die Beschreibungen präzisiert: Der Quellen-Domainname allein ist kein Beleg für einen ausdrücklich kirchlichen Veranstalter. Diese Werte bleiben im Sheet frei editierbar.
- Historische Bewertungen aus Lauf 26 bleiben als damalige Entscheidungen unverändert; die geänderten Gewichte wirken erst auf folgende Klassifizierungsläufe. Ohne weitere Evaluation ist der Score keine belastbare Entscheidung über Aufnahme oder Ausschluss.

## OpenAI Decisions API (neuer Anbieterpfad)
- `classifier_provider=openai` nutzt `src/decisions_classify.py`: eine gemeinsame JSON-Eingabe und eine benannte `predicate`-Frage je aktiviertem Kriterium. Die API liefert `probability` im Bereich 0 bis 1 pro Merkmal; die Werte sind Schätzungen, vor automatischer Aussortierung anhand markierter Beispiele zu kalibrieren. Die andere Relevanzregel im Python-Runner bleibt unverändert.
- Fehlen Antworten, kommen doppelte IDs, ungültige Werte oder Verweigerungen zurück, schlägt der Lauf ausdrücklich fehl, statt fehlende Merkmale als Nullbewertungen zu speichern.
- Kein freier Text und keine belegenden Zitate aus der Decisions API. `evidence` bleibt daher leer, `additional_tags` bleibt leer, `reason` ist ein fester Hinweis. Legacy-Tags werden aus expliziten Format-Aliasnamen abgeleitet, sofern sie in `Tags` erlaubt sind. Keine zusätzlichen Responses-Aufrufe für Text.
- Scores aller Veranstaltungen, auch bei geringer Relevanz, landen unverändert in `ClassificationDetails`; ältere Läufe bleiben unverändert.

## Fragebogenschema und Antwortverteilungen
- `Criteria` ergänzt zu den bisherigen Spalten `question_type` (leer entspricht `predicate`) und `answer_options_json` als JSON-Liste. Bei `choice` bestehen Optionen aus `{value,description}`, bei `score` Stufen aus `{label,description}`. Die Beschreibung erläutert, unter welchen Bedingungen die Antwort gewählt werden soll. Die Reihenfolge der Stufen für `score` ist aufsteigend.
- OpenAI Decisions liefert für `choice` sowohl die gewählte Antwort als auch die komplette Verteilung `probabilities` aller Optionen und separate `confidence`. Bei `score` liefert es den gewichteten Mittelwert des Stufenindex, die komplette Verteilung und `confidence`. Der Runner prüft Anzahl, Identität, Wertebereich und Summe der Antwortwahrscheinlichkeiten; unvollständige Verteilungen führen zu einem Fehler statt stillem Datenverlust.
- `ClassificationDetails` speichert jede Antwort mit `question_type` und `answer_json` zusätzlich zu den vorhandenen Feldern. Legacy-Score-Spalte: bei `choice` die Wahrscheinlichkeit der ausgewählten Antwort, bei `score` der normierte Mittelwert; die vollständige Verteilung ist ausschließlich `answer_json` zu entnehmen.
- **Wichtig:** Auswahlalternativen einer `choice`-Frage konkurrieren, ihre Wahrscheinlichkeiten ergeben zusammen ungefähr 1. Mehrere zugleich zutreffende Eigenschaften besser als unabhängige `predicate`-Fragen modellieren. Nur `predicate` darf aktuell ein positives Relevanzgewicht haben. Es werden keine Veranstaltungen ausgeschlossen.

## Format-Klassifizierung ohne Auffangoption „Sonstiges“
- Die bisherige Frage `format_primary_choice` wurde im Sheet `Criteria` **deaktiviert**, nicht gelöscht, damit historische Runs vollständig und unverändert bleiben. Ihr Ergebnis war eine relative Einzelauswahl-Verteilung; eine hohe Wahrscheinlichkeit für „sonstiges“ bedeutet ausdrücklich **nicht**, dass ein Veranstaltungsformat mit 98 % Sicherheit zutrifft.
- Formate werden zukünftig unabhängig durch `predicate`-Fragen beurteilt; neben den vorhandenen acht Formatfragen gibt es nun `format_freizeit_sport`. Damit können **alle** Formatwerte gleichzeitig niedrig sein, wenn keines ausreichend durch die Veranstaltungsdaten gestützt ist. Formate können auch gleichzeitig hohe Werte haben.
- Deaktivierte frühere Einzelauswahlfragen werden nicht mehr als aktuelle Hauptformat-Chips in der Ergebnisübersicht gezeigt. In historischen Details bleiben sie als deaktivierte frühere Auswahl einsehbar.
- Die Änderung wirkt auf **neue** Klassifizierungsläufe. Historische Klassifizierungen werden weder überschrieben noch neu bewertet. Der Relevanzstatus ist weiterhin unabhängig aus den dafür gewichteten Merkmalen abgeleitet.
