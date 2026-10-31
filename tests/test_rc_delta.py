import unittest
from src.rc_delta import canonical_event, event_id, fingerprints, plan_delta


class RCDeltaTests(unittest.TestCase):
    def setUp(self):
        self.event = {
            "url": "https://www.regnumchristi.eu/demnaechst/?vid=38260",
            "title": "  Jugend-  Abend ",
            "description": "Gebet  und\nBegegnung",
            "target_groups": ["Jugend", "Familien"],
            "updated_at": "2026-10-31T09:01:02",
            "page_views": 324,
        }

    def test_content_normalization_and_timestamp_noise(self):
        first = fingerprints(self.event)
        changed = dict(self.event, updated_at="2026-11-01T10:02:00", page_views=328)
        changed["description"] = "Gebet und Begegnung"
        changed["target_groups"] = ["Familien", "Jugend"]
        self.assertEqual(first, fingerprints(changed))

    def test_classification_and_display_hash_independent(self):
        first = fingerprints(self.event)
        edited = dict(self.event, location="Wien")
        self.assertEqual(first["classification_hash"], fingerprints(edited)["classification_hash"])
        self.assertNotEqual(first["display_hash"], fingerprints(edited)["display_hash"])

    def test_changed_content_requires_classification(self):
        existing = {"rc-38260": dict(fingerprints(self.event), classification={"scores": []})}
        self.assertFalse(plan_delta([self.event], existing)[0]["classify"])
        edited = dict(self.event, description="Neue Veranstaltung")
        self.assertTrue(plan_delta([edited], existing)[0]["classify"])

    def test_questionnaire_changes_not_trigger(self):
        record = dict(fingerprints(self.event), classification={"scores": []}, questionnaire_version="old")
        planned = plan_delta([self.event], {"rc-38260": record})
        self.assertFalse(planned[0]["classify"])

    def test_stable_id_and_duplicates(self):
        self.assertEqual(event_id(self.event), "rc-38260")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            plan_delta([self.event, self.event], {})

    def test_event_requires_numeric_vid(self):
        with self.assertRaises(ValueError):
            event_id({"url": "https://example.org/?vid=12"})

    def test_new_event_requires_classification(self):
        self.assertTrue(plan_delta([self.event], {})[0]["classify"])


if __name__ == "__main__":
    unittest.main()
