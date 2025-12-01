import unittest
import os
import sys
import json
import shutil
import tempfile
from unittest.mock import patch, MagicMock

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pbir_utils.pbir_processor import (
    _load_csv_mapping,
    _update_dax_expression,
    _update_entity,
    _update_property,
    batch_update_pbir_project
)

class TestPBIRProcessor(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_dummy_file(self, path, content):
        full_path = os.path.join(self.test_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            if isinstance(content, dict) or isinstance(content, list):
                json.dump(content, f)
            else:
                f.write(content)
        return full_path

    def test_load_csv_mapping_invalid_columns(self):
        csv_content = "old_tbl,old_col,new_tbl\nTable,Col,NewTable"
        csv_path = self.create_dummy_file("mapping.csv", csv_content)
        with self.assertRaises(ValueError):
            _load_csv_mapping(csv_path)

    def test_update_dax_expression_patterns(self):
        # Test quoted table
        expr = "'Old Table'[Column]"
        table_map = {"Old Table": "New Table"}
        self.assertEqual(_update_dax_expression(expr, table_map=table_map), "'New Table'[Column]")

        # Test unquoted table
        expr = "OldTable[Column]"
        table_map = {"OldTable": "NewTable"}
        self.assertEqual(_update_dax_expression(expr, table_map=table_map), "NewTable[Column]")
        
        # Test table with spaces becoming unquoted (if logic allowed, but here we test preservation/quoting)
        expr = "'Old Table'[Column]"
        table_map = {"Old Table": "NewTable"}
        self.assertEqual(_update_dax_expression(expr, table_map=table_map), "'NewTable'[Column]") # Code preserves quotes if present

        # Test column update
        expr = "'Table'[OldColumn]"
        column_map = {("Table", "OldColumn"): "NewColumn"}
        self.assertEqual(_update_dax_expression(expr, column_map=column_map), "'Table'[NewColumn]")

        # Test column update with unquoted table
        expr = "Table[OldColumn]"
        column_map = {("Table", "OldColumn"): "NewColumn"}
        self.assertEqual(_update_dax_expression(expr, column_map=column_map), "Table[NewColumn]")

    def test_update_entity_nested(self):
        data = {
            "Entity": "OldTable",
            "nested": {
                "Entity": "OldTable",
                "entities": [{"name": "OldTable"}]
            }
        }
        table_map = {"OldTable": "NewTable"}
        updated = _update_entity(data, table_map)
        self.assertTrue(updated)
        self.assertEqual(data["Entity"], "NewTable")
        self.assertEqual(data["nested"]["Entity"], "NewTable")
        self.assertEqual(data["nested"]["entities"][0]["name"], "NewTable")

    def test_update_property_nested(self):
        data = {
            "Column": {
                "Expression": {"SourceRef": {"Entity": "Table"}},
                "Property": "OldCol"
            },
            "nested": {
                "Measure": {
                    "Expression": {"SourceRef": {"Entity": "Table"}},
                    "Property": "OldCol"
                }
            }
        }
        column_map = {("Table", "OldCol"): "NewCol"}
        updated = _update_property(data, column_map)
        self.assertTrue(updated)
        self.assertEqual(data["Column"]["Property"], "NewCol")
        self.assertEqual(data["nested"]["Measure"]["Property"], "NewCol")

    def test_batch_update_pbir_project_exception(self):
        # Test with non-existent CSV to trigger exception handling
        with patch('builtins.print') as mock_print:
            batch_update_pbir_project(self.test_dir, "non_existent.csv")
            mock_print.assert_called()
            self.assertTrue("An error occurred" in mock_print.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
