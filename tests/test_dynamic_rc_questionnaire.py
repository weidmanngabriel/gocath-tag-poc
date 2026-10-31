import unittest
from src.rc_catalog import criterion_signature, presentation_scores, publish_questions

class DynamicQuestionnaireTests(unittest.TestCase):
    def setUp(self):
        self.question = {"id":"target_youth","category":"Zielgruppe","label":"Jugendliche","description":"Explizit an Jugendliche gerichtet","type":"predicate","threshold":0.65}
        self.revision = {"revision":"new", "criteria":[self.question]}
        self.classification = {"questionnaire_revision":"old","criterion_signatures":{"target_youth":criterion_signature(self.question)},
            "scores":[{"id":"target_youth","category":"Frühere Kategorie","label":"Alter Titel","score":0.72,"matched":False}]}

    def test_current_labels_and_thresholds_apply_without_rerun(self):
        result = presentation_scores(self.classification,self.revision)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["category"],"Zielgruppe")
        self.assertEqual(result[0]["label"],"Jugendliche")
        self.assertTrue(result[0]["matched"])
        self.assertFalse(self.classification["scores"][0]["matched"])

    def test_semantic_change_hides_stale_answer(self):
        changed={**self.question,"description":"Abweichende Zielgruppe"}
        self.assertEqual(presentation_scores(self.classification,{"revision":"next","criteria":[changed]}),[])

    def test_removed_question_is_hidden(self):
        self.assertEqual(presentation_scores(self.classification,{"revision":"next","criteria":[]}),[])

    def test_legacy_revisions_cannot_be_assumed_compatible(self):
        legacy={**self.classification}
        legacy.pop("criterion_signatures")
        self.assertEqual(presentation_scores(legacy,self.revision),[])

if __name__ == "__main__":
    unittest.main()
