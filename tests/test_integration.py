import unittest
import os
import sys
import json
import shutil
import tempfile
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pbir_utils.metadata_extractor import _extract_metadata_from_file, _consolidate_metadata_from_directory, export_pbir_metadata_to_csv
from pbir_utils.pbir_report_sanitizer import sanitize_powerbi_report
from pbir_utils.pbir_processor import batch_update_pbir_project

class TestPBIRUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a temporary directory for the test suite
        cls.test_dir = tempfile.mkdtemp()
        
        # Define the synthetic report path
        cls.report_name = "Mock.Report"
        cls.report_path = os.path.join(cls.test_dir, cls.report_name)
        cls.temp_report_path = os.path.join(cls.test_dir, "Temp_Mock.Report")
        
        # Create the synthetic report structure
        cls._create_synthetic_report(cls.report_path)
        
        # Create a copy for destructive tests
        shutil.copytree(cls.report_path, cls.temp_report_path)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    @classmethod
    def _create_synthetic_report(cls, base_path):
        """Creates a synthetic PBIP report structure."""
        os.makedirs(base_path, exist_ok=True)
        
        # 1. definition/report.json
        definition_dir = os.path.join(base_path, "definition")
        os.makedirs(definition_dir, exist_ok=True)
        
        report_json = {
            "name": "MockReport",
            "publicCustomVisuals": ["customVisual1"],
            "themeCollection": {"baseTheme": {"name": "CY24SU06"}},
            "modelId": 12345
        }
        cls._write_json(os.path.join(definition_dir, "report.json"), report_json)
        
        # 2. definition/pages/pages.json
        pages_dir = os.path.join(definition_dir, "pages")
        os.makedirs(pages_dir, exist_ok=True)
        
        pages_json = {
            "pageOrder": ["Page1", "Page2", "TooltipPage"],
            "activePageName": "Page1"
        }
        cls._write_json(os.path.join(pages_dir, "pages.json"), pages_json)
        
        # 3. definition/pages/Page1 (Standard Page)
        cls._create_page(pages_dir, "Page1", "Page 1", "ReportSection", "Visible", visuals=[
            {
                "name": "visual1",
                "visual": {
                    "visualType": "columnChart",
                    "objects": {
                        "general": [{"properties": {"showAll": True}}] # For disable_show_items_with_no_data
                    },
                    "query": {
                        "Category": {
                            "Entity": "Sales",
                            "Property": "Amount"
                        }
                    }
                }
            },
            {
                "name": "visual2",
                "isHidden": True, # For remove_hidden_visuals_never_shown (needs bookmark check)
                "visual": {
                    "visualType": "card"
                }
            }
        ])
        
        # 4. definition/pages/Page2 (Empty Page)
        cls._create_page(pages_dir, "Page2", "Page 2", "ReportSection", "Visible", visuals=[])
        
        # 5. definition/pages/TooltipPage (Tooltip)
        cls._create_page(pages_dir, "TooltipPage", "Tooltip Page", "Tooltip", "Visible", visuals=[])

        # 6. definition/bookmarks/bookmarks.json
        bookmarks_dir = os.path.join(definition_dir, "bookmarks")
        os.makedirs(bookmarks_dir, exist_ok=True)
        
        bookmarks_json = {
            "items": [{"name": "Bookmark1"}, {"name": "Bookmark2"}]
        }
        cls._write_json(os.path.join(bookmarks_dir, "bookmarks.json"), bookmarks_json)
        
        # 7. definition/bookmarks/Bookmark1.bookmark.json (Valid)
        bookmark1 = {
            "name": "Bookmark1",
            "displayName": "Valid Bookmark",
            "explorationState": {
                "activeSection": "Page1",
                "sections": {
                    "Page1": {
                        "visualContainers": {
                            "visual2": {"singleVisual": {"display": {"mode": "Visible"}}} # References hidden visual
                        }
                    }
                }
            }
        }
        cls._write_json(os.path.join(bookmarks_dir, "Bookmark1.bookmark.json"), bookmark1)

        # 8. definition/bookmarks/Bookmark2.bookmark.json (Invalid - references non-existent page)
        bookmark2 = {
            "name": "Bookmark2",
            "displayName": "Invalid Bookmark",
            "explorationState": {
                "activeSection": "NonExistentPage"
            }
        }
        cls._write_json(os.path.join(bookmarks_dir, "Bookmark2.bookmark.json"), bookmark2)

    @classmethod
    def _create_page(cls, pages_dir, page_name, display_name, page_type, visibility, visuals=[]):
        page_dir = os.path.join(pages_dir, page_name)
        os.makedirs(page_dir, exist_ok=True)
        
        page_json = {
            "name": page_name,
            "displayName": display_name,
            "pageBinding": {"type": page_type},
            "visibility": visibility
        }
        cls._write_json(os.path.join(page_dir, "page.json"), page_json)
        
        visuals_dir = os.path.join(page_dir, "visuals")
        if visuals:
            os.makedirs(visuals_dir, exist_ok=True)
            for i, visual in enumerate(visuals):
                v_name = visual.get("name", f"visual{i}")
                # Create individual visual file (PBIR structure usually has one file per visual or folder)
                # Assuming folder structure: visuals/visualName/visual.json
                v_folder = os.path.join(visuals_dir, v_name)
                os.makedirs(v_folder, exist_ok=True)
                cls._write_json(os.path.join(v_folder, "visual.json"), visual)

    @classmethod
    def _write_json(cls, path, content):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4)

    def test_metadata_extraction(self):
        print(f"\nTesting Metadata Extraction on: {self.report_path}")
        metadata = _consolidate_metadata_from_directory(self.report_path)
        
        print(f"Metadata rows found: {len(metadata)}")
        self.assertTrue(len(metadata) > 0, "No metadata extracted")
        
        # Check for expected fields
        first_row = metadata[0]
        expected_fields = [
            "Report", "Page Name", "Page ID", "Table", 
            "Column or Measure", "Expression", "Used In", 
            "Used In Detail", "ID"
        ]
        for field in expected_fields:
            self.assertIn(field, first_row)
            
        print(f"Extracted {len(metadata)} metadata rows.")

    def test_export_pbir_metadata_to_csv(self):
        print(f"\nTesting Metadata Export to CSV on: {self.report_path}")
        csv_output_path = os.path.join(self.test_dir, "metadata.csv")
        export_pbir_metadata_to_csv(self.test_dir, csv_output_path)
        
        self.assertTrue(os.path.exists(csv_output_path), "CSV file was not created")
        
        with open(csv_output_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        self.assertTrue(len(lines) > 1, "CSV file is empty or only has header")
        header = lines[0].strip().split(',')
        expected_fields = [
            "Report", "Page Name", "Page ID", "Table", 
            "Column or Measure", "Expression", "Used In", 
            "Used In Detail", "ID"
        ]
        self.assertEqual(header, expected_fields)
        print(f"Exported metadata to {csv_output_path}")

    def test_sanitization_remove_unused_measures(self):
        print("\nTesting Sanitization: Remove Unused Measures...")
        sanitize_powerbi_report(self.temp_report_path, ["remove_unused_measures"])
        self.assertTrue(os.path.exists(self.temp_report_path))

    def test_sanitization_remove_unused_bookmarks(self):
        print("\nTesting Sanitization: Remove Unused Bookmarks...")
        sanitize_powerbi_report(self.temp_report_path, ["remove_unused_bookmarks"])
        self.assertTrue(os.path.exists(self.temp_report_path))

    def test_batch_update(self):
        print("\nTesting Batch Update...")
        # Create a dummy mapping CSV
        csv_path = os.path.join(self.test_dir, 'mapping.csv')
        with open(csv_path, 'w', newline='') as f:
            f.write("old_tbl,old_col,new_tbl,new_col\n")
            f.write("Date,Month,DateTable,MonthName\n")
        
        definition_folder = os.path.join(self.temp_report_path, 'definition')
        batch_update_pbir_project(definition_folder, csv_path)
        
        print("Batch update executed.")

    def test_sanitization_remove_unused_custom_visuals(self):
        print("\nTesting Sanitization: Remove Unused Custom Visuals...")
        sanitize_powerbi_report(self.temp_report_path, ["remove_unused_custom_visuals"])
        self.assertTrue(os.path.exists(self.temp_report_path))

    def test_sanitization_disable_show_items_with_no_data(self):
        print("\nTesting Sanitization: Disable Show Items With No Data...")
        sanitize_powerbi_report(self.temp_report_path, ["disable_show_items_with_no_data"])
        self.assertTrue(os.path.exists(self.temp_report_path))

    def test_sanitization_hide_tooltip_drillthrough_pages(self):
        print("\nTesting Sanitization: Hide Tooltip Drillthrough Pages...")
        sanitize_powerbi_report(self.temp_report_path, ["hide_tooltip_drillthrough_pages"])
        self.assertTrue(os.path.exists(self.temp_report_path))
        
        # Verify TooltipPage is hidden
        tooltip_page_json = os.path.join(self.temp_report_path, "definition", "pages", "TooltipPage", "page.json")
        with open(tooltip_page_json, 'r') as f:
            data = json.load(f)
        self.assertEqual(data["visibility"], "HiddenInViewMode")

    def test_sanitization_set_first_page_as_active(self):
        print("\nTesting Sanitization: Set First Page As Active...")
        sanitize_powerbi_report(self.temp_report_path, ["set_first_page_as_active"])
        self.assertTrue(os.path.exists(self.temp_report_path))

    def test_sanitization_remove_empty_pages(self):
        print("\nTesting Sanitization: Remove Empty Pages...")
        sanitize_powerbi_report(self.temp_report_path, ["remove_empty_pages"])
        self.assertTrue(os.path.exists(self.temp_report_path))
        
        # Verify Page2 (empty) is removed
        page2_path = os.path.join(self.temp_report_path, "definition", "pages", "Page2")
        self.assertFalse(os.path.exists(page2_path))

    def test_sanitization_remove_hidden_visuals_never_shown(self):
        print("\nTesting Sanitization: Remove Hidden Visuals Never Shown...")
        sanitize_powerbi_report(self.temp_report_path, ["remove_hidden_visuals_never_shown"])
        self.assertTrue(os.path.exists(self.temp_report_path))

    def test_sanitization_cleanup_invalid_bookmarks(self):
        print("\nTesting Sanitization: Cleanup Invalid Bookmarks...")
        sanitize_powerbi_report(self.temp_report_path, ["cleanup_invalid_bookmarks"])
        self.assertTrue(os.path.exists(self.temp_report_path))
        
        # Verify Bookmark2 (invalid) is removed
        bookmark2_path = os.path.join(self.temp_report_path, "definition", "bookmarks", "Bookmark2.bookmark.json")
        self.assertFalse(os.path.exists(bookmark2_path))

if __name__ == '__main__':
    unittest.main()
