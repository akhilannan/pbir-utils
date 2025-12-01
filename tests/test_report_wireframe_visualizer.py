import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pbir_utils.report_wireframe_visualizer import (
    _extract_page_info,
    _extract_visual_info,
    _adjust_visual_positions,
    _create_wireframe_figure,
    _apply_filters,
    display_report_wireframes
)

class TestReportWireframeVisualizer(unittest.TestCase):

    def setUp(self):
        self.mock_page_json = {
            "name": "ReportSection1",
            "displayName": "Page 1",
            "width": 1280,
            "height": 720
        }
        self.mock_visual_json = {
            "position": {"x": 10, "y": 20, "width": 100, "height": 200},
            "visual": {"visualType": "columnChart"},
            "parentGroupName": None,
            "isHidden": False
        }
        self.mock_group_json = {
            "position": {"x": 5, "y": 5, "width": 300, "height": 300},
            "visual": {"visualType": "Group"},
            "parentGroupName": None,
            "isHidden": False
        }
        self.mock_child_visual_json = {
            "position": {"x": 10, "y": 10, "width": 50, "height": 50},
            "visual": {"visualType": "card"},
            "parentGroupName": "visual_group",
            "isHidden": True
        }

    @patch('pbir_utils.report_wireframe_visualizer._load_json')
    @patch('os.path.exists')
    def test_extract_page_info(self, mock_exists, mock_load_json):
        mock_exists.return_value = True
        mock_load_json.return_value = self.mock_page_json
        
        info = _extract_page_info("dummy/path")
        self.assertEqual(info, ("ReportSection1", "Page 1", 1280, 720))

    @patch('os.path.exists')
    def test_extract_page_info_not_found(self, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(FileNotFoundError):
            _extract_page_info("dummy/path")

    @patch('pbir_utils.report_wireframe_visualizer._load_json')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_extract_visual_info(self, mock_listdir, mock_exists, mock_load_json):
        mock_listdir.return_value = ["visual1", "visual2"]
        mock_exists.return_value = True
        
        # Return different data for different calls
        def side_effect(path):
            if "visual1" in path:
                return self.mock_visual_json
            return self.mock_child_visual_json
            
        mock_load_json.side_effect = side_effect
        
        visuals = _extract_visual_info("dummy/visuals")
        self.assertEqual(len(visuals), 2)
        self.assertIn("visual1", visuals)
        self.assertIn("visual2", visuals)
        self.assertEqual(visuals["visual1"][4], "columnChart")

    def test_adjust_visual_positions(self):
        visuals = {
            "group1": (10, 10, 200, 200, "Group", None, False),
            "child1": (5, 5, 50, 50, "card", "group1", False),
            "orphan": (100, 100, 50, 50, "card", "missing_parent", False)
        }
        
        adjusted = _adjust_visual_positions(visuals)
        
        # Child should be offset by parent position
        self.assertEqual(adjusted["child1"][0], 15) # 5 + 10
        self.assertEqual(adjusted["child1"][1], 15) # 5 + 10
        
        # Orphan should remain as is (or handled gracefully if code allows)
        # Code says: x + visuals[parent][0] if parent in visuals else x
        self.assertEqual(adjusted["orphan"][0], 100)

    def test_create_wireframe_figure(self):
        visuals_info = {
            "v1": (10, 10, 100, 100, "chart", None, False),
            "v2": (200, 200, 50, 50, "card", None, True)
        }
        
        # Test with show_hidden=True
        fig = _create_wireframe_figure(1000, 800, visuals_info, show_hidden=True)
        self.assertIsNotNone(fig)
        # We expect 2 traces (one for each visual)
        self.assertEqual(len(fig.data), 2)
        
        # Test with show_hidden=False
        fig = _create_wireframe_figure(1000, 800, visuals_info, show_hidden=False)
        self.assertEqual(len(fig.data), 1)

    def test_apply_filters(self):
        pages_info = [
            ("p1", "Page 1", 100, 100, {
                "v1": (0, 0, 10, 10, "chart", None, False),
                "v2": (20, 20, 10, 10, "card", None, False)
            }),
            ("p2", "Page 2", 100, 100, {})
        ]
        
        # Filter by page
        filtered = _apply_filters(pages_info, pages=["p1"])
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0][0], "p1")
        
        # Filter by visual type
        filtered = _apply_filters(pages_info, visual_types=["chart"])
        self.assertEqual(len(filtered), 1) # p2 is empty, p1 has chart
        self.assertEqual(len(filtered[0][4]), 1) # only v1
        
        # Filter by visual id
        filtered = _apply_filters(pages_info, visual_ids=["v2"])
        self.assertEqual(len(filtered), 1)
        self.assertIn("v2", filtered[0][4])

    @patch('pbir_utils.report_wireframe_visualizer.dash.Dash')
    @patch('pbir_utils.report_wireframe_visualizer._get_page_order')
    @patch('pbir_utils.report_wireframe_visualizer._extract_visual_info')
    @patch('pbir_utils.report_wireframe_visualizer._extract_page_info')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_display_report_wireframes(self, mock_isdir, mock_listdir, mock_extract_page, mock_extract_visual, mock_get_order, mock_dash):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["Page1"]
        mock_extract_page.return_value = ("p1", "Page 1", 100, 100)
        mock_extract_visual.return_value = {}
        mock_get_order.return_value = ["p1"]
        
        mock_app = MagicMock()
        mock_dash.return_value = mock_app
        
        display_report_wireframes("dummy/report")
        
        mock_app.run.assert_called_once()

if __name__ == '__main__':
    unittest.main()
