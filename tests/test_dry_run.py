import os
import shutil
import pytest
import json
import tempfile
from pbir_utils.pbir_report_sanitizer import sanitize_powerbi_report
from pbir_utils.pbir_processor import batch_update_pbir_project
from pbir_utils.pbir_measure_utils import remove_measures
from pbir_utils.filter_utils import update_report_filters, sort_report_filters
from pbir_utils.visual_interactions_utils import disable_visual_interactions

@pytest.fixture
def setup_report():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    report_dir = os.path.join(temp_dir, "Synthetic.Report")
    os.makedirs(report_dir)
    
    # Create necessary subdirectories
    definition_dir = os.path.join(report_dir, "definition")
    pages_dir = os.path.join(definition_dir, "pages")
    bookmarks_dir = os.path.join(definition_dir, "bookmarks")
    os.makedirs(pages_dir)
    os.makedirs(bookmarks_dir)

    # 1. report.json
    report_json = {
        "publicCustomVisuals": ["customVisual1"],
        "filterConfig": {
            "filters": [
                {
                    "name": "Filter1",
                    "field": {
                        "Column": {
                            "Expression": {"SourceRef": {"Entity": "Table1"}},
                            "Property": "Column1"
                        }
                    },
                    "filter": {
                        "Version": 2,
                        "From": [{"Name": "t", "Entity": "Table1", "Type": 0}],
                        "Where": [{"Condition": {}}]
                    }
                }
            ]
        }
    }
    with open(os.path.join(definition_dir, "report.json"), "w") as f:
        json.dump(report_json, f)

    # 2. reportExtensions.json (Measures)
    report_extensions_json = {
        "entities": [
            {
                "name": "Table1",
                "measures": [
                    {"name": "Measure1", "expression": "SUM(Table1[Column1])"},
                    {"name": "UnusedMeasure", "expression": "SUM(Table1[Column2])"}
                ]
            }
        ]
    }
    with open(os.path.join(definition_dir, "reportExtensions.json"), "w") as f:
        json.dump(report_extensions_json, f)

    # 3. Pages and Visuals
    # Page 1 (Active)
    page1_dir = os.path.join(pages_dir, "Page1")
    visual1_dir = os.path.join(page1_dir, "visuals", "Visual1")
    os.makedirs(visual1_dir)
    
    page1_json = {
        "name": "Page1",
        "displayName": "Page 1",
        "pageOrder": ["Page1", "Page2"],
        "activePageName": "Page1",
        "visibility": "Visible",
        "visualInteractions": [
            {"source": "Visual1", "target": "Visual2", "type": 0}
        ]
    }
    with open(os.path.join(page1_dir, "page.json"), "w") as f:
        json.dump(page1_json, f)

    # Visual 1 (Uses Measure1)
    visual1_json = {
        "name": "Visual1",
        "visual": {
            "visualType": "columnChart",
            "objects": {}
        },
        "singleVisual": {
            "projections": {
                "Y": [{"queryRef": "Measure1"}]
            }
        }
    }
    with open(os.path.join(visual1_dir, "visual.json"), "w") as f:
        json.dump(visual1_json, f)

    # Page 2 (Tooltip, Hidden)
    page2_dir = os.path.join(pages_dir, "Page2")
    os.makedirs(os.path.join(page2_dir, "visuals"))
    
    page2_json = {
        "name": "Page2",
        "displayName": "Page 2",
        "pageBinding": {"type": "Tooltip"},
        "visibility": "HiddenInViewMode"
    }
    with open(os.path.join(page2_dir, "page.json"), "w") as f:
        json.dump(page2_json, f)

    # 4. Bookmarks
    bookmarks_json = {
        "items": [
            {"name": "Bookmark1", "children": []}
        ]
    }
    with open(os.path.join(bookmarks_dir, "bookmarks.json"), "w") as f:
        json.dump(bookmarks_json, f)

    bookmark1_json = {
        "name": "Bookmark1",
        "explorationState": {
            "activeSection": "Page1",
            "sections": {
                "Page1": {
                    "visualContainers": {
                        "Visual1": {}
                    }
                }
            }
        }
    }
    with open(os.path.join(bookmarks_dir, "Bookmark1.bookmark.json"), "w") as f:
        json.dump(bookmark1_json, f)
        
    # Pages.json at root of pages
    pages_root_json = {
        "pageOrder": ["Page1", "Page2"],
        "activePageName": "Page1"
    }
    with open(os.path.join(pages_dir, "pages.json"), "w") as f:
        json.dump(pages_root_json, f)

    yield report_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)

def get_dir_mtime(directory):
    mtimes = {}
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            mtimes[path] = os.path.getmtime(path)
    return mtimes

def test_sanitize_powerbi_report_dry_run(setup_report):
    initial_mtimes = get_dir_mtime(setup_report)
    
    actions = [
        "remove_unused_measures",
        "remove_unused_bookmarks",
        "remove_unused_custom_visuals",
        "disable_show_items_with_no_data",
        "hide_tooltip_drillthrough_pages",
        "set_first_page_as_active",
        "remove_empty_pages",
        "remove_hidden_visuals_never_shown",
        "cleanup_invalid_bookmarks",
    ]
    
    sanitize_powerbi_report(setup_report, actions, dry_run=True)
    
    final_mtimes = get_dir_mtime(setup_report)
    assert initial_mtimes == final_mtimes, "Files were modified during dry run!"

def test_batch_update_pbir_project_dry_run(setup_report):
    initial_mtimes = get_dir_mtime(setup_report)
    
    # Create a dummy CSV for mapping
    csv_path = os.path.join(setup_report, "mapping.csv")
    with open(csv_path, "w") as f:
        f.write("old_tbl,old_col,new_tbl,new_col\nTable1,Col1,Table1_New,Col1_New")
    
    # Exclude the CSV from mtime check
    initial_mtimes = get_dir_mtime(setup_report)
    
    batch_update_pbir_project(os.path.dirname(setup_report), csv_path, dry_run=True)
    
    final_mtimes = get_dir_mtime(setup_report)
    assert initial_mtimes == final_mtimes, "Files were modified during dry run!"

def test_remove_measures_dry_run(setup_report):
    initial_mtimes = get_dir_mtime(setup_report)
    
    remove_measures(setup_report, dry_run=True)
    
    final_mtimes = get_dir_mtime(setup_report)
    assert initial_mtimes == final_mtimes, "Files were modified during dry run!"

def test_update_report_filters_dry_run(setup_report):
    initial_mtimes = get_dir_mtime(setup_report)
    
    filters = [
        {
            "Table": "Table1",
            "Column": "Column1",
            "Condition": "GreaterThan",
            "Values": ["100"]
        }
    ]
    
    update_report_filters(os.path.dirname(setup_report), filters, dry_run=True)
    
    final_mtimes = get_dir_mtime(setup_report)
    assert initial_mtimes == final_mtimes, "Files were modified during dry run!"

def test_sort_report_filters_dry_run(setup_report):
    initial_mtimes = get_dir_mtime(setup_report)
    
    sort_report_filters(os.path.dirname(setup_report), sort_order="Ascending", dry_run=True)
    
    final_mtimes = get_dir_mtime(setup_report)
    assert initial_mtimes == final_mtimes, "Files were modified during dry run!"

def test_disable_visual_interactions_dry_run(setup_report):
    initial_mtimes = get_dir_mtime(setup_report)
    
    disable_visual_interactions(setup_report, dry_run=True)
    
    final_mtimes = get_dir_mtime(setup_report)
    assert initial_mtimes == final_mtimes, "Files were modified during dry run!"
