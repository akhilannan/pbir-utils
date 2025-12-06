import pytest
import os
import sys
import json
import subprocess

# Path to the src directory
SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")

# Add src to sys.path for all tests
sys.path.insert(0, os.path.abspath(SRC_DIR))


def create_dummy_file(test_dir, path, content):
    """
    Create a file at test_dir/path with the given content.

    Args:
        test_dir: Base directory (typically tmp_path from pytest)
        path: Relative path within test_dir
        content: File content - dict/list will be JSON dumped, str written as-is

    Returns:
        str: Full path to the created file
    """
    full_path = test_dir / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        if isinstance(content, dict) or isinstance(content, list):
            json.dump(content, f)
        else:
            f.write(content)
    return str(full_path)


@pytest.fixture
def simple_report(tmp_path):
    """Creates a simple dummy report structure."""
    report_dir = tmp_path / "Dummy.Report"
    report_dir.mkdir()
    definition_dir = report_dir / "definition"
    definition_dir.mkdir()
    pages_dir = definition_dir / "pages"
    pages_dir.mkdir()

    # Create a dummy page
    page_dir = pages_dir / "Page1"
    page_dir.mkdir()
    with open(page_dir / "page.json", "w") as f:
        json.dump({"name": "Page1", "displayName": "Page 1"}, f)

    # Create a dummy visual
    visuals_dir = page_dir / "visuals"
    visuals_dir.mkdir()
    with open(visuals_dir / "visual1.json", "w") as f:
        json.dump({"name": "visual1", "type": "slicer"}, f)

    return str(report_dir)


@pytest.fixture
def complex_report(tmp_path):
    """Creates a complex synthetic report structure with measures, bookmarks, etc."""
    report_dir = tmp_path / "Synthetic.Report"
    report_dir.mkdir()

    # Create necessary subdirectories
    definition_dir = report_dir / "definition"
    definition_dir.mkdir()
    pages_dir = definition_dir / "pages"
    pages_dir.mkdir()
    bookmarks_dir = definition_dir / "bookmarks"
    bookmarks_dir.mkdir()

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
                            "Property": "Column1",
                        }
                    },
                    "filter": {
                        "Version": 2,
                        "From": [{"Name": "t", "Entity": "Table1", "Type": 0}],
                        "Where": [{"Condition": {}}],
                    },
                }
            ]
        },
    }
    with open(definition_dir / "report.json", "w") as f:
        json.dump(report_json, f)

    # 2. reportExtensions.json (Measures)
    report_extensions_json = {
        "entities": [
            {
                "name": "Table1",
                "measures": [
                    {"name": "Measure1", "expression": "SUM(Table1[Column1])"},
                    {"name": "UnusedMeasure", "expression": "SUM(Table1[Column2])"},
                ],
            }
        ]
    }
    with open(definition_dir / "reportExtensions.json", "w") as f:
        json.dump(report_extensions_json, f)

    # 3. Pages and Visuals
    # Page 1 (Active)
    page1_dir = pages_dir / "Page1"
    page1_dir.mkdir()
    visual1_dir = page1_dir / "visuals" / "Visual1"
    visual1_dir.mkdir(parents=True)

    page1_json = {
        "name": "Page1",
        "displayName": "Page 1",
        "pageOrder": ["Page1", "Page2"],
        "activePageName": "Page1",
        "visibility": "Visible",
        "visualInteractions": [{"source": "Visual1", "target": "Visual2", "type": 0}],
    }
    with open(page1_dir / "page.json", "w") as f:
        json.dump(page1_json, f)

    # Visual 1 (Uses Measure1)
    visual1_json = {
        "name": "Visual1",
        "visual": {"visualType": "columnChart", "objects": {}},
        "singleVisual": {"projections": {"Y": [{"queryRef": "Measure1"}]}},
    }
    with open(visual1_dir / "visual.json", "w") as f:
        json.dump(visual1_json, f)

    # Page 2 (Tooltip, Hidden)
    page2_dir = pages_dir / "Page2"
    page2_dir.mkdir()
    (page2_dir / "visuals").mkdir()

    page2_json = {
        "name": "Page2",
        "displayName": "Page 2",
        "pageBinding": {"type": "Tooltip"},
        "visibility": "HiddenInViewMode",
    }
    with open(page2_dir / "page.json", "w") as f:
        json.dump(page2_json, f)

    # 4. Bookmarks
    bookmarks_json = {"items": [{"name": "Bookmark1", "children": []}]}
    with open(bookmarks_dir / "bookmarks.json", "w") as f:
        json.dump(bookmarks_json, f)

    bookmark1_json = {
        "name": "Bookmark1",
        "explorationState": {
            "activeSection": "Page1",
            "sections": {"Page1": {"visualContainers": {"Visual1": {}}}},
        },
    }
    with open(bookmarks_dir / "Bookmark1.bookmark.json", "w") as f:
        json.dump(bookmark1_json, f)

    # Pages.json at root of pages
    pages_root_json = {"pageOrder": ["Page1", "Page2"], "activePageName": "Page1"}
    with open(pages_dir / "pages.json", "w") as f:
        json.dump(pages_root_json, f)

    return str(report_dir)


@pytest.fixture
def run_cli():
    def _run_cli(args, cwd=None):
        """Helper to run CLI commands."""
        cmd = [sys.executable, "-m", "pbir_utils.cli"] + args
        env = os.environ.copy()
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=cwd)
        return result

    return _run_cli
