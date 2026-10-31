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

    def test_refresh_updates_dates_without_ai(self):
        from src.rc_catalog import sync,public_feed
        state={"schema_version":1,"events":{}}
        publish_questions(state,{"criteria":[{"id":"prayer","weight":1}]})
        ev={"url":"https://www.regnumchristi.eu/demnaechst/?vid=52","title":"RC-Camp",
            "description":"Camp für Jugendliche","starts_at":"07.11.2026"}
        calls=[]
        def classify(e,c,u):
            calls.append(1)
            return {"criteria_scores":[{"id":"prayer","score":.7,"matched":True}]}
        sync(state,[ev],classify)
        before=state["events"]["rc-52"]["classification"]
        corrected=dict(ev,starts_at="2026-11-03",ends_at="2026-11-07")
        summary=sync(state,[corrected],classify,mode="refresh")
        self.assertEqual(summary["classified"],0)
        self.assertEqual(len(calls),1)
        self.assertEqual(state["events"]["rc-52"]["classification"],before)
        self.assertEqual(public_feed(state)["events"][0]["event"]["starts_at"],"2026-11-03")

    def test_decisions_invalid_response_fallback(self):
        from src import rc_runtime
        from unittest.mock import patch
        criteria=[{"id":str(i)} for i in range(5)]
        calls=[]
        def mock(event,key,config,usage):
            calls.append(len(config["criteria"]))
            if len(config["criteria"])==5:
                raise ValueError("Decisions response missing criterion answers")
            usage["input_tokens"]=100
            return {"criteria_scores":[{"id":c["id"],"score":.8,"matched":True} for c in config["criteria"]]}
        usage={}
        with patch.object(rc_runtime,"classify_decisions",side_effect=mock):
            result=rc_runtime.classify_with_fallback({}, "secret", {"criteria":criteria}, usage)
        self.assertEqual(calls,[5,3,2])
        self.assertEqual(len(result["criteria_scores"]),5)
        self.assertEqual(usage["input_tokens"],200)

    def test_decisions_configuration_error_is_not_retried(self):
        from src import rc_runtime
        from unittest.mock import patch
        with patch.object(rc_runtime,"classify_decisions",side_effect=ValueError("Criteria must have unique IDs")) as mock:
            with self.assertRaisesRegex(ValueError,"Criteria"):
                rc_runtime.classify_with_fallback({}, "secret", {"criteria":[{"id":"a"},{"id":"b"}]}, {})
        mock.assert_called_once()

    def test_public_feed_contains_published_questionnaire_snapshot(self):
        from src.rc_catalog import public_feed
        state={"schema_version":1,"events":{}}
        config={"criteria":[{"id":"format_test","label":"Testformat","category":"Format",
                    "description":"Findet das statt?","type":"predicate","threshold":0.6,"weight":1}]}
        publish_questions(state,config)
        config["criteria"][0]["description"]="Unpublished edit"
        public=public_feed(state)
        self.assertEqual(public["questionnaire"]["criteria"][0]["description"],"Findet das statt?")
        self.assertEqual(len(public["questionnaire"]["revision"]),64)
