import unittest
from src.rc_catalog import publish_questions, sync

class CatalogTests(unittest.TestCase):
    def test_publish(self):
        s={'events': {}}
        publish_questions(s, {'criteria': []})
        self.assertIn('revision', s['active_questionnaire'])

    def test_delta_and_manual_reclassification(self):
        from src.rc_catalog import sync,start_campaign
        event={"url":"https://www.regnumchristi.eu/demnaechst/?vid=12","title":"Gebet","description":"Gemeinsames Gebet"}
        state={"schema_version":1,"events":{}}
        publish_questions(state,{"criteria":[{"id":"prayer","weight":1}]})
        calls=[]
        def classify(e,c,u):
            calls.append(e["title"])
            u["input_tokens"]=100
            return {"criteria_scores":[{"id":"prayer","score":.9,"matched":True}]}
        sync(state,[event],classify)
        sync(state,[event],classify)
        self.assertEqual(len(calls),1)
        self.assertEqual(start_campaign(state),1)
        sync(state,[event],classify,mode="continue")
        self.assertEqual(len(calls),2)
        self.assertIsNone(state["campaign"])

    def test_failed_update_keeps_previous_classification(self):
        from src.rc_catalog import sync
        event={"url":"https://www.regnumchristi.eu/demnaechst/?vid=13","title":"Gebet","description":"Gebet"}
        state={"schema_version":1,"events":{}}
        publish_questions(state,{"criteria":[{"id":"prayer","weight":1}]})
        def ok(e,c,u):return {"criteria_scores":[{"id":"prayer","score":.9,"matched":True}]}
        sync(state,[event],ok)
        before=state["events"]["rc-13"]["classification"]
        def fail(e,c,u):raise RuntimeError("offline")
        changed=dict(event,description="Neue Details")
        result=sync(state,[changed],fail)
        self.assertEqual(len(result["failures"]),1)
        self.assertEqual(state["events"]["rc-13"]["classification"],before)

    def test_rc_html_fixture(self):
        from src.rc_import import parse_cards
        html='<section><a href="/demnaechst/?vid=123">Jugendgebetsabend</a><p>Gemeinsames Gebet und geistliches Leben mit Austausch in der Gemeinde und einer Feier für Jugendliche.</p><p>Adresse Wien Österreich</p></section>'
        result=parse_cards(html)
        self.assertIn("rc-123",result)

    def test_calendar_without_semantic_card_wrapper(self):
        from src.rc_import import parse_cards
        html = ('<div><a href="/demnaechst/?vid=33">Gebetsabend</a></div>'
                '<p>Gemeinsames Gebet am Freitag mit anschließendem geistlichen '
                'Austausch für Familien und Jugendliche.</p>'
                '<p>Adresse Kirche Berlin Deutschland</p>'
                '<div><a href="/demnaechst/?vid=34">Sommerfreizeit</a></div>'
                '<p>Eine Freizeit für Jugendliche mit Ausflügen und gemeinsamen '
                'Aktivitäten und Spielen.</p><p>Adresse Wien Österreich</p>')
        cards=parse_cards(html)
        self.assertEqual(set(cards), {"rc-33","rc-34"})
        self.assertIn("geistlichen",cards["rc-33"]["description"])
        self.assertNotIn("Sommerfreizeit",cards["rc-33"]["description"])

    def test_multiday_event_start_and_end_dates(self):
        from src.rc_import import event_dates
        self.assertEqual(event_dates("03.11. - 07.11.2026 Jugendcamp"),("2026-11-03","2026-11-07"))
        self.assertEqual(event_dates("26.11. - 29.11.2026"),("2026-11-26","2026-11-29"))
        self.assertEqual(event_dates("29.12. - 03.01.2027"),("2026-12-29","2027-01-03"))
        self.assertEqual(event_dates("31.10.2026"),("2026-10-31",""))
        self.assertEqual(event_dates(""),("",""))
    def test_multiday_date_on_parsed_card(self):
        from src.rc_import import parse_cards
        html='<section><a href="/demnaechst/?vid=42">Wintercamp</a><p>03.11. - 07.11.2026</p><p>Ein aufregendes Camp mit gemeinsamen Veranstaltungen, Ausflügen und Gesprächen für Jugendliche.</p><p>Adresse München Deutschland</p></section>'
        event=parse_cards(html)["rc-42"]
        self.assertEqual(event["starts_at"],"2026-11-03")
        self.assertEqual(event["ends_at"],"2026-11-07")
