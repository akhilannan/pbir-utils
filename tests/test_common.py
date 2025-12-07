from unittest.mock import patch
import pytest

from conftest import create_dummy_file
from pbir_utils.common import (
    load_json,
    write_json,
    get_report_paths,
    iter_pages,
    iter_visuals,
    walk_json_files,
    process_json_files,
    traverse_pbir_json,
    resolve_report_path,
)


def test_load_json_errors(tmp_path):
    # Test malformed JSON
    json_path = create_dummy_file(tmp_path, "bad.json", "{bad json")
    with patch("builtins.print") as mock_print:
        data = load_json(json_path)
        assert data == {}
        mock_print.assert_called()
        assert "Error: Unable to parse JSON" in mock_print.call_args[0][0]

    # Test non-existent file
    with patch("builtins.print") as mock_print:
        data = load_json("non_existent.json")
        assert data == {}
        mock_print.assert_called()
        assert "Error: Unable to read or write file" in mock_print.call_args[0][0]


def test_load_json_success(tmp_path):
    """Test successful JSON loading."""
    json_path = create_dummy_file(tmp_path, "test.json", {"key": "value"})
    data = load_json(json_path)
    assert data == {"key": "value"}


def test_write_json(tmp_path):
    """Test writing JSON to file."""
    json_path = str(tmp_path / "output.json")
    write_json(json_path, {"key": "value", "nested": {"a": 1}})

    # Read back and verify
    data = load_json(json_path)
    assert data == {"key": "value", "nested": {"a": 1}}


def test_float_precision_preserved(tmp_path):
    """Test that high-precision floats are preserved during round-trip."""
    # Original JSON with high-precision floats (as they appear in PBIR files)
    original_json = '{"x": 20, "y": 268.57142857142861, "height": 352.85714285714289}'
    json_path = tmp_path / "precision_test.json"

    # Write original content directly
    json_path.write_text(original_json, encoding="utf-8")

    # Load and save using our functions
    data = load_json(str(json_path))
    write_json(str(json_path), data)

    # Read back raw content
    result = json_path.read_text(encoding="utf-8")

    # Normalize for comparison (ignore formatting differences)
    original_normalized = original_json.replace(" ", "")
    result_normalized = result.replace(" ", "").replace("\n", "")

    assert (
        original_normalized == result_normalized
    ), f"Float precision lost!\nOriginal: {original_json}\nResult: {result}"


def test_get_report_paths(tmp_path):
    # Create dummy report structure
    report1_dir = tmp_path / "Report1.Report" / "definition"
    report1_dir.mkdir(parents=True)
    (report1_dir / "report.json").touch()

    report2_dir = tmp_path / "Report2.Report" / "definition"
    report2_dir.mkdir(parents=True)
    (report2_dir / "report.json").touch()

    # Test finding all reports in root
    paths = get_report_paths(str(tmp_path))
    assert len(paths) == 2
    assert any("Report1.Report" in p for p in paths)
    assert any("Report2.Report" in p for p in paths)

    # Test finding specific report by folder path (The Fix)
    report1_path = tmp_path / "Report1.Report"
    paths = get_report_paths(str(report1_path))
    assert len(paths) == 1
    assert "Report1.Report" in paths[0]
    assert paths[0].endswith("report.json")


def test_get_report_paths_with_reports_list(tmp_path):
    """Test get_report_paths with specific reports list."""
    report1_dir = tmp_path / "Report1.Report" / "definition"
    report1_dir.mkdir(parents=True)
    (report1_dir / "report.json").touch()

    report2_dir = tmp_path / "Report2.Report" / "definition"
    report2_dir.mkdir(parents=True)
    (report2_dir / "report.json").touch()

    # Test with specific reports list
    paths = get_report_paths(str(tmp_path), reports=["Report1"])
    assert len(paths) == 1
    assert "Report1.Report" in paths[0]


def test_get_report_paths_missing_report(tmp_path, capsys):
    """Test get_report_paths with missing report."""
    paths = get_report_paths(str(tmp_path), reports=["NonExistent"])
    assert len(paths) == 0
    captured = capsys.readouterr()
    assert "Report file not found" in captured.out


class TestIterPages:
    """Tests for iter_pages function."""

    def test_iter_pages_basic(self, tmp_path):
        """Test iterating over pages."""
        report_dir = tmp_path / "Test.Report"
        page1_data = {"name": "Page1", "displayName": "Overview"}
        page2_data = {"name": "Page2", "displayName": "Detail"}

        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page1_data)
        create_dummy_file(report_dir, "definition/pages/Page2/page.json", page2_data)

        pages = list(iter_pages(str(report_dir)))
        assert len(pages) == 2

        page_ids = [p[0] for p in pages]
        assert "Page1" in page_ids
        assert "Page2" in page_ids

    def test_iter_pages_no_pages_dir(self, tmp_path):
        """Test iter_pages with no pages directory."""
        report_dir = tmp_path / "Test.Report"
        report_dir.mkdir(parents=True)

        pages = list(iter_pages(str(report_dir)))
        assert pages == []

    def test_iter_pages_skips_files(self, tmp_path):
        """Test that iter_pages skips non-directory items."""
        report_dir = tmp_path / "Test.Report"
        page1_data = {"name": "Page1", "displayName": "Overview"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page1_data)
        # Create a file in pages dir (should be skipped)
        create_dummy_file(report_dir, "definition/pages/pages.json", {})

        pages = list(iter_pages(str(report_dir)))
        assert len(pages) == 1
        assert pages[0][0] == "Page1"

    def test_iter_pages_skips_missing_page_json(self, tmp_path):
        """Test that iter_pages skips folders without page.json."""
        report_dir = tmp_path / "Test.Report"
        (report_dir / "definition" / "pages" / "EmptyFolder").mkdir(parents=True)
        page_data = {"name": "Page1", "displayName": "Valid"}
        create_dummy_file(report_dir, "definition/pages/Page1/page.json", page_data)

        pages = list(iter_pages(str(report_dir)))
        assert len(pages) == 1


class TestIterVisuals:
    """Tests for iter_visuals function."""

    def test_iter_visuals_basic(self, tmp_path):
        """Test iterating over visuals."""
        page_dir = tmp_path / "Page1"
        visual1_data = {"name": "Visual1", "visual": {"visualType": "card"}}
        visual2_data = {"name": "Visual2", "visual": {"visualType": "slicer"}}

        create_dummy_file(page_dir, "visuals/Visual1/visual.json", visual1_data)
        create_dummy_file(page_dir, "visuals/Visual2/visual.json", visual2_data)

        visuals = list(iter_visuals(str(page_dir)))
        assert len(visuals) == 2

        visual_ids = [v[0] for v in visuals]
        assert "Visual1" in visual_ids
        assert "Visual2" in visual_ids

    def test_iter_visuals_no_visuals_dir(self, tmp_path):
        """Test iter_visuals with no visuals directory."""
        page_dir = tmp_path / "Page1"
        page_dir.mkdir(parents=True)

        visuals = list(iter_visuals(str(page_dir)))
        assert visuals == []

    def test_iter_visuals_skips_missing_visual_json(self, tmp_path):
        """Test that iter_visuals skips folders without visual.json."""
        page_dir = tmp_path / "Page1"
        (page_dir / "visuals" / "EmptyVisual").mkdir(parents=True)
        visual_data = {"name": "Visual1", "visual": {"visualType": "card"}}
        create_dummy_file(page_dir, "visuals/Valid/visual.json", visual_data)

        visuals = list(iter_visuals(str(page_dir)))
        assert len(visuals) == 1


class TestWalkJsonFiles:
    """Tests for walk_json_files function."""

    def test_walk_json_files_pattern(self, tmp_path):
        """Test walking JSON files with pattern."""
        create_dummy_file(tmp_path, "file1.json", {})
        create_dummy_file(tmp_path, "file2.json", {})
        create_dummy_file(tmp_path, "file3.txt", "text")
        create_dummy_file(tmp_path, "subdir/file4.json", {})

        files = list(walk_json_files(str(tmp_path), ".json"))
        assert len(files) == 3  # file1, file2, file4
        assert all(f.endswith(".json") for f in files)

    def test_walk_json_files_specific_pattern(self, tmp_path):
        """Test walking with specific pattern like page.json."""
        create_dummy_file(tmp_path, "page.json", {})
        create_dummy_file(tmp_path, "visual.json", {})
        create_dummy_file(tmp_path, "subdir/page.json", {})

        files = list(walk_json_files(str(tmp_path), "page.json"))
        assert len(files) == 2
        assert all("page.json" in f for f in files)

    def test_walk_json_files_invalid_directory(self, tmp_path):
        """Test walking non-existent directory."""
        files = list(walk_json_files(str(tmp_path / "nonexistent"), ".json"))
        assert files == []


class TestProcessJsonFiles:
    """Tests for process_json_files function."""

    def test_process_json_files_check_mode(self, tmp_path):
        """Test process_json_files in check mode (process=False)."""
        create_dummy_file(tmp_path, "file1.json", {"key": "value1"})
        create_dummy_file(tmp_path, "file2.json", {"key": "value2"})

        def extract_key(data, path):
            return data.get("key")

        results = process_json_files(str(tmp_path), ".json", extract_key, process=False)
        assert len(results) == 2
        assert any(r[1] == "value1" for r in results)
        assert any(r[1] == "value2" for r in results)

    def test_process_json_files_process_mode(self, tmp_path):
        """Test process_json_files in process mode."""
        create_dummy_file(tmp_path, "file1.json", {"count": 1})

        def increment_count(data, path):
            data["count"] += 1
            return True

        modified = process_json_files(
            str(tmp_path), ".json", increment_count, process=True, dry_run=False
        )
        assert modified == 1

        # Verify the change was made
        data = load_json(str(tmp_path / "file1.json"))
        assert data["count"] == 2

    def test_process_json_files_dry_run(self, tmp_path):
        """Test process_json_files in dry run mode."""
        create_dummy_file(tmp_path, "file1.json", {"count": 1})

        def increment_count(data, path):
            data["count"] += 1
            return True

        modified = process_json_files(
            str(tmp_path), ".json", increment_count, process=True, dry_run=True
        )
        assert modified == 1

        # Verify no change was made (dry run)
        data = load_json(str(tmp_path / "file1.json"))
        assert data["count"] == 1


class TestTraversePbirJson:
    """Tests for traverse_pbir_json function."""

    def test_traverse_entity(self):
        """Test traversing data with Entity key."""
        data = {"Entity": "TableName"}
        results = list(traverse_pbir_json(data))
        assert any(r[0] == "TableName" for r in results)

    def test_traverse_property(self):
        """Test traversing data with Property key."""
        data = {"Property": "ColumnName"}
        results = list(traverse_pbir_json(data))
        assert any(r[1] == "ColumnName" for r in results)

    def test_traverse_visual(self):
        """Test traversing visual data with Entity/Property references."""
        data = {
            "visual": {
                "visualType": "card",
                "singleVisual": {
                    "projections": {"Values": [{"queryRef": "Sales.Total"}]}
                },
            }
        }
        results = list(traverse_pbir_json(data))
        # Should yield queryRef with visual type as context
        assert any(r[1] == "Sales.Total" and r[2] == "card" for r in results)

    def test_traverse_measures(self):
        """Test traversing entities with measures."""
        data = {
            "entities": [
                {
                    "name": "Sales",
                    "measures": [
                        {"name": "TotalSales", "expression": "SUM(Sales[Amount])"}
                    ],
                }
            ]
        }
        results = list(traverse_pbir_json(data))
        assert any(r[0] == "Sales" and r[1] == "TotalSales" for r in results)
        assert any(r[3] == "SUM(Sales[Amount])" for r in results)

    def test_traverse_queryref(self):
        """Test traversing data with queryRef."""
        data = {"queryRef": "Sales.Amount"}
        results = list(traverse_pbir_json(data))
        assert any(r[1] == "Sales.Amount" for r in results)

    def test_traverse_list(self):
        """Test traversing list data."""
        data = [{"Entity": "Table1"}, {"Entity": "Table2"}]
        results = list(traverse_pbir_json(data))
        assert any(r[0] == "Table1" for r in results)
        assert any(r[0] == "Table2" for r in results)


class TestResolveReportPath:
    """Tests for resolve_report_path function."""

    def test_resolve_with_provided_path(self):
        """Test that provided path is returned as-is."""
        result = resolve_report_path("C:\\Reports\\Test.Report")
        assert result == "C:\\Reports\\Test.Report"

    def test_resolve_from_cwd_report_folder(self, tmp_path, monkeypatch):
        """Test resolving from CWD when in a .Report folder."""
        report_dir = tmp_path / "Test.Report"
        report_dir.mkdir()
        monkeypatch.chdir(report_dir)

        result = resolve_report_path(None)
        assert result.endswith(".Report")

    def test_resolve_from_cwd_non_report_folder(self, tmp_path, monkeypatch):
        """Test that error is raised when not in a .Report folder."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit):
            resolve_report_path(None)
