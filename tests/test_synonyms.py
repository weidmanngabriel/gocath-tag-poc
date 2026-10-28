import unittest
from src.classify import filter_duplicate_synonyms
class SynonymTests(unittest.TestCase):
    def test_filters_only_selected_tag_synonyms(self):
        result={"standard_tags":["Heilige Messe"],"additional_tags":["Gottesdienst","Jugendmesse","gottesdienst","Pilgerfahrt"]}
        cleaned=filter_duplicate_synonyms(result,{"Heilige Messe":["Gottesdienst","Hl. Messe"],"Wallfahrt":["Pilgerfahrt"]})
        self.assertEqual(cleaned["additional_tags"],["Jugendmesse","Pilgerfahrt"])
    def test_no_selected_tag_leaves_synonym(self):
        result={"standard_tags":[],"additional_tags":["Gottesdienst"]}
        self.assertEqual(filter_duplicate_synonyms(result,{"Heilige Messe":["Gottesdienst"]})["additional_tags"],["Gottesdienst"])
