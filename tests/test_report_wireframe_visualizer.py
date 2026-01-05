from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from jinja2 import Environment, FileSystemLoader

from pbir_utils.report_wireframe_visualizer import (
    _adjust_visual_positions,
    _apply_wireframe_filters,
    display_report_wireframes,
)


# =============================================================================
# Shared Fixtures
# =============================================================================


@pytest.fixture
def display_wireframes_mocks():
    """Shared fixture for display_report_wireframes tests with common mocks."""
    with (
        patch("pbir_utils.report_wireframe_visualizer.iter_pages") as mock_iter_pages,
        patch(
            "pbir_utils.report_wireframe_visualizer.extract_visual_info"
        ) as mock_extract_visual_info,
        patch(
            "pbir_utils.report_wireframe_visualizer._get_page_order"
        ) as mock_get_order,
        patch("os.fdopen") as mock_fdopen,
        patch("tempfile.mkstemp") as mock_mkstemp,
        patch("webbrowser.open") as mock_webbrowser,
    ):
        # Default setup for temp file mocks
        mock_mkstemp.return_value = (1, "/tmp/pbir_wireframe.html")
        mock_file = MagicMock()
        mock_fdopen.return_value.__enter__.return_value = mock_file

        yield {
            "iter_pages": mock_iter_pages,
            "extract_visual_info": mock_extract_visual_info,
            "get_order": mock_get_order,
            "fdopen": mock_fdopen,
            "mkstemp": mock_mkstemp,
            "webbrowser": mock_webbrowser,
            "file": mock_file,
        }


# =============================================================================
# Shared Fixtures
# =============================================================================


def test_adjust_positions_for_groups():
    visuals = [
        {
            "id": "group1",
            "x": 10,
            "y": 10,
            "width": 200,
            "height": 200,
            "visualType": "Group",
            "parentGroupName": None,
            "isHidden": False,
        },
        {
            "id": "child1",
            "x": 5,
            "y": 5,
            "width": 50,
            "height": 50,
            "visualType": "card",
            "parentGroupName": "group1",
            "isHidden": False,
        },
        {
            "id": "orphan",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
            "visualType": "card",
            "parentGroupName": "missing_parent",
            "isHidden": False,
        },
    ]

    adjusted = _adjust_visual_positions(visuals)

    # Child should be offset by parent position
    child = next(v for v in adjusted if v["id"] == "child1")
    assert child["x"] == 15  # 5 + 10
    assert child["y"] == 15  # 5 + 10

    # Orphan should remain as is
    orphan = next(v for v in adjusted if v["id"] == "orphan")
    assert orphan["x"] == 100


def test_apply_wireframe_filters():
    pages_info = [
        {
            "id": "p1",
            "display_name": "Page 1",
            "width": 100,
            "height": 100,
            "visuals": [
                {
                    "id": "v1",
                    "visualType": "chart",
                    "parentGroupName": None,
                    "isHidden": False,
                },
                {
                    "id": "v2",
                    "visualType": "card",
                    "parentGroupName": None,
                    "isHidden": False,
                },
            ],
            "is_hidden": False,
        },
        {
            "id": "p2",
            "display_name": "Page 2",
            "width": 100,
            "height": 100,
            "visuals": [],
            "is_hidden": False,
        },
    ]

    # Filter by page
    filtered = _apply_wireframe_filters(pages_info, pages=["p1"])
    assert len(filtered) == 1
    assert filtered[0]["id"] == "p1"

    # Filter by visual type
    filtered = _apply_wireframe_filters(pages_info, visual_types=["chart"])
    assert len(filtered) == 1
    assert len(filtered[0]["visuals"]) == 1
    assert filtered[0]["visuals"][0]["id"] == "v1"

    # Filter by visual id
    filtered = _apply_wireframe_filters(pages_info, visual_ids=["v2"])
    assert len(filtered) == 1
    assert filtered[0]["visuals"][0]["id"] == "v2"


# =============================================================================
# display_report_wireframes Tests
# =============================================================================


def test_display_report_wireframes(display_wireframes_mocks):
    """Test happy path for generating and displaying wireframes."""
    mocks = display_wireframes_mocks

    # Setup iterative pages
    mocks["iter_pages"].return_value = iter(
        [
            (
                "p1",
                "dummy/report/definition/pages/Page1",
                {"name": "p1", "displayName": "Page 1", "width": 100, "height": 100},
            )
        ]
    )
    mocks["extract_visual_info"].return_value = {}
    mocks["get_order"].return_value = ["p1"]

    display_report_wireframes("dummy/report.Report")

    # Verify file writing
    mocks["mkstemp"].assert_called_once()
    mocks["file"].write.assert_called_once()

    # Verify browser opening
    mocks["webbrowser"].assert_called_once_with("file:///tmp/pbir_wireframe.html")


def test_display_report_wireframes_no_pages(display_wireframes_mocks):
    """Test that empty report (no pages) is handled gracefully."""
    mocks = display_wireframes_mocks
    mocks["iter_pages"].return_value = iter([])

    display_report_wireframes("dummy/report.Report")

    # Should not attempt to write or open browser
    mocks["mkstemp"].assert_not_called()
    mocks["webbrowser"].assert_not_called()


def test_display_report_wireframes_no_matching_filters(display_wireframes_mocks):
    """Test that no pages matching filters is handled gracefully."""
    mocks = display_wireframes_mocks

    mocks["iter_pages"].return_value = iter(
        [
            (
                "p1",
                "dummy/report/definition/pages/Page1",
                {"name": "p1", "displayName": "Page 1", "width": 100, "height": 100},
            )
        ]
    )
    mocks["extract_visual_info"].return_value = {}
    mocks["get_order"].return_value = ["p1"]

    # Filter for a page that doesn't exist
    display_report_wireframes("dummy/report.Report", pages=["nonexistent_page"])

    # Should not attempt to write or open browser
    mocks["mkstemp"].assert_not_called()
    mocks["webbrowser"].assert_not_called()


def test_display_report_wireframes_show_hidden_false(display_wireframes_mocks):
    """Test that show_hidden=False filters out hidden visuals."""
    mocks = display_wireframes_mocks

    mocks["iter_pages"].return_value = iter(
        [
            (
                "p1",
                "dummy/report/definition/pages/Page1",
                {"name": "p1", "displayName": "Page 1", "width": 100, "height": 100},
            )
        ]
    )
    mocks["extract_visual_info"].return_value = {
        "v1": {
            "x": 0,
            "y": 0,
            "width": 50,
            "height": 50,
            "visualType": "chart",
            "parentGroupName": None,
            "isHidden": True,
            "fields": {},
        },
        "v2": {
            "x": 0,
            "y": 0,
            "width": 50,
            "height": 50,
            "visualType": "card",
            "parentGroupName": None,
            "isHidden": False,
            "fields": {},
        },
    }
    mocks["get_order"].return_value = ["p1"]

    display_report_wireframes("dummy/report.Report", show_hidden=False)

    # Check the HTML content written does not include the hidden visual
    call_args = mocks["file"].write.call_args[0][0]
    assert "v2" in call_args
    # Hidden visual should not be in output (it gets filtered)
    assert "v1" not in call_args or call_args.count("v1") == 0


def test_display_report_wireframes_page_order_fallback(display_wireframes_mocks):
    """Test that page sorting gracefully handles _get_page_order exceptions."""
    mocks = display_wireframes_mocks

    mocks["iter_pages"].return_value = iter(
        [
            (
                "p1",
                "dummy/report/definition/pages/Page1",
                {"name": "p1", "displayName": "Page 1", "width": 100, "height": 100},
            )
        ]
    )
    mocks["extract_visual_info"].return_value = {}
    mocks["get_order"].side_effect = Exception("Order error")

    # Should not raise, should gracefully fallback
    display_report_wireframes("dummy/report.Report")

    mocks["file"].write.assert_called_once()


def test_apply_wireframe_filters_by_display_name():
    """Test filtering pages by display_name instead of id."""
    pages_info = [
        {
            "id": "p1",
            "display_name": "Sales Dashboard",
            "width": 100,
            "height": 100,
            "visuals": [{"id": "v1", "visualType": "chart"}],
            "is_hidden": False,
        },
        {
            "id": "p2",
            "display_name": "Revenue Report",
            "width": 100,
            "height": 100,
            "visuals": [{"id": "v2", "visualType": "card"}],
            "is_hidden": False,
        },
    ]

    # Filter by display_name
    filtered = _apply_wireframe_filters(pages_info, pages=["Sales Dashboard"])
    assert len(filtered) == 1
    assert filtered[0]["id"] == "p1"
    assert filtered[0]["display_name"] == "Sales Dashboard"


def test_apply_wireframe_filters_combined():
    """Test combined page and visual type filters."""
    pages_info = [
        {
            "id": "p1",
            "display_name": "Page 1",
            "width": 100,
            "height": 100,
            "visuals": [
                {"id": "v1", "visualType": "chart"},
                {"id": "v2", "visualType": "card"},
            ],
            "is_hidden": False,
        },
        {
            "id": "p2",
            "display_name": "Page 2",
            "width": 100,
            "height": 100,
            "visuals": [
                {"id": "v3", "visualType": "chart"},
            ],
            "is_hidden": False,
        },
    ]

    # Filter by page + visual type
    filtered = _apply_wireframe_filters(pages_info, pages=["p1"], visual_types=["card"])
    assert len(filtered) == 1
    assert filtered[0]["id"] == "p1"
    assert len(filtered[0]["visuals"]) == 1
    assert filtered[0]["visuals"][0]["id"] == "v2"


def test_adjust_visual_positions_no_parent():
    """Test that visuals with no parent (parentGroupName=None) remain unchanged."""
    visuals = [
        {
            "id": "standalone",
            "x": 50,
            "y": 75,
            "width": 100,
            "height": 100,
            "visualType": "card",
            "parentGroupName": None,
            "isHidden": False,
        },
    ]

    adjusted = _adjust_visual_positions(visuals)

    assert len(adjusted) == 1
    assert adjusted[0]["x"] == 50
    assert adjusted[0]["y"] == 75


# =============================================================================
# Template Rendering Tests
# =============================================================================


@pytest.fixture
def template_env():
    """Set up the Jinja2 environment for template testing."""
    base_dir = Path(__file__).parent.parent / "src" / "pbir_utils"
    template_dir = base_dir / "templates"
    static_dir = base_dir / "static"
    return Environment(loader=FileSystemLoader([template_dir, static_dir]))


@pytest.fixture
def sample_pages_data():
    """Sample pages data for template rendering tests."""
    return [
        {
            "id": "page1",
            "display_name": "Overview",
            "width": 1280,
            "height": 720,
            "is_hidden": False,
            "visuals": [
                {
                    "id": "visual1",
                    "x": 10,
                    "y": 20,
                    "width": 100,
                    "height": 200,
                    "visualType": "columnChart",
                    "parentGroupName": None,
                    "isHidden": False,
                    "fields": {"Sales": {"columns": ["Amount"], "measures": []}},
                },
                {
                    "id": "visual2",
                    "x": 150,
                    "y": 20,
                    "width": 80,
                    "height": 80,
                    "visualType": "card",
                    "parentGroupName": "group1",
                    "isHidden": True,
                    "fields": {},
                },
            ],
        },
        {
            "id": "page2",
            "display_name": "Details",
            "width": 1920,
            "height": 1080,
            "is_hidden": True,
            "visuals": [],
        },
    ]


def test_template_renders_report_name(template_env):
    """Test that report name is rendered in title and header."""
    template = template_env.get_template("wireframe.html.j2")
    fields_index = {"tables": {}, "fieldToVisuals": {}}
    html = template.render(
        report_name="Sales Report", pages=[], fields_index=fields_index
    )

    assert "<title>PBIR Wireframe - Sales Report</title>" in html
    assert "<h1>Sales Report</h1>" in html


def test_template_renders_page_tabs(template_env, sample_pages_data):
    """Test that page tabs are rendered with correct attributes."""
    template = template_env.get_template("wireframe.html.j2")
    fields_index = {"tables": {}, "fieldToVisuals": {}}
    html = template.render(
        report_name="Test", pages=sample_pages_data, fields_index=fields_index
    )

    # Check first page tab (should be active)
    assert 'id="tab-page1"' in html
    assert "onclick=\"openPage('page1')\"" in html
    assert 'data-page-name="Overview"' in html
    assert 'data-visual-count="2"' in html

    # Check second page tab (should have hidden-page class)
    assert 'id="tab-page2"' in html
    assert "hidden-page" in html


def test_template_renders_visual_boxes(template_env, sample_pages_data):
    """Test that visual boxes are rendered with correct positioning and attributes."""
    template = template_env.get_template("wireframe.html.j2")
    fields_index = {"tables": {}, "fieldToVisuals": {}}
    html = template.render(
        report_name="Test", pages=sample_pages_data, fields_index=fields_index
    )

    # Check visual1 attributes
    assert 'id="visual-visual1"' in html
    assert 'data-id="visual1"' in html
    assert 'data-type="columnChart"' in html
    assert 'data-width="100"' in html
    assert 'data-height="200"' in html
    assert 'data-x="10"' in html
    assert 'data-y="20"' in html
    assert "left: 10px" in html
    assert "top: 20px" in html

    # Check visual label
    assert "columnChart" in html
    assert "card" in html


def test_template_renders_hidden_visuals(template_env, sample_pages_data):
    """Test that hidden visuals have the 'hidden' class."""
    template = template_env.get_template("wireframe.html.j2")
    fields_index = {"tables": {}, "fieldToVisuals": {}}
    html = template.render(
        report_name="Test", pages=sample_pages_data, fields_index=fields_index
    )

    # visual2 is hidden, should have 'hidden' class
    # Find the visual2 div and check it has hidden class
    assert 'class="visual-box hidden"' in html


def test_template_renders_parent_group(template_env, sample_pages_data):
    """Test that parent group name is rendered as data attribute."""
    template = template_env.get_template("wireframe.html.j2")
    fields_index = {"tables": {}, "fieldToVisuals": {}}
    html = template.render(
        report_name="Test", pages=sample_pages_data, fields_index=fields_index
    )

    assert 'data-parent-group="group1"' in html


def test_template_active_page(template_env, sample_pages_data):
    """Test that the specified active page and tab are marked as active."""
    template = template_env.get_template("wireframe.html.j2")
    fields_index = {"tables": {}, "fieldToVisuals": {}}

    # Set page2 as active instead of first page
    html = template.render(
        report_name="Test",
        pages=sample_pages_data,
        fields_index=fields_index,
        active_page_id="page2",
    )

    # page2 should have 'active' class, not page1
    assert 'id="page2" class="page-container active' in html
    assert 'id="tab-page2"' in html
    assert 'class="tab-button active' in html  # The active tab is page2
    # page1 should NOT have active class on its page-container
    assert 'id="page1" class="page-container active' not in html


def test_template_empty_pages(template_env):
    """Test that template handles empty pages list gracefully."""
    template = template_env.get_template("wireframe.html.j2")
    fields_index = {"tables": {}, "fieldToVisuals": {}}
    html = template.render(
        report_name="Empty Report", pages=[], fields_index=fields_index
    )

    # Should still render valid HTML structure
    assert "<title>PBIR Wireframe - Empty Report</title>" in html
    assert '<div class="tabs"' in html
    assert '<div class="content-area">' in html
    assert "Generated by PBIR-Utils" in html


def test_template_special_characters_in_names(template_env):
    """Test that special characters in names are handled correctly."""
    pages = [
        {
            "id": "page_special",
            "display_name": "Sales & Revenue <Report>",
            "width": 1280,
            "height": 720,
            "is_hidden": False,
            "visuals": [
                {
                    "id": "vis_special",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                    "visualType": "tableEx",
                    "parentGroupName": None,
                    "isHidden": False,
                    "fields": {},
                },
            ],
        },
    ]
    template = template_env.get_template("wireframe.html.j2")
    fields_index = {"tables": {}, "fieldToVisuals": {}}
    html = template.render(
        report_name="Test & Demo", pages=pages, fields_index=fields_index
    )

    # Jinja2 auto-escapes by default, so special chars should be escaped
    assert "Sales &amp; Revenue" in html or "Sales & Revenue" in html
    assert "Test &amp; Demo" in html or "Test & Demo" in html
