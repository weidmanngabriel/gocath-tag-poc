import unittest
from src.rc_catalog import publish_questions, sync

class CatalogTests(unittest.TestCase):
    def test_publish(self):
        s={'events': {}}
        publish_questions(s, {'criteria': []})
        self.assertIn('revision', s['active_questionnaire'])
