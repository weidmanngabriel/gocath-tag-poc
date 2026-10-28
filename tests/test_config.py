import unittest
from unittest.mock import Mock,patch
from src.config import run_count

class ConfigTests(unittest.TestCase):
    def test_monthly_counter(self):
        from datetime import datetime,timezone
        month=datetime.now(timezone.utc).strftime("%Y-%m")
        doc=Mock()
        doc.worksheet.return_value.get_all_values.return_value=[["run_id","started_at","finished_at","status","events_classified"],["a",month+"-01T01:00Z","", "success","2"],["b","2020-01-01T00:00Z","","success","3"]]
        self.assertEqual(run_count(doc),2)
