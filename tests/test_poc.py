import unittest
from src.scrape import event_links, parse_event
from src.classify import clean

class TestPOC(unittest.TestCase):
    def test_links(self):
        markup = '<a href="/de/event/first">First</a><a href="/de/event/first">Again</a><a href="/de/event/second">Second</a>'
        self.assertEqual(len(event_links(markup, 20)), 2)
    def test_parse(self):
        self.assertEqual(parse_event("<main><h1>Abendgebet</h1><p>Gemeinsam beten</p></main>", "url")["title"], "Abendgebet")
    def test_tags(self):
        result = clean({"standard_tags": ["Gebet", "Fantasie"], "additional_tags": ["Taizé", "Taizé"], "reason": "Test"})
        self.assertEqual(result["standard_tags"], ["Gebet"])
        self.assertEqual(result["additional_tags"], ["Taizé"])
