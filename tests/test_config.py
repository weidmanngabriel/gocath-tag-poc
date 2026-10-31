"""The active RC configuration depends only on Config and Criteria."""
import unittest
from unittest.mock import Mock, patch
from src.config import settings

class ConfigTests(unittest.TestCase):
    @patch("src.config.gspread.authorize")
    @patch("src.config.Credentials.from_service_account_info")
    def test_reads_no_historical_tabs(self, credentials, authorize):
        doc = Mock()
        authorize.return_value.open_by_key.return_value = doc
        def worksheet(name):
            if name == "Config":
                return Mock(get_all_values=lambda: [
                    ["key", "value"], ["rc_model", "gpt-6-luna"],
                    ["rc_input_per_million_usd", "0.10"]])
            if name == "Criteria":
                return Mock(get_all_values=lambda: [
                    ["id", "category", "label", "description", "active", "weight", "threshold"],
                    ["rc_test", "Format", "Test", "Testfrage", "true", "1", "0.65"]])
            raise AssertionError("Unexpected sheet: " + name)
        doc.worksheet.side_effect = worksheet
        _, config = settings('{"type":"service_account"}', "test-sheet")
        self.assertEqual(config["criteria"][0]["id"], "rc_test")
        self.assertEqual(config["rc_model"], "gpt-6-luna")
        self.assertEqual(doc.worksheet.call_count, 2)

if __name__ == "__main__":
    unittest.main()
