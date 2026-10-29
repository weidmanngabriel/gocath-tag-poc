import unittest
from src.regnum_scrape import event_links, parse_event

class RegnumSourceTests(unittest.TestCase):
    def test_extracts_only_regnum_event_links(self):
        html = '<a href="/demnaechst/?vid=37995">Pauluscamp</a><a href="/demnaechst/?vid=37995">same</a><a href="https://example.com/?vid=3">external</a>'
        self.assertEqual(event_links(html),["https://www.regnumchristi.eu/demnaechst/?vid=37995"])

    def test_extracts_title_and_event_description(self):
        html = '<h1>DEMNÄCHST</h1><article><h2>Termin</h2><a href="/demnaechst/?vid=42">Einkehrtag</a><p>Ein Einkehrtag für Familien mit Gebet und Austausch in Berlin.</p></article>'
        event = parse_event(html,"https://www.regnumchristi.eu/demnaechst/?vid=42")
        self.assertEqual(event["title"],"Einkehrtag")
        self.assertIn("Einkehrtag",event["description"])

if __name__=="__main__": unittest.main()
