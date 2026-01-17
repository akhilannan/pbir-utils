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
    """Create a simple dummy report structure for basic tests."""
    report_dir = tmp_path / "Dummy.Report"

    create_dummy_file(
        report_dir,
        "definition/pages/Page1/page.json",
        {"name": "Page1", "displayName": "Page 1"},
    )
    create_dummy_file(
        report_dir,
        "definition/pages/Page1/visuals/visual1/visual.json",
        {"name": "visual1", "visual": {"visualType": "slicer"}},
    )
    create_dummy_file(
        report_dir,
        "definition/pages/Page1/visuals/visual2/visual.json",
        {"name": "visual2", "visual": {"visualType": "columnChart"}},
    )
    create_dummy_file(
        report_dir,
        "definition/pages/pages.json",
        {"pageOrder": ["Page1"]},
    )
    # Add root report.json for validation
    create_dummy_file(
        report_dir,
        "definition/report.json",
        {},
    )

    return str(report_dir)


@pytest.fixture
def complex_report(tmp_path):
    """Create a complex synthetic report with measures, bookmarks, visuals, etc."""
    report_dir = tmp_path / "Synthetic.Report"

    # report.json with filter config
    create_dummy_file(
        report_dir,
        "definition/report.json",
        {
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
        },
    )

    # reportExtensions.json (Measures)
    create_dummy_file(
        report_dir,
        "definition/reportExtensions.json",
        {
            "entities": [
                {
                    "name": "Table1",
                    "measures": [
                        {"name": "Measure1", "expression": "SUM(Table1[Column1])"},
                        {"name": "UnusedMeasure", "expression": "SUM(Table1[Column2])"},
                    ],
                }
            ]
        },
    )

    # Page 1 (Active)
    create_dummy_file(
        report_dir,
        "definition/pages/Page1/page.json",
        {
            "name": "Page1",
            "displayName": "Page 1",
            "pageOrder": ["Page1", "Page2"],
            "activePageName": "Page1",
            "visibility": "Visible",
            "visualInteractions": [
                {"source": "Visual1", "target": "Visual2", "type": 0}
            ],
        },
    )

    # Visual 1 (Uses Measure1 - with proper Entity/Property format)
    create_dummy_file(
        report_dir,
        "definition/pages/Page1/visuals/Visual1/visual.json",
        {
            "name": "Visual1",
            "visual": {"visualType": "columnChart", "objects": {}},
            "singleVisual": {
                "projections": {
                    "Y": [
                        {
                            "Measure": {
                                "Expression": {"SourceRef": {"Entity": "Table1"}},
                                "Property": "Measure1",
                            }
                        }
                    ]
                }
            },
        },
    )

    # Page 2 (Tooltip, Hidden)
    create_dummy_file(
        report_dir,
        "definition/pages/Page2/page.json",
        {
            "name": "Page2",
            "displayName": "Page 2",
            "pageBinding": {"type": "Tooltip"},
            "visibility": "HiddenInViewMode",
        },
    )

    # Bookmarks
    create_dummy_file(
        report_dir,
        "definition/bookmarks/bookmarks.json",
        {"items": [{"name": "Bookmark1", "children": []}]},
    )

    create_dummy_file(
        report_dir,
        "definition/bookmarks/Bookmark1.bookmark.json",
        {
            "name": "Bookmark1",
            "explorationState": {
                "activeSection": "Page1",
                "sections": {"Page1": {"visualContainers": {"Visual1": {}}}},
            },
        },
    )

    # Pages.json at root of pages
    create_dummy_file(
        report_dir,
        "definition/pages/pages.json",
        {"pageOrder": ["Page1", "Page2"], "activePageName": "Page1"},
    )

    return str(report_dir)


@pytest.fixture
def temp_report_structure(tmp_path):
    """Create a minimal report structure with just pages directory for folder tests."""
    report_dir = tmp_path / "TestReport.Report"
    pages_dir = report_dir / "definition" / "pages"
    os.makedirs(pages_dir)
    # Add root report.json for validation
    with open(report_dir / "definition" / "report.json", "w") as f:
        f.write("{}")
    return report_dir


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
