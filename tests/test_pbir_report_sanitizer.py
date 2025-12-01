import unittest
import os
import sys
import json
import shutil
import tempfile
from unittest.mock import patch, MagicMock

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pbir_utils.pbir_report_sanitizer import (
    remove_unused_bookmarks,
    remove_unused_custom_visuals,
    disable_show_items_with_no_data,
    hide_tooltip_drillthrough_pages,
    remove_empty_pages,
    remove_hidden_visuals_never_shown,
    cleanup_invalid_bookmarks
)
from pbir_utils.json_utils import _load_json

class TestPBIRReportSanitizer(unittest.TestCase):
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

    def test_remove_unused_bookmarks_no_file(self):
        # Test when bookmarks.json doesn't exist
        report_path = self.test_dir
        with patch('builtins.print') as mock_print:
            remove_unused_bookmarks(report_path)
            mock_print.assert_called()
            self.assertTrue("No bookmarks found" in mock_print.call_args[0][0])

    def test_remove_unused_custom_visuals_none(self):
        # Test when no custom visuals exist
        report_path = self.test_dir
        self.create_dummy_file("definition/report.json", {"publicCustomVisuals": []})
        with patch('builtins.print') as mock_print:
            remove_unused_custom_visuals(report_path)
            mock_print.assert_called()
            self.assertTrue("No custom visuals found" in mock_print.call_args[0][0])

    def test_disable_show_items_with_no_data_nested(self):
        # Test nested structure
        report_path = self.test_dir
        visual_json = {
            "visual": {
                "objects": {
                    "some_obj": [{"properties": {"showAll": True}}]
                }
            }
        }
        self.create_dummy_file("definition/pages/Page1/visuals/visual.json", visual_json)
        
        disable_show_items_with_no_data(report_path)
        
        updated_data = _load_json(os.path.join(report_path, "definition/pages/Page1/visuals/visual.json"))
        self.assertNotIn("showAll", updated_data["visual"]["objects"]["some_obj"][0]["properties"])

    def test_hide_tooltip_drillthrough_pages(self):
        report_path = self.test_dir
        # Page 1: Tooltip, visible -> should hide
        self.create_dummy_file("definition/pages/Page1/page.json", {
            "displayName": "Page1",
            "pageBinding": {"type": "Tooltip"},
            "visibility": "Visible"
        })
        # Page 2: Drillthrough, visible -> should hide
        self.create_dummy_file("definition/pages/Page2/page.json", {
            "displayName": "Page2",
            "pageBinding": {"type": "Drillthrough"},
            "visibility": "Visible"
        })
        # Page 3: Normal, visible -> should stay visible
        self.create_dummy_file("definition/pages/Page3/page.json", {
            "displayName": "Page3",
            "pageBinding": {"type": "ReportSection"},
            "visibility": "Visible"
        })
        
        hide_tooltip_drillthrough_pages(report_path)
        
        p1 = _load_json(os.path.join(report_path, "definition/pages/Page1/page.json"))
        self.assertEqual(p1["visibility"], "HiddenInViewMode")
        
        p2 = _load_json(os.path.join(report_path, "definition/pages/Page2/page.json"))
        self.assertEqual(p2["visibility"], "HiddenInViewMode")
        
        p3 = _load_json(os.path.join(report_path, "definition/pages/Page3/page.json"))
        self.assertEqual(p3["visibility"], "Visible")

    def test_remove_empty_pages_all_empty(self):
        report_path = self.test_dir
        self.create_dummy_file("definition/pages/pages.json", {
            "pageOrder": ["Page1", "Page2"],
            "activePageName": "Page1"
        })
        # Create empty folders (no visuals)
        os.makedirs(os.path.join(report_path, "definition/pages/Page1/visuals"), exist_ok=True)
        os.makedirs(os.path.join(report_path, "definition/pages/Page2/visuals"), exist_ok=True)
        
        with patch('builtins.print') as mock_print:
            remove_empty_pages(report_path)
            mock_print.assert_called()
            # Should keep first page as placeholder
            pages_data = _load_json(os.path.join(report_path, "definition/pages/pages.json"))
            self.assertEqual(pages_data["pageOrder"], ["Page1"])
            self.assertEqual(pages_data["activePageName"], "Page1")

    def test_cleanup_invalid_bookmarks(self):
        report_path = self.test_dir
        # Valid page
        self.create_dummy_file("definition/pages/pages.json", {"pageOrder": ["Page1"]})
        # Fix: Create visual.json inside a folder named v1, or just visual.json if it's recursive
        # But to be safe and match structure:
        self.create_dummy_file("definition/pages/Page1/visuals/v1/visual.json", {"name": "v1"})
        
        # Bookmark referencing invalid page
        self.create_dummy_file("definition/bookmarks/b1.bookmark.json", {
            "name": "b1",
            "explorationState": {"activeSection": "InvalidPage"}
        })
        
        # Bookmark referencing valid page but invalid visual
        self.create_dummy_file("definition/bookmarks/b2.bookmark.json", {
            "name": "b2",
            "explorationState": {
                "activeSection": "Page1",
                "sections": {
                    "Page1": {
                        "visualContainers": {"v1": {}, "invalid_v": {}}
                    }
                }
            }
        })
        
        self.create_dummy_file("definition/bookmarks/bookmarks.json", {
            "items": [{"name": "b1"}, {"name": "b2"}]
        })
        
        cleanup_invalid_bookmarks(report_path)
        
        # b1 should be removed
        self.assertFalse(os.path.exists(os.path.join(report_path, "definition/bookmarks/b1.bookmark.json")))
        
        # b2 should be cleaned
        b2_data = _load_json(os.path.join(report_path, "definition/bookmarks/b2.bookmark.json"))
        self.assertIn("v1", b2_data["explorationState"]["sections"]["Page1"]["visualContainers"])
        self.assertNotIn("invalid_v", b2_data["explorationState"]["sections"]["Page1"]["visualContainers"])

    def test_remove_hidden_visuals_never_shown_cleanup(self):
        report_path = self.test_dir
        # Create a page with interactions
        self.create_dummy_file("definition/pages/Page1/page.json", {
            "name": "Page1",
            "visualInteractions": [
                {"source": "v1", "target": "hidden_v"}, # Interaction with hidden visual
                {"source": "v1", "target": "v2"}        # Valid interaction
            ]
        })
        
        # Create visible visual v1
        self.create_dummy_file("definition/pages/Page1/visuals/v1/visual.json", {"name": "v1"})
        
        # Create visible visual v2
        self.create_dummy_file("definition/pages/Page1/visuals/v2/visual.json", {"name": "v2"})
        
        # Create hidden visual hidden_v
        hidden_v_path = self.create_dummy_file("definition/pages/Page1/visuals/hidden_v/visual.json", {
            "name": "hidden_v",
            "isHidden": True
        })
        hidden_v_folder = os.path.dirname(hidden_v_path)
        
        # Create bookmarks (none show hidden_v)
        self.create_dummy_file("definition/bookmarks/bookmarks.json", {"items": []})
        
        remove_hidden_visuals_never_shown(report_path)
        
        # Verify hidden visual folder is removed
        self.assertFalse(os.path.exists(hidden_v_folder), "Hidden visual folder was not removed")
        
        # Verify interactions are cleaned up
        page_data = _load_json(os.path.join(report_path, "definition/pages/Page1/page.json"))
        interactions = page_data["visualInteractions"]
        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0]["target"], "v2")

if __name__ == '__main__':
    unittest.main()
