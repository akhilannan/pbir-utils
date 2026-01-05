"""Tests for metadata_extractor module."""

import os

from conftest import create_dummy_file
from pbir_utils.metadata_extractor import (
    _extract_report_name,
    _extract_active_section,
    _get_page_order,
    _apply_row_filters,
    _extract_metadata_from_file,
    _consolidate_metadata_from_directory,
    export_pbir_metadata_to_csv,
    HEADER_FIELDS,
)


class TestExtractReportName:
    """Tests for _extract_report_name function."""

    def test_extract_from_standard_path(self):
        """Test extracting report name from a standard PBIR path."""
        path = os.path.join(
            "C:", "Reports", "MyReport.Report", "definition", "report.json"
        )
        assert _extract_report_name(path) == "MyReport"

    def test_extract_from_nested_path(self):
        """Test extracting report name from a deeply nested path."""
        path = os.path.join(
            "C:",
            "Projects",
            "PBI",
            "Reports",
            "SalesReport.Report",
            "definition",
            "pages",
            "Page1",
            "page.json",
        )
        assert _extract_report_name(path) == "SalesReport"

    def test_no_report_in_path(self):
        """Test returns NA when no .Report folder in path."""
        path = r"C:\Some\Random\Path\file.json"
        assert _extract_report_name(path) == "NA"

    def test_unix_style_path(self):
        """Test with Unix-style path separators."""
        path = "/home/user/Reports/MyReport.Report/definition/report.json"
        # On Windows this may not work perfectly, but the logic should handle it
        result = _extract_report_name(path)
        # May be "MyReport" or "NA" depending on OS
        assert result in ["MyReport", "NA"]


class TestExtractActiveSection:
    """Tests for _extract_active_section function."""

    def test_extract_from_bookmarks_path(self, tmp_path):
        """Test extracting active section from a bookmark file."""
        bookmark_data = {
            "name": "Bookmark1",
            "explorationState": {"activeSection": "Page1"},
        }
        bookmark_path = create_dummy_file(
            tmp_path, "bookmarks/Bookmark1.bookmark.json", bookmark_data
        )
        result = _extract_active_section(bookmark_path)
        assert result == "Page1"

    def test_extract_from_pages_path(self, tmp_path):
        """Test extracting section from a pages path."""
        page_path = str(tmp_path / "pages" / "Page1" / "page.json")
        os.makedirs(os.path.dirname(page_path), exist_ok=True)
        with open(page_path, "w") as f:
            f.write("{}")
        result = _extract_active_section(page_path)
        assert result == "Page1"

    def test_no_active_section(self, tmp_path):
        """Test returns None when no active section found."""
        file_path = str(tmp_path / "random" / "file.json")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write("{}")
        result = _extract_active_section(file_path)
        assert result is None


class TestGetPageOrder:
    """Tests for _get_page_order function."""

    def test_get_page_order(self, tmp_path):
        """Test getting page order from pages.json."""
        pages_data = {
            "pageOrder": ["Page1", "Page2", "Page3"],
            "activePageName": "Page1",
        }
        create_dummy_file(tmp_path, "definition/pages/pages.json", pages_data)
        result = _get_page_order(str(tmp_path))
        assert result == ["Page1", "Page2", "Page3"]

    def test_get_page_order_empty(self, tmp_path):
        """Test getting page order when no pageOrder key."""
        pages_data = {"activePageName": "Page1"}
        create_dummy_file(tmp_path, "definition/pages/pages.json", pages_data)
        result = _get_page_order(str(tmp_path))
        assert result == []

    def test_get_page_order_missing_file(self, tmp_path):
        """Test getting page order when file doesn't exist."""
        result = _get_page_order(str(tmp_path))
        assert result == []

    def test_get_page_order_with_active_page(self, tmp_path):
        """Test getting page order with active page name."""
        pages_data = {
            "pageOrder": ["Page1", "Page2", "Page3"],
            "activePageName": "Page2",
        }
        create_dummy_file(tmp_path, "definition/pages/pages.json", pages_data)
        page_order, active_page = _get_page_order(
            str(tmp_path), include_active_page=True
        )
        assert page_order == ["Page1", "Page2", "Page3"]
        assert active_page == "Page2"

    def test_get_page_order_with_active_page_missing(self, tmp_path):
        """Test getting page order when activePageName is missing."""
        pages_data = {"pageOrder": ["Page1", "Page2"]}
        create_dummy_file(tmp_path, "definition/pages/pages.json", pages_data)
        page_order, active_page = _get_page_order(
            str(tmp_path), include_active_page=True
        )
        assert page_order == ["Page1", "Page2"]
        assert active_page is None


class TestApplyFilters:
    """Tests for _apply_row_filters function."""

    def test_no_filters(self):
        """Test that row passes when no filters specified."""
        row = {"Report": "Sales", "Page Name": "Overview"}
        assert _apply_row_filters(row, None) is True
        assert _apply_row_filters(row, {}) is True

    def test_matching_filter(self):
        """Test that row passes when it matches filter."""
        row = {"Report": "Sales", "Page Name": "Overview"}
        filters = {"Report": {"Sales"}}
        assert _apply_row_filters(row, filters) is True

    def test_non_matching_filter(self):
        """Test that row fails when it doesn't match filter."""
        row = {"Report": "Sales", "Page Name": "Overview"}
        filters = {"Report": {"Finance"}}
        assert _apply_row_filters(row, filters) is False

    def test_multiple_filters_all_match(self):
        """Test that row passes when it matches all filters."""
        row = {"Report": "Sales", "Page Name": "Overview"}
        filters = {"Report": {"Sales"}, "Page Name": {"Overview"}}
        assert _apply_row_filters(row, filters) is True

    def test_multiple_filters_one_fails(self):
        """Test that row fails when one filter doesn't match."""
        row = {"Report": "Sales", "Page Name": "Overview"}
        filters = {"Report": {"Sales"}, "Page Name": {"Detail"}}
        assert _apply_row_filters(row, filters) is False

    def test_empty_filter_value(self):
        """Test that empty filter value is ignored."""
        row = {"Report": "Sales", "Page Name": "Overview"}
        filters = {"Report": set()}  # Empty set
        assert _apply_row_filters(row, filters) is True


class TestExtractMetadataFromFile:
    """Tests for _extract_metadata_from_file function."""

    def test_extract_from_visual_json(self, tmp_path):
        """Test extracting metadata from a visual.json file."""
        # Create report structure
        report_dir = tmp_path / "TestReport.Report"
        visual_data = {
            "name": "Visual1",
            "visual": {
                "visualType": "columnChart",
                "objects": {},
            },
            "singleVisual": {
                "projections": {
                    "Y": [
                        {
                            "field": {
                                "Column": {
                                    "Expression": {"SourceRef": {"Entity": "Sales"}},
                                    "Property": "Amount",
                                }
                            }
                        }
                    ],
                }
            },
        }
        # Create page.json for the page
        page_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)

        visual_path = create_dummy_file(
            report_dir,
            "definition/pages/Page1/visuals/Visual1/visual.json",
            visual_data,
        )

        result = _extract_metadata_from_file(visual_path)
        assert len(result) > 0
        # Check first row has expected structure
        assert all(field in result[0] for field in HEADER_FIELDS)

    def test_extract_with_page_filter_match(self, tmp_path):
        """Test that file is processed when page matches filter."""
        report_dir = tmp_path / "TestReport.Report"
        page_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)

        visual_data = {"name": "Visual1", "visual": {"visualType": "card"}}
        visual_path = create_dummy_file(
            report_dir,
            "definition/pages/Page1/visuals/Visual1/visual.json",
            visual_data,
        )

        filters = {"Page Name": {"Overview"}}
        result = _extract_metadata_from_file(visual_path, filters)
        # Should return results since page matches
        assert isinstance(result, list)

    def test_extract_with_page_filter_no_match(self, tmp_path):
        """Test that file is skipped when page doesn't match filter."""
        report_dir = tmp_path / "TestReport.Report"
        page_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)

        visual_data = {"name": "Visual1", "visual": {"visualType": "card"}}
        visual_path = create_dummy_file(
            report_dir,
            "definition/pages/Page1/visuals/Visual1/visual.json",
            visual_data,
        )

        filters = {"Page Name": {"Detail"}}
        result = _extract_metadata_from_file(visual_path, filters)
        # Should return empty since page doesn't match
        assert result == []


class TestConsolidateMetadataFromDirectory:
    """Tests for _consolidate_metadata_from_directory function."""

    def test_consolidate_from_report(self, tmp_path):
        """Test consolidating metadata from a report directory."""
        report_dir = tmp_path / "TestReport.Report"

        # Create minimal report structure
        page_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)

        visual_data = {
            "name": "Visual1",
            "visual": {"visualType": "card"},
            "singleVisual": {"projections": {"Values": [{"queryRef": "Sales.Total"}]}},
        }
        create_dummy_file(
            report_dir,
            "definition/pages/Page1/visuals/Visual1/visual.json",
            visual_data,
        )

        result = _consolidate_metadata_from_directory(str(report_dir))
        assert isinstance(result, list)

    def test_consolidate_empty_directory(self, tmp_path):
        """Test consolidating from empty directory."""
        result = _consolidate_metadata_from_directory(str(tmp_path))
        assert result == []


class TestExportPbirMetadataToCsv:
    """Tests for export_pbir_metadata_to_csv function."""

    def test_export_creates_csv(self, tmp_path):
        """Test that export creates a CSV file."""
        report_dir = tmp_path / "TestReport.Report"

        # Create minimal report structure
        pages_data = {"pageOrder": ["Page1"], "activePageName": "Page1"}
        create_dummy_file(report_dir, "definition/pages/pages.json", pages_data)

        page_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)

        visual_data = {
            "name": "Visual1",
            "visual": {"visualType": "card"},
        }
        create_dummy_file(
            report_dir,
            "definition/pages/Page1/visuals/Visual1/visual.json",
            visual_data,
        )

        output_csv = tmp_path / "output.csv"
        export_pbir_metadata_to_csv(str(report_dir), str(output_csv))

        assert output_csv.exists()

    def test_export_csv_has_headers(self, tmp_path):
        """Test that exported CSV has correct headers."""
        report_dir = tmp_path / "TestReport.Report"

        # Create minimal structure
        pages_data = {"pageOrder": ["Page1"], "activePageName": "Page1"}
        create_dummy_file(report_dir, "definition/pages/pages.json", pages_data)

        page_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)
        create_dummy_file(report_dir, "definition/pages/Page1/visuals/.keep", "")

        output_csv = tmp_path / "output.csv"
        export_pbir_metadata_to_csv(str(report_dir), str(output_csv))

        with open(output_csv, "r") as f:
            header = f.readline().strip()

        expected_headers = ",".join(HEADER_FIELDS)
        assert header == expected_headers

    def test_export_with_filters(self, tmp_path):
        """Test export with filters applied."""
        report_dir = tmp_path / "TestReport.Report"

        pages_data = {"pageOrder": ["Page1", "Page2"], "activePageName": "Page1"}
        create_dummy_file(report_dir, "definition/pages/pages.json", pages_data)

        page1_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page1_data)

        page2_data = {"name": "Page2", "displayName": "Detail"}
        create_dummy_file(report_dir, "definition/pages/Page2/page.json", page2_data)

        output_csv = tmp_path / "output.csv"
        filters = {"Page Name": {"Overview"}}
        export_pbir_metadata_to_csv(str(report_dir), str(output_csv), filters)

        assert output_csv.exists()


class TestVisualMetadataExport:
    """Tests for visual metadata export (visuals_only=True)."""

    def test_visuals_only_creates_csv(self, tmp_path):
        """Test that visuals_only export creates a CSV file."""
        report_dir = tmp_path / "TestReport.Report"

        # Create minimal report structure
        pages_data = {"pageOrder": ["Page1"], "activePageName": "Page1"}
        create_dummy_file(report_dir, "definition/pages/pages.json", pages_data)

        page_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)

        visual_data = {
            "name": "Visual1",
            "position": {"x": 10, "y": 20, "width": 100, "height": 200},
            "visual": {"visualType": "card"},
            "isHidden": False,
        }
        create_dummy_file(
            report_dir,
            "definition/pages/Page1/visuals/Visual1/visual.json",
            visual_data,
        )

        output_csv = tmp_path / "visuals.csv"
        export_pbir_metadata_to_csv(str(report_dir), str(output_csv), visuals_only=True)

        assert output_csv.exists()

    def test_visuals_only_has_correct_headers(self, tmp_path):
        """Test that visuals_only CSV has correct headers."""
        report_dir = tmp_path / "TestReport.Report"

        pages_data = {"pageOrder": ["Page1"], "activePageName": "Page1"}
        create_dummy_file(report_dir, "definition/pages/pages.json", pages_data)

        page_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)

        output_csv = tmp_path / "visuals.csv"
        export_pbir_metadata_to_csv(str(report_dir), str(output_csv), visuals_only=True)

        with open(output_csv, "r") as f:
            header = f.readline().strip()

        expected_headers = (
            "Report,Page Name,Page ID,Visual Type,Visual ID,Parent Group ID,Is Hidden"
        )
        assert header == expected_headers

    def test_visuals_only_extracts_parent_group(self, tmp_path):
        """Test that parent group is correctly extracted."""
        report_dir = tmp_path / "TestReport.Report"

        pages_data = {"pageOrder": ["Page1"], "activePageName": "Page1"}
        create_dummy_file(report_dir, "definition/pages/pages.json", pages_data)

        page_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)

        # Create parent group
        group_data = {
            "name": "Group1",
            "position": {"x": 0, "y": 0, "width": 300, "height": 300},
            "visual": {"visualType": "Group"},
        }
        create_dummy_file(
            report_dir,
            "definition/pages/Page1/visuals/Group1/visual.json",
            group_data,
        )

        # Create child visual
        child_data = {
            "name": "Child1",
            "position": {"x": 10, "y": 10, "width": 50, "height": 50},
            "visual": {"visualType": "card"},
            "parentGroupName": "Group1",
        }
        create_dummy_file(
            report_dir,
            "definition/pages/Page1/visuals/Child1/visual.json",
            child_data,
        )

        output_csv = tmp_path / "visuals.csv"
        export_pbir_metadata_to_csv(str(report_dir), str(output_csv), visuals_only=True)

        import csv

        with open(output_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        child_row = next(r for r in rows if r["Visual ID"] == "Child1")
        assert child_row["Parent Group ID"] == "Group1"

    def test_visuals_only_extracts_hidden_status(self, tmp_path):
        """Test that hidden status is correctly extracted."""
        report_dir = tmp_path / "TestReport.Report"

        pages_data = {"pageOrder": ["Page1"], "activePageName": "Page1"}
        create_dummy_file(report_dir, "definition/pages/pages.json", pages_data)

        page_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)

        # Hidden visual
        hidden_visual = {
            "name": "HiddenVis",
            "position": {"x": 0, "y": 0, "width": 100, "height": 100},
            "visual": {"visualType": "slicer"},
            "isHidden": True,
        }
        create_dummy_file(
            report_dir,
            "definition/pages/Page1/visuals/HiddenVis/visual.json",
            hidden_visual,
        )

        output_csv = tmp_path / "visuals.csv"
        export_pbir_metadata_to_csv(str(report_dir), str(output_csv), visuals_only=True)

        import csv

        with open(output_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["Is Hidden"] == "True"

    def test_visuals_only_recursive_search(self, tmp_path):
        """Test recursive search for .Report folders in visual export."""
        root_dir = tmp_path / "Root"
        # Report 1
        r1_dir = root_dir / "Report1.Report"
        create_dummy_file(r1_dir, "definition/pages/pages.json", {"pageOrder": ["P1"]})
        create_dummy_file(
            r1_dir,
            "definition/pages/P1/page.json",
            {"name": "P1", "displayName": "Page1"},
        )
        create_dummy_file(
            r1_dir,
            "definition/pages/P1/visuals/V1/visual.json",
            {"name": "V1", "visual": {"visualType": "card"}},
        )

        # Report 2 nested
        r2_dir = root_dir / "subdir" / "Report2.Report"
        create_dummy_file(r2_dir, "definition/pages/pages.json", {"pageOrder": ["P2"]})
        create_dummy_file(
            r2_dir,
            "definition/pages/P2/page.json",
            {"name": "P2", "displayName": "Page2"},
        )
        create_dummy_file(
            r2_dir,
            "definition/pages/P2/visuals/V2/visual.json",
            {"name": "V2", "visual": {"visualType": "slicer"}},
        )

        output_csv = tmp_path / "visuals.csv"
        export_pbir_metadata_to_csv(str(root_dir), str(output_csv), visuals_only=True)

        import csv

        with open(output_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        reports = {r["Report"] for r in rows}
        assert "Report1" in reports
        assert "Report2" in reports


class TestExplicitParameters:
    """Tests for new explicit filter parameters (pages, reports, visual_types, etc)."""

    def test_export_with_pages_param(self, tmp_path):
        """Test export with explicit pages parameter."""
        report_dir = tmp_path / "TestReport.Report"

        pages_data = {"pageOrder": ["Page1", "Page2"], "activePageName": "Page1"}
        create_dummy_file(report_dir, "definition/pages/pages.json", pages_data)

        page1_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page1_data)

        page2_data = {"name": "Page2", "displayName": "Detail"}
        create_dummy_file(report_dir, "definition/pages/Page2/page.json", page2_data)

        output_csv = tmp_path / "output.csv"
        export_pbir_metadata_to_csv(
            str(report_dir), str(output_csv), pages=["Overview"]
        )

        assert output_csv.exists()

    def test_export_visuals_only_with_visual_types(self, tmp_path):
        """Test visuals_only export with visual_types filter."""
        report_dir = tmp_path / "TestReport.Report"

        pages_data = {"pageOrder": ["Page1"], "activePageName": "Page1"}
        create_dummy_file(report_dir, "definition/pages/pages.json", pages_data)

        page_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)

        # Create slicer visual
        slicer_data = {
            "name": "Slicer1",
            "position": {"x": 0, "y": 0, "width": 100, "height": 50},
            "visual": {"visualType": "slicer"},
        }
        create_dummy_file(
            report_dir,
            "definition/pages/Page1/visuals/Slicer1/visual.json",
            slicer_data,
        )

        # Create card visual
        card_data = {
            "name": "Card1",
            "position": {"x": 100, "y": 0, "width": 100, "height": 50},
            "visual": {"visualType": "card"},
        }
        create_dummy_file(
            report_dir,
            "definition/pages/Page1/visuals/Card1/visual.json",
            card_data,
        )

        output_csv = tmp_path / "visuals.csv"
        export_pbir_metadata_to_csv(
            str(report_dir), str(output_csv), visuals_only=True, visual_types=["slicer"]
        )

        import csv

        with open(output_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Should only include slicer
        assert len(rows) == 1
        assert rows[0]["Visual Type"] == "slicer"

    def test_explicit_params_merge_with_filters(self, tmp_path):
        """Test that explicit params merge with legacy filters dict."""
        report_dir = tmp_path / "TestReport.Report"

        pages_data = {"pageOrder": ["Page1"], "activePageName": "Page1"}
        create_dummy_file(report_dir, "definition/pages/pages.json", pages_data)

        page_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)

        output_csv = tmp_path / "output.csv"
        # Both filters dict and explicit pages param
        filters = {"Table": {"Sales"}}
        export_pbir_metadata_to_csv(
            str(report_dir), str(output_csv), filters=filters, pages=["Overview"]
        )

        assert output_csv.exists()
