"""Tests for error handling paths in common utilities."""

import pytest
import json
from unittest.mock import patch
from pbir_utils.common import (
    load_json,
    resolve_report_path,
    get_report_paths,
    iter_pages,
    iter_visuals,
    walk_json_files,
    write_json,
)


class TestCommonErrorHandling:
    """Tests for error handling in common.py."""

    @patch("pbir_utils.common.console")
    @patch("builtins.open")
    def test_load_json_io_error(self, mock_open, mock_console):
        """Test load_json with an IOError."""
        mock_open.side_effect = IOError("Permissions denied")
        result = load_json("invalid/path.json")
        assert result == {}
        mock_console.print_error.assert_called()
        assert (
            "Unable to read or write file" in mock_console.print_error.call_args[0][0]
        )

    def test_load_json_actual_decode_error(self, tmp_path):
        """Test load_json with an actual malformed file."""
        p = tmp_path / "bad.json"
        p.write_text("invalid { json")
        with patch("pbir_utils.common.console") as mock_console:
            result = load_json(str(p))
            assert result == {}
            mock_console.print_error.assert_called_with(
                f"Unable to parse JSON in file: {str(p)}"
            )

    @patch("pbir_utils.common.console")
    @patch("sys.exit")
    def test_resolve_report_path_error(self, mock_exit, mock_console):
        """Test resolve_report_path when no path provided and not in .Report folder."""
        with patch("os.getcwd", return_value="C:\\NotAReport"):
            # Mock os.path.isdir to return True for any path to avoid other errors
            with patch("os.path.isdir", return_value=True):
                resolve_report_path(None)
                mock_console.print_error.assert_called()
                mock_exit.assert_called_with(1)

    @patch("pbir_utils.common.console")
    def test_get_report_paths_not_found(self, mock_console, tmp_path):
        """Test get_report_paths when report files are missing."""
        base = tmp_path / "Project"
        base.mkdir()
        (base / "My.Report").mkdir()

        # definition/report.json is missing
        paths = get_report_paths(str(base), reports=["My"])
        assert paths == []
        mock_console.print_warning.assert_called()
        assert "Report file not found" in mock_console.print_warning.call_args[0][0]

    def test_iter_pages_missing_dir(self, tmp_path):
        """Test iter_pages with missing pages directory."""
        pages = list(iter_pages(str(tmp_path)))
        assert pages == []

    def test_iter_visuals_missing_dir(self, tmp_path):
        """Test iter_visuals with missing visuals directory."""
        visuals = list(iter_visuals(str(tmp_path)))
        assert visuals == []

    def test_walk_json_files_missing_dir(self):
        """Test walk_json_files with non-existent directory."""
        files = list(walk_json_files("non/existent/dir", ".json"))
        assert files == []

    def test_walk_json_files_traversal_prevention(self, tmp_path):
        """Test walk_json_files path traversal logic."""
        base = tmp_path / "base"
        base.mkdir()
        secret = tmp_path / "secret.json"
        secret.write_text("{}")

        # This is a bit tricky to mock os.walk to return a path outside base
        with patch("os.walk") as mock_walk:
            mock_walk.return_value = [
                (str(base), [], ["file.json"]),
                (str(tmp_path), [], ["secret.json"]),
            ]
            files = list(walk_json_files(str(base), ".json"))
            # Only file.json should be yielded, secret.json is excluded by commonpath check
            assert len(files) == 1
            assert "file.json" in files[0]

    @patch("pbir_utils.common.console")
    @patch("builtins.open")
    def test_write_json_permission_denied(self, mock_open, mock_console):
        """Test write_json with permission error."""
        mock_open.side_effect = PermissionError("Access denied")
        with pytest.raises(PermissionError):
            write_json("path.json", {"a": 1})


class TestFilterEdgeCases:
    """Tests for edge cases in filter_utils.py."""

    @patch("pbir_utils.filter_utils.console")
    @patch("pbir_utils.filter_utils.load_json")
    @patch("pbir_utils.filter_utils.write_json")
    @patch("pbir_utils.filter_utils.iter_pages")
    def test_clear_filters_with_table_wildcard(
        self, mock_pages, mock_write, mock_load, mock_console
    ):
        """Test clear_filters with wildcard table names."""
        from pbir_utils.filter_utils import clear_filters

        mock_pages.return_value = iter(
            [
                (
                    "p1",
                    "path/p1",
                    {
                        "name": "p1",
                        "displayName": "Page 1",
                        "filterConfig": {
                            "filters": [
                                {
                                    "field": {
                                        "Column": {
                                            "Expression": {
                                                "SourceRef": {"Entity": "DimSales"}
                                            },
                                            "Property": "C1",
                                        }
                                    },
                                    "filter": {
                                        "Where": [
                                            {
                                                "Condition": {
                                                    "In": {
                                                        "Values": [
                                                            [
                                                                {
                                                                    "Literal": {
                                                                        "Value": "v1"
                                                                    }
                                                                }
                                                            ]
                                                        ]
                                                    }
                                                }
                                            }
                                        ]
                                    },
                                    "name": "f1",
                                },
                                {
                                    "field": {
                                        "Column": {
                                            "Expression": {
                                                "SourceRef": {"Entity": "DimDate"}
                                            },
                                            "Property": "C2",
                                        }
                                    },
                                    "filter": {
                                        "Where": [
                                            {
                                                "Condition": {
                                                    "In": {
                                                        "Values": [
                                                            [
                                                                {
                                                                    "Literal": {
                                                                        "Value": "v2"
                                                                    }
                                                                }
                                                            ]
                                                        ]
                                                    }
                                                }
                                            }
                                        ]
                                    },
                                    "name": "f2",
                                },
                            ],
                        },
                    },
                )
            ]
        )
        mock_load.return_value = {}

        # Mock os.path.exists to return True for report.json
        with patch("os.path.exists", return_value=True):
            # Actually CLEAR filters (dry_run=False) to trigger the del f["filter"]
            clear_filters(
                "dummy", include_tables=["Dim*"], dry_run=False, show_page_filters=True
            )

        # Verify write_json was called with modified data
        assert mock_write.called
        data = mock_write.call_args[0][1]
        filters = data["filterConfig"]["filters"]
        # Both should be cleared (no "filter" key)
        assert "filter" not in filters[0]
        assert "filter" not in filters[1]

    def test_slicer_detection_variants(self):
        """Test detection of various slicer types with valid structured data."""
        from pbir_utils.filter_utils import _get_slicer_filter_data

        def create_slicer_data(v_type):
            return {
                "visual": {
                    "visualType": v_type,
                    "objects": {
                        "general": [
                            {"properties": {"filter": {"filter": {"Where": []}}}}
                        ]
                    },
                    "query": {
                        "queryState": {
                            "Values": {
                                "projections": [
                                    {"field": {"Entity": "T", "Property": "C"}}
                                ]
                            }
                        }
                    },
                }
            }

        # Chiclet Slicer
        result = _get_slicer_filter_data(create_slicer_data("chicletSlicer"))
        assert result is not None

        # Standard Slicer
        result = _get_slicer_filter_data(create_slicer_data("slicer"))
        assert result is not None

        # Not a slicer
        visual_data = {"visual": {"visualType": "barChart"}}
        result = _get_slicer_filter_data(visual_data)
        assert result is None

    def test_clear_filters_summary_actual(self, tmp_path):
        """Test clear_filters with summary=True and dry_run=False."""
        from pbir_utils.filter_utils import clear_filters

        # Setup a dummy report structure
        report_dir = tmp_path / "Test.Report"
        report_dir.mkdir()
        def_dir = report_dir / "definition"
        def_dir.mkdir()
        pages_dir = def_dir / "pages"
        pages_dir.mkdir()

        # Report level filter
        report_json = def_dir / "report.json"
        report_json.write_text(
            json.dumps(
                {
                    "filterConfig": {
                        "filters": [
                            {
                                "field": {"Entity": "T1", "Property": "C1"},
                                "filter": {
                                    "Where": [
                                        {
                                            "Condition": {
                                                "Comparison": {
                                                    "ComparisonKind": 0,
                                                    "Right": {
                                                        "Literal": {"Value": "1"}
                                                    },
                                                }
                                            }
                                        }
                                    ]
                                },
                            }
                        ]
                    }
                }
            )
        )

        # Page level filter
        p1_dir = pages_dir / "p1"
        p1_dir.mkdir()
        page_json = p1_dir / "page.json"
        page_json.write_text(
            json.dumps(
                {
                    "name": "p1",
                    "displayName": "Page1",
                    "filterConfig": {
                        "filters": [
                            {
                                "field": {"Entity": "T2", "Property": "C2"},
                                "filter": {
                                    "Where": [
                                        {
                                            "Condition": {
                                                "Comparison": {
                                                    "ComparisonKind": 0,
                                                    "Right": {
                                                        "Literal": {"Value": "2"}
                                                    },
                                                }
                                            }
                                        }
                                    ]
                                },
                            }
                        ]
                    },
                }
            )
        )

        with patch("pbir_utils.filter_utils.console") as mock_console:
            result = clear_filters(
                str(report_dir), show_page_filters=True, dry_run=False, summary=True
            )
            assert result is True
            # Check if summary was printed
            mock_console.print_success.assert_called()
            summary_msg = mock_console.print_success.call_args[0][0]
            assert "Cleared" in summary_msg
            assert "report filter" in summary_msg
            assert "page filter" in summary_msg

    def test_literal_display_value_edge_cases(self):
        """Test _get_literal_display_value with DateSpan and numeric suffixes."""
        from pbir_utils.filter_utils import _get_literal_display_value

        # Decimal suffix
        expr = {"Literal": {"Value": "123.45D"}}
        assert _get_literal_display_value(expr) == "123.45"

        # Long suffix
        expr = {"Literal": {"Value": "1000L"}}
        assert _get_literal_display_value(expr) == "1000"

        # DateSpan
        expr = {"DateSpan": {"Expression": {"Literal": {"Value": "'2023-01-01'"}}}}
        assert _get_literal_display_value(expr) == "'2023-01-01'"

        # Fallback
        assert _get_literal_display_value({"Unknown": 1}) == "Expression"
        assert _get_literal_display_value(123) == "123"


class TestMeasureEdgeCases:
    """Tests for edge cases in pbir_measure_utils.py."""

    def test_remove_measures_no_measures_file(self, tmp_path):
        """Test remove_measures when measures.json doesn't exist."""
        from pbir_utils.pbir_measure_utils import remove_measures

        with patch("pbir_utils.pbir_measure_utils.console") as mock_console:
            remove_measures(str(tmp_path))
            mock_console.print_info.assert_called()
            # It should warn that no measures found
            assert any(
                "No measures found" in str(c)
                for c in mock_console.print_info.call_args_list
            )
