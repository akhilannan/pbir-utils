import unittest
import os
import sys
from unittest.mock import patch, mock_open, MagicMock

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pbir_utils.filter_utils import (
    _format_date,
    _is_date,
    _is_number,
    _format_value,
    _create_condition,
    _validate_filters,
    update_report_filters,
    sort_report_filters
)

class TestFilterUtils(unittest.TestCase):

    def test_format_date(self):
        self.assertEqual(_format_date("01-Jan-2023"), "datetime'2023-01-01T00:00:00'")

    def test_is_date(self):
        self.assertTrue(_is_date("01-Jan-2023"))
        self.assertFalse(_is_date("2023-01-01"))
        self.assertFalse(_is_date(123))

    def test_is_number(self):
        self.assertTrue(_is_number(123))
        self.assertTrue(_is_number(123.45))
        self.assertFalse(_is_number("123"))

    def test_format_value(self):
        self.assertEqual(_format_value("01-Jan-2023"), "datetime'2023-01-01T00:00:00'")
        self.assertEqual(_format_value(123), "123L")
        self.assertEqual(_format_value("text"), "'text'")

    def test_create_condition_greater_than(self):
        condition = _create_condition("GreaterThan", "col", [10], "src")
        self.assertEqual(condition["Comparison"]["ComparisonKind"], 1)
        self.assertEqual(condition["Comparison"]["Right"]["Literal"]["Value"], "10L")

    def test_create_condition_between(self):
        condition = _create_condition("Between", "col", [10, 20], "src")
        self.assertIn("And", condition)
        self.assertEqual(condition["And"]["Left"]["Comparison"]["ComparisonKind"], 2) # GreaterThanOrEqual
        self.assertEqual(condition["And"]["Right"]["Comparison"]["ComparisonKind"], 4) # LessThanOrEqual

    def test_create_condition_in(self):
        condition = _create_condition("In", "col", ["a", "b"], "src")
        self.assertIn("In", condition)
        self.assertEqual(len(condition["In"]["Values"]), 2)

    def test_create_condition_contains(self):
        condition = _create_condition("Contains", "col", ["text"], "src")
        self.assertIn("Contains", condition)

    def test_validate_filters(self):
        filters = [
            {"Condition": "GreaterThan", "Values": [10]}, # Valid
            {"Condition": "GreaterThan", "Values": [10, 20]}, # Invalid, requires 1 value
            {"Condition": "Between", "Values": [10]}, # Invalid, requires 2 values
            {"Condition": "Contains", "Values": [123]} # Invalid, requires string
        ]
        
        valid, ignored = _validate_filters(filters)
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(ignored), 3)

    @patch('pbir_utils.filter_utils._load_json')
    @patch('pbir_utils.filter_utils._write_json')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_update_report_filters(self, mock_listdir, mock_exists, mock_write_json, mock_load_json):
        mock_listdir.return_value = ["Report1.Report"]
        mock_exists.return_value = True
        
        # Mock report data
        mock_load_json.return_value = {
            "filterConfig": {
                "filters": [
                    {
                        "field": {
                            "Column": {
                                "Property": "Col1",
                                "Expression": {"SourceRef": {"Entity": "Table1"}}
                            }
                        }
                    }
                ]
            }
        }
        
        filters = [
            {"Table": "Table1", "Column": "Col1", "Condition": "GreaterThan", "Values": [10]}
        ]
        
        update_report_filters("dummy_path", filters)
        
        mock_write_json.assert_called_once()
        # Verify that the filter was updated (checking if 'filter' key was added)
        args, _ = mock_write_json.call_args
        self.assertIn("filter", args[1]["filterConfig"]["filters"][0])

    @patch('pbir_utils.filter_utils._load_json')
    @patch('pbir_utils.filter_utils._write_json')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_sort_report_filters(self, mock_listdir, mock_exists, mock_write_json, mock_load_json):
        mock_listdir.return_value = ["Report1.Report"]
        mock_exists.return_value = True
        
        mock_load_json.return_value = {
            "filterConfig": {
                "filters": [
                    {"field": {"Column": {"Property": "B"}}},
                    {"field": {"Column": {"Property": "A"}}}
                ]
            }
        }
        
        sort_report_filters("dummy_path", sort_order="Ascending")
        
        mock_write_json.assert_called_once()
        args, _ = mock_write_json.call_args
        filter_config = args[1]["filterConfig"]
        self.assertEqual(filter_config["filterSortOrder"], "Ascending")

    @patch('pbir_utils.filter_utils._load_json')
    @patch('pbir_utils.filter_utils._write_json')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_sort_report_filters_selected_top(self, mock_listdir, mock_exists, mock_write_json, mock_load_json):
        mock_listdir.return_value = ["Report1.Report"]
        mock_exists.return_value = True
        
        mock_load_json.return_value = {
            "filterConfig": {
                "filters": [
                    {"field": {"Column": {"Property": "B"}}}, # Unselected
                    {"field": {"Column": {"Property": "A"}}, "filter": {}} # Selected
                ]
            }
        }
        
        sort_report_filters("dummy_path", sort_order="SelectedFilterTop")
        
        mock_write_json.assert_called_once()
        args, _ = mock_write_json.call_args
        filter_config = args[1]["filterConfig"]
        self.assertEqual(filter_config["filterSortOrder"], "Custom")
        # Selected (A) should be first, then Unselected (B)
        self.assertEqual(filter_config["filters"][0]["field"]["Column"]["Property"], "A")
        self.assertEqual(filter_config["filters"][1]["field"]["Column"]["Property"], "B")

    @patch('pbir_utils.filter_utils._load_json')
    @patch('pbir_utils.filter_utils._write_json')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_sort_report_filters_custom(self, mock_listdir, mock_exists, mock_write_json, mock_load_json):
        mock_listdir.return_value = ["Report1.Report"]
        mock_exists.return_value = True
        
        mock_load_json.return_value = {
            "filterConfig": {
                "filters": [
                    {"field": {"Column": {"Property": "C"}}},
                    {"field": {"Column": {"Property": "A"}}},
                    {"field": {"Column": {"Property": "B"}}}
                ]
            }
        }
        
        sort_report_filters("dummy_path", sort_order="Custom", custom_order=["B", "A"])
        
        mock_write_json.assert_called_once()
        args, _ = mock_write_json.call_args
        filter_config = args[1]["filterConfig"]
        self.assertEqual(filter_config["filterSortOrder"], "Custom")
        # B should be first, then A, then C (alphabetical among remaining)
        self.assertEqual(filter_config["filters"][0]["field"]["Column"]["Property"], "B")
        self.assertEqual(filter_config["filters"][1]["field"]["Column"]["Property"], "A")
        self.assertEqual(filter_config["filters"][2]["field"]["Column"]["Property"], "C")

    @patch('pbir_utils.filter_utils._load_json')
    @patch('pbir_utils.filter_utils._write_json')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_sort_report_filters_invalid(self, mock_listdir, mock_exists, mock_write_json, mock_load_json):
        mock_listdir.return_value = ["Report1.Report"]
        mock_exists.return_value = True
        
        mock_load_json.return_value = {
            "filterConfig": {
                "filters": [
                    {"field": {"Column": {"Property": "A"}}}
                ]
            }
        }
        
        sort_report_filters("dummy_path", sort_order="InvalidOrder")
        
        mock_write_json.assert_not_called()

if __name__ == '__main__':
    unittest.main()
