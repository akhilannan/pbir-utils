import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pbir_utils.pbir_measure_utils import (
    _get_dependent_measures,
    _get_visual_ids_for_measure,
    _is_measure_used_in_visuals,
    _is_measure_or_dependents_used_in_visuals,
    _trace_dependency_path,
    _format_measure_with_visual_ids,
    generate_measure_dependencies_report,
    remove_measures
)

class TestPBIRMeasureUtils(unittest.TestCase):

    def setUp(self):
        self.measures_dict = {
            "MeasureA": "SUM(Table[Col])",
            "MeasureB": "[MeasureA] * 2",
            "MeasureC": "[MeasureB] + 10",
            "MeasureD": "COUNT(Table[ID])"
        }

    def test_get_dependent_measures(self):
        # MeasureA is used in MeasureB
        deps_A = _get_dependent_measures("MeasureA", self.measures_dict)
        self.assertIn("MeasureB", deps_A)
        self.assertNotIn("MeasureC", deps_A) # Direct only by default

        # MeasureB is used in MeasureC
        deps_B = _get_dependent_measures("MeasureB", self.measures_dict)
        self.assertIn("MeasureC", deps_B)

        # MeasureD has no dependents
        deps_D = _get_dependent_measures("MeasureD", self.measures_dict)
        self.assertEqual(len(deps_D), 0)

        # Recursive (all dependents)
        all_deps_A = _get_dependent_measures("MeasureA", self.measures_dict, include_all_dependents=True)
        self.assertIn("MeasureB", all_deps_A)
        self.assertIn("MeasureC", all_deps_A)

    @patch('pbir_utils.pbir_measure_utils.os.walk')
    @patch('pbir_utils.pbir_measure_utils._load_json')
    @patch('pbir_utils.pbir_measure_utils._extract_metadata_from_file')
    def test_get_visual_ids_for_measure(self, mock_extract, mock_load, mock_walk):
        mock_walk.return_value = [("root", [], ["visual.json"])]
        mock_load.return_value = {"name": "Visual123"}
        
        # Case 1: Measure is used
        mock_extract.return_value = [{"Column or Measure": "MeasureA"}]
        ids = _get_visual_ids_for_measure("dummy_path", "MeasureA")
        self.assertEqual(ids, ["Visual123"])
        
        # Case 2: Measure is not used
        mock_extract.return_value = [{"Column or Measure": "OtherMeasure"}]
        ids = _get_visual_ids_for_measure("dummy_path", "MeasureA")
        self.assertEqual(ids, [])

    @patch('pbir_utils.pbir_measure_utils._get_visual_ids_for_measure')
    def test_is_measure_used_in_visuals(self, mock_get_ids):
        mock_get_ids.return_value = ["v1"]
        self.assertTrue(_is_measure_used_in_visuals("path", "m1"))
        
        mock_get_ids.return_value = []
        self.assertFalse(_is_measure_used_in_visuals("path", "m1"))

    @patch('pbir_utils.pbir_measure_utils._is_measure_used_in_visuals')
    def test_is_measure_or_dependents_used_in_visuals(self, mock_is_used):
        # Case 1: Measure itself is used
        mock_is_used.side_effect = lambda p, m: m == "MeasureA"
        self.assertTrue(_is_measure_or_dependents_used_in_visuals("path", "MeasureA", self.measures_dict))
        
        # Case 2: Dependent is used (MeasureB uses MeasureA)
        mock_is_used.side_effect = lambda p, m: m == "MeasureB"
        self.assertTrue(_is_measure_or_dependents_used_in_visuals("path", "MeasureA", self.measures_dict))
        
        # Case 3: None used
        mock_is_used.side_effect = None
        mock_is_used.return_value = False
        self.assertFalse(_is_measure_or_dependents_used_in_visuals("path", "MeasureA", self.measures_dict))

    def test_trace_dependency_path(self):
        paths = []
        _trace_dependency_path(self.measures_dict, "MeasureA", ["MeasureA"], paths)
        # Expected paths: A -> B -> C
        self.assertTrue(any(p == ["MeasureA", "MeasureB", "MeasureC"] for p in paths))

    @patch('pbir_utils.pbir_measure_utils._load_report_extension_data')
    @patch('pbir_utils.pbir_measure_utils._get_dependent_measures')
    def test_generate_measure_dependencies_report(self, mock_get_deps, mock_load_data):
        mock_load_data.return_value = ("path", {"entities": [{"measures": [{"name": "M1", "expression": "exp"}]}]})
        mock_get_deps.return_value = {"M2"}
        
        report = generate_measure_dependencies_report("path", measure_names=["M1"])
        self.assertIn("Dependencies for M1", report)

    @patch('pbir_utils.pbir_measure_utils._load_report_extension_data')
    @patch('pbir_utils.pbir_measure_utils._write_json')
    @patch('pbir_utils.pbir_measure_utils._is_measure_or_dependents_used_in_visuals')
    def test_remove_measures(self, mock_is_used, mock_write, mock_load_data):
        report_data = {
            "entities": [{
                "measures": [
                    {"name": "KeepMe", "expression": "exp1"},
                    {"name": "RemoveMe", "expression": "exp2"}
                ]
            }]
        }
        mock_load_data.return_value = ("path/reportExtensions.json", report_data)
        
        # Mock usage check: KeepMe is used, RemoveMe is not
        mock_is_used.side_effect = lambda p, m, d: m == "KeepMe"
        
        remove_measures("path", measure_names=None, check_visual_usage=True)
        
        # Check what was written back
        args, _ = mock_write.call_args
        written_data = args[1]
        measures = written_data["entities"][0]["measures"]
        self.assertEqual(len(measures), 1)
        self.assertEqual(measures[0]["name"], "KeepMe")

if __name__ == '__main__':
    unittest.main()
