"""Tests for page_utils module."""

import os
from unittest.mock import patch


from conftest import create_dummy_file
from pbir_utils.page_utils import (
    hide_pages_by_type,
    set_first_page_as_active,
    remove_empty_pages,
    set_page_size,
    set_page_display_option,
)
from pbir_utils.common import load_json


class TestHidePagesByType:
    """Tests for hide_pages_by_type."""

    def test_hide_tooltip_pages(self, tmp_path):
        """Test hiding only tooltip pages."""
        report_path = str(tmp_path)

        # Tooltip page - should be hidden
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {
                "displayName": "Page1",
                "pageBinding": {"type": "Tooltip"},
                "visibility": "Visible",
            },
        )
        # Drillthrough page - should NOT be hidden
        create_dummy_file(
            tmp_path,
            "definition/pages/Page2/page.json",
            {
                "displayName": "Page2",
                "pageBinding": {"type": "Drillthrough"},
                "visibility": "Visible",
            },
        )
        # Normal page - should stay visible
        create_dummy_file(
            tmp_path,
            "definition/pages/Page3/page.json",
            {
                "displayName": "Page3",
                "pageBinding": {"type": "ReportSection"},
                "visibility": "Visible",
            },
        )

        result = hide_pages_by_type(report_path, page_type="Tooltip")

        assert result is True
        p1 = load_json(os.path.join(report_path, "definition/pages/Page1/page.json"))
        assert p1["visibility"] == "HiddenInViewMode"

        p2 = load_json(os.path.join(report_path, "definition/pages/Page2/page.json"))
        assert p2["visibility"] == "Visible"  # NOT hidden

        p3 = load_json(os.path.join(report_path, "definition/pages/Page3/page.json"))
        assert p3["visibility"] == "Visible"

    def test_hide_drillthrough_pages(self, tmp_path):
        """Test hiding only drillthrough pages."""
        report_path = str(tmp_path)

        # Tooltip page - should NOT be hidden
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {
                "displayName": "Page1",
                "pageBinding": {"type": "Tooltip"},
                "visibility": "Visible",
            },
        )
        # Drillthrough page - should be hidden
        create_dummy_file(
            tmp_path,
            "definition/pages/Page2/page.json",
            {
                "displayName": "Page2",
                "pageBinding": {"type": "Drillthrough"},
                "visibility": "Visible",
            },
        )

        result = hide_pages_by_type(report_path, page_type="Drillthrough")

        assert result is True
        p1 = load_json(os.path.join(report_path, "definition/pages/Page1/page.json"))
        assert p1["visibility"] == "Visible"  # NOT hidden

        p2 = load_json(os.path.join(report_path, "definition/pages/Page2/page.json"))
        assert p2["visibility"] == "HiddenInViewMode"

    def test_no_pages_to_hide(self, tmp_path):
        """Test when no pages of the specified type need hiding."""
        report_path = str(tmp_path)

        # Normal page only - no tooltip pages
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {
                "displayName": "Page1",
                "pageBinding": {"type": "ReportSection"},
                "visibility": "Visible",
            },
        )

        result = hide_pages_by_type(report_path, page_type="Tooltip")
        assert result is False


class TestSetFirstPageAsActive:
    """Tests for set_first_page_as_active."""

    def test_with_hidden_pages(self, tmp_path):
        """Test that the first non-hidden page is set as active."""
        report_path = str(tmp_path)

        create_dummy_file(
            tmp_path,
            "definition/pages/pages.json",
            {
                "pageOrder": ["Page1", "Page2", "Page3"],
                "activePageName": "Page1",
            },
        )

        # Page 1: Hidden
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {
                "name": "Page1",
                "displayName": "Tooltip",
                "visibility": "HiddenInViewMode",
            },
        )
        # Page 2: Also hidden
        create_dummy_file(
            tmp_path,
            "definition/pages/Page2/page.json",
            {
                "name": "Page2",
                "displayName": "Another Hidden",
                "visibility": "HiddenInViewMode",
            },
        )
        # Page 3: Visible
        create_dummy_file(
            tmp_path,
            "definition/pages/Page3/page.json",
            {
                "name": "Page3",
                "displayName": "Main Page",
                "visibility": "Visible",
            },
        )

        set_first_page_as_active(report_path)

        pages_data = load_json(os.path.join(report_path, "definition/pages/pages.json"))
        assert pages_data["activePageName"] == "Page3"

    def test_all_hidden(self, tmp_path):
        """Test fallback when all pages are hidden."""
        report_path = str(tmp_path)

        create_dummy_file(
            tmp_path,
            "definition/pages/pages.json",
            {
                "pageOrder": ["Page1", "Page2"],
                "activePageName": "Page2",
            },
        )

        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {
                "name": "Page1",
                "displayName": "Hidden 1",
                "visibility": "HiddenInViewMode",
            },
        )
        create_dummy_file(
            tmp_path,
            "definition/pages/Page2/page.json",
            {
                "name": "Page2",
                "displayName": "Hidden 2",
                "visibility": "HiddenInViewMode",
            },
        )

        with patch("builtins.print") as mock_print:
            set_first_page_as_active(report_path)
            assert any("Warning" in str(call) for call in mock_print.call_args_list)

        pages_data = load_json(os.path.join(report_path, "definition/pages/pages.json"))
        assert pages_data["activePageName"] == "Page1"

    def test_renamed_folders(self, tmp_path):
        """Test when folder names don't match page IDs."""
        report_path = str(tmp_path)

        create_dummy_file(
            tmp_path,
            "definition/pages/pages.json",
            {"pageOrder": ["Page1", "Page2"], "activePageName": "Page2"},
        )

        create_dummy_file(
            tmp_path,
            "definition/pages/Folder_Page1/page.json",
            {"name": "Page1", "displayName": "Page 1", "visibility": "Visible"},
        )
        create_dummy_file(
            tmp_path,
            "definition/pages/Page2/page.json",
            {
                "name": "Page2",
                "displayName": "Page 2",
                "visibility": "HiddenInViewMode",
            },
        )

        set_first_page_as_active(report_path)

        pages_data = load_json(os.path.join(report_path, "definition/pages/pages.json"))
        assert pages_data["activePageName"] == "Page1"


class TestRemoveEmptyPages:
    """Tests for remove_empty_pages."""

    def test_all_empty(self, tmp_path):
        """Test when all pages are empty."""
        report_path = str(tmp_path)
        create_dummy_file(
            tmp_path,
            "definition/pages/pages.json",
            {"pageOrder": ["Page1", "Page2"], "activePageName": "Page1"},
        )
        os.makedirs(
            os.path.join(report_path, "definition/pages/Page1/visuals"), exist_ok=True
        )
        os.makedirs(
            os.path.join(report_path, "definition/pages/Page2/visuals"), exist_ok=True
        )

        with patch("builtins.print"):
            remove_empty_pages(report_path)
            pages_data = load_json(
                os.path.join(report_path, "definition/pages/pages.json")
            )
            assert pages_data["pageOrder"] == ["Page1"]
            assert pages_data["activePageName"] == "Page1"

    def test_renamed_folders(self, tmp_path):
        """Test removing empty pages with renamed folders."""
        report_path = str(tmp_path)
        create_dummy_file(
            tmp_path,
            "definition/pages/pages.json",
            {"pageOrder": ["Page1", "Page2"], "activePageName": "Page1"},
        )

        create_dummy_file(
            tmp_path, "definition/pages/Folder_Page1/page.json", {"name": "Page1"}
        )
        create_dummy_file(
            tmp_path,
            "definition/pages/Folder_Page1/visuals/v1/visual.json",
            {"name": "v1"},
        )

        create_dummy_file(
            tmp_path, "definition/pages/Folder_Page2/page.json", {"name": "Page2"}
        )
        os.makedirs(
            os.path.join(report_path, "definition/pages/Folder_Page2/visuals"),
            exist_ok=True,
        )

        os.makedirs(
            os.path.join(report_path, "definition/pages/RogueFolder"), exist_ok=True
        )

        with patch("builtins.print"):
            remove_empty_pages(report_path)

        pages_data = load_json(os.path.join(report_path, "definition/pages/pages.json"))
        assert pages_data["pageOrder"] == ["Page1"]
        assert os.path.exists(
            os.path.join(report_path, "definition/pages/Folder_Page1")
        )
        assert not os.path.exists(
            os.path.join(report_path, "definition/pages/Folder_Page2")
        )
        assert not os.path.exists(
            os.path.join(report_path, "definition/pages/RogueFolder")
        )


class TestSetPageSize:
    """Tests for set_page_size."""

    def test_set_page_size(self, tmp_path):
        """Test setting page size on non-tooltip pages."""
        report_path = str(tmp_path)

        # Normal page
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {"displayName": "Page1", "width": 1000, "height": 600},
        )
        # Tooltip page - should be skipped
        create_dummy_file(
            tmp_path,
            "definition/pages/Page2/page.json",
            {"displayName": "Tooltip", "type": "Tooltip", "width": 200, "height": 100},
        )

        result = set_page_size(report_path, width=1280, height=720)

        assert result is True
        p1 = load_json(os.path.join(report_path, "definition/pages/Page1/page.json"))
        assert p1["width"] == 1280
        assert p1["height"] == 720

        p2 = load_json(os.path.join(report_path, "definition/pages/Page2/page.json"))
        assert p2["width"] == 200  # Unchanged
        assert p2["height"] == 100

    def test_no_changes_needed(self, tmp_path):
        """Test when pages already have target size."""
        report_path = str(tmp_path)

        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {"displayName": "Page1", "width": 1280, "height": 720},
        )

        result = set_page_size(report_path, width=1280, height=720)
        assert result is False


class TestSetPageDisplayOption:
    """Tests for set_page_display_option."""

    def test_set_display_option_by_display_name(self, tmp_path):
        """Test setting display option on a page matched by displayName."""
        report_path = str(tmp_path)

        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {
                "name": "abc123",
                "displayName": "Trends",
                "displayOption": "FitToWidth",
            },
        )
        create_dummy_file(
            tmp_path,
            "definition/pages/Page2/page.json",
            {
                "name": "def456",
                "displayName": "Overview",
                "displayOption": "FitToWidth",
            },
        )

        result = set_page_display_option(
            report_path, display_option="ActualSize", page="Trends"
        )

        assert result is True
        p1 = load_json(os.path.join(report_path, "definition/pages/Page1/page.json"))
        assert p1["displayOption"] == "ActualSize"

        # Other page should be unchanged
        p2 = load_json(os.path.join(report_path, "definition/pages/Page2/page.json"))
        assert p2["displayOption"] == "FitToWidth"

    def test_set_display_option_by_name(self, tmp_path):
        """Test setting display option on a page matched by internal name."""
        report_path = str(tmp_path)

        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {
                "name": "abc123",
                "displayName": "Trends",
                "displayOption": "FitToWidth",
            },
        )

        result = set_page_display_option(
            report_path, display_option="FitToPage", page="abc123"
        )

        assert result is True
        p1 = load_json(os.path.join(report_path, "definition/pages/Page1/page.json"))
        assert p1["displayOption"] == "FitToPage"

    def test_set_display_option_all_pages(self, tmp_path):
        """Test setting display option on all pages when no filter provided."""
        report_path = str(tmp_path)

        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {"name": "abc123", "displayName": "Trends", "displayOption": "FitToWidth"},
        )
        create_dummy_file(
            tmp_path,
            "definition/pages/Page2/page.json",
            {
                "name": "def456",
                "displayName": "Overview",
                "displayOption": "ActualSize",
            },
        )

        result = set_page_display_option(report_path, display_option="FitToPage")

        assert result is True
        p1 = load_json(os.path.join(report_path, "definition/pages/Page1/page.json"))
        assert p1["displayOption"] == "FitToPage"
        p2 = load_json(os.path.join(report_path, "definition/pages/Page2/page.json"))
        assert p2["displayOption"] == "FitToPage"

    def test_no_changes_needed(self, tmp_path):
        """Test when pages already have target display option."""
        report_path = str(tmp_path)

        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {"displayName": "Page1", "displayOption": "FitToWidth"},
        )

        result = set_page_display_option(report_path, display_option="FitToWidth")
        assert result is False

    def test_dry_run_mode(self, tmp_path):
        """Test that dry run does not modify files."""
        report_path = str(tmp_path)

        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {"displayName": "Page1", "displayOption": "FitToWidth"},
        )

        result = set_page_display_option(
            report_path, display_option="ActualSize", dry_run=True
        )

        assert result is True
        p1 = load_json(os.path.join(report_path, "definition/pages/Page1/page.json"))
        assert p1["displayOption"] == "FitToWidth"  # Unchanged due to dry run
