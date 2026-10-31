"""Regression tests for safe, source-specific event text trimming."""
import unittest
from src.scrape import clean_event_text, parse_event

class EventTextCleanupTests(unittest.TestCase):
    def test_keeps_religious_content_organiser_location_and_dates(self):
        html = """<main><h1>Jugendmesse</h1><div>Google Maps kann aufgrund Deiner Datenschutzeinstellungen leider nicht angezeigt werden. Bitte akzeptiere die Cookies. Cookie akzeptieren</div>
        <p>So., 1. November 2026 19:00 Wo Pfarrkirche St. Peter Wer Katholische Jugend</p>
        <p>Heilige Messe mit anschließender Beichte und gemeinsamem Abendessen.</p>
        <div>Alle Angaben ohne Gewähr. Bitte prüfe Datum, Uhrzeit und Ort vor dem Besuch auf der offiziellen Veranstaltungsseite. Fehler melden</div>
        <section><h2>Ähnliche Veranstaltungen</h2><p>Yoga für alle am Montag</p></section></main>"""
        e = parse_event(html, "https://gocath.org/de/event/jugendmesse")
        for fact in ("Jugendmesse", "1. November 2026", "19:00",
                     "Pfarrkirche St. Peter", "Katholische Jugend", "Beichte", "Abendessen"):
            self.assertIn(fact, e["description"])
        for noise in ("Google Maps kann", "Cookie akzeptieren", "Alle Angaben ohne Gewähr",
                      "Ähnliche Veranstaltungen", "Yoga für alle"):
            self.assertNotIn(noise, e["description"])
        self.assertEqual(e["url"], "https://gocath.org/de/event/jugendmesse")

    def test_more_topics_stops_following_unrelated_articles(self):
        original = "Wer Pfarrei St. Peter Heilige Messe und Eucharistie. Mehr zum Thema Rosenkranz im Advent."
        self.assertEqual(clean_event_text(original), "Wer Pfarrei St. Peter Heilige Messe und Eucharistie.")

    def test_do_not_strip_liturgical_event_when_no_known_markers(self):
        original = "Vortrag über Kirchenmusik mit anschließendem Workshop. 7. November, 19 Uhr."
        self.assertEqual(clean_event_text(original), original)

    def test_preserves_full_event_text_when_no_related_section(self):
        original = "So., 1. November 2026 19:00 Wo Köln Wer Gemeinde Christliche Gemeinschaft und Gebet."
        self.assertEqual(clean_event_text(original), original)

if __name__ == "__main__":
    unittest.main()
