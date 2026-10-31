"""Regression tests for UTF-8 source decoding."""
import unittest
from unittest.mock import patch
from src import regnum_scrape

class Response:
    status_code = 200
    content = '<html><main><h1>Neuer Trägerinnenkreis in München</h1></main></html>'.encode("utf-8")
    def raise_for_status(self): pass

class Session:
    def get(self, *args, **kwargs): return Response()
    def close(self): pass

class EncodingTests(unittest.TestCase):
    def test_regnum_utf8(self):
        with patch.object(regnum_scrape.requests, "Session", return_value=Session()), patch.object(regnum_scrape, "event_links", return_value=["https://www.regnumchristi.eu/demnaechst/?vid=1"]):
            self.assertEqual(regnum_scrape.fetch_events(1)[0]["title"], "Neuer Trägerinnenkreis in München")

if __name__ == "__main__":
    unittest.main()
