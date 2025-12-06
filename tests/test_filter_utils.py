import os
from unittest.mock import patch

from conftest import create_dummy_file
from pbir_utils.filter_utils import (
    _format_date,
    _is_date,
    _is_number,
    _format_value,
    _create_condition,
    _validate_filters,
    update_report_filters,
    sort_report_filters,
    collapse_filter_pane,
    reset_filter_pane_width,
)
from pbir_utils.common import load_json


def test_collapse_filter_pane_already_collapsed(tmp_path):
    """Test that no changes are made if filter pane is already collapsed."""
    report_path = str(tmp_path)
    create_dummy_file(
        tmp_path,
        "definition/report.json",
        {
            "objects": {
                "outspacePane": [
                    {
                        "properties": {
                            "expanded": {"expr": {"Literal": {"Value": "false"}}}
                        }
                    }
                ]
            }
        },
    )

    result = collapse_filter_pane(report_path)
    assert result is False


def test_collapse_filter_pane_expanded(tmp_path):
    """Test that filter pane is collapsed when expanded."""
    report_path = str(tmp_path)
    create_dummy_file(
        tmp_path,
        "definition/report.json",
        {
            "objects": {
                "outspacePane": [
                    {
                        "properties": {
                            "expanded": {"expr": {"Literal": {"Value": "true"}}}
                        }
                    }
                ]
            }
        },
    )

    result = collapse_filter_pane(report_path)
    assert result is True

    report_data = load_json(os.path.join(report_path, "definition/report.json"))
    assert (
        report_data["objects"]["outspacePane"][0]["properties"]["expanded"]["expr"][
            "Literal"
        ]["Value"]
        == "false"
    )


def test_collapse_filter_pane_no_outspace_pane(tmp_path):
    """Test that outspacePane is created if it doesn't exist."""
    report_path = str(tmp_path)
    create_dummy_file(
        tmp_path,
        "definition/report.json",
        {},
    )

    result = collapse_filter_pane(report_path)
    assert result is True

    report_data = load_json(os.path.join(report_path, "definition/report.json"))
    assert (
        report_data["objects"]["outspacePane"][0]["properties"]["expanded"]["expr"][
            "Literal"
        ]["Value"]
        == "false"
    )


def test_reset_filter_pane_width(tmp_path):
    """Test that filter pane width is removed from page.json."""
    report_path = str(tmp_path)
    create_dummy_file(
        tmp_path,
        "definition/pages/Page1/page.json",
        {
            "name": "Page1",
            "objects": {
                "outspacePane": [
                    {"properties": {"width": {"expr": {"Literal": {"Value": "274L"}}}}}
                ]
            },
        },
    )

    result = reset_filter_pane_width(report_path)
    assert result is True

    page_data = load_json(os.path.join(report_path, "definition/pages/Page1/page.json"))
    # objects should be removed since it's now empty
    assert "objects" not in page_data


def test_reset_filter_pane_width_no_width(tmp_path):
    """Test that no changes are made if width is not set."""
    report_path = str(tmp_path)
    create_dummy_file(
        tmp_path,
        "definition/pages/Page1/page.json",
        {"name": "Page1"},
    )

    result = reset_filter_pane_width(report_path)
    assert result is False


def test_format_date():
    assert _format_date("01-Jan-2023") == "datetime'2023-01-01T00:00:00'"


def test_is_date():
    assert _is_date("01-Jan-2023")
    assert not _is_date("2023-01-01")
    assert not _is_date(123)


def test_is_number():
    assert _is_number(123)
    assert _is_number(123.45)
    assert not _is_number("123")


def test_format_value():
    assert _format_value("01-Jan-2023") == "datetime'2023-01-01T00:00:00'"
    assert _format_value(123) == "123L"
    assert _format_value("text") == "'text'"


def test_create_condition_greater_than():
    condition = _create_condition("GreaterThan", "col", [10], "src")
    assert condition["Comparison"]["ComparisonKind"] == 1
    assert condition["Comparison"]["Right"]["Literal"]["Value"] == "10L"


def test_create_condition_between():
    condition = _create_condition("Between", "col", [10, 20], "src")
    assert "And" in condition
    assert (
        condition["And"]["Left"]["Comparison"]["ComparisonKind"] == 2
    )  # GreaterThanOrEqual
    assert (
        condition["And"]["Right"]["Comparison"]["ComparisonKind"] == 4
    )  # LessThanOrEqual


def test_create_condition_in():
    condition = _create_condition("In", "col", ["a", "b"], "src")
    assert "In" in condition
    assert len(condition["In"]["Values"]) == 2


def test_create_condition_contains():
    condition = _create_condition("Contains", "col", ["text"], "src")
    assert "Contains" in condition


def test_validate_filters():
    filters = [
        {"Condition": "GreaterThan", "Values": [10]},  # Valid
        {
            "Condition": "GreaterThan",
            "Values": [10, 20],
        },  # Invalid, requires 1 value
        {"Condition": "Between", "Values": [10]},  # Invalid, requires 2 values
        {"Condition": "Contains", "Values": [123]},  # Invalid, requires string
    ]

    valid, ignored = _validate_filters(filters)
    assert len(valid) == 1
    assert len(ignored) == 3


@patch("pbir_utils.filter_utils.load_json")
@patch("pbir_utils.filter_utils.write_json")
@patch("os.path.exists")
@patch("os.listdir")
def test_update_report_filters(
    mock_listdir, mock_exists, mock_write_json, mock_load_json
):
    mock_listdir.return_value = ["Report1.Report"]
    mock_exists.return_value = True

    # Mock report data
    mock_load_json.return_value = {
        "filterConfig": {
            "filters": [
                {
                    "field": {
                        "Column": {
                            "Property": "Col1",
                            "Expression": {"SourceRef": {"Entity": "Table1"}},
                        }
                    }
                }
            ]
        }
    }

    filters = [
        {
            "Table": "Table1",
            "Column": "Col1",
            "Condition": "GreaterThan",
            "Values": [10],
        }
    ]

    update_report_filters("dummy_path", filters)

    mock_write_json.assert_called_once()
    # Verify that the filter was updated (checking if 'filter' key was added)
    args, _ = mock_write_json.call_args
    assert "filter" in args[1]["filterConfig"]["filters"][0]


@patch("pbir_utils.filter_utils.load_json")
@patch("pbir_utils.filter_utils.write_json")
@patch("os.path.exists")
@patch("os.listdir")
def test_sort_report_filters(
    mock_listdir, mock_exists, mock_write_json, mock_load_json
):
    mock_listdir.return_value = ["Report1.Report"]
    mock_exists.return_value = True

    mock_load_json.return_value = {
        "filterConfig": {
            "filters": [
                {"field": {"Column": {"Property": "B"}}},
                {"field": {"Column": {"Property": "A"}}},
            ]
        }
    }

    sort_report_filters("dummy_path", sort_order="Ascending")

    mock_write_json.assert_called_once()
    args, _ = mock_write_json.call_args
    filter_config = args[1]["filterConfig"]
    assert filter_config["filterSortOrder"] == "Ascending"


@patch("pbir_utils.filter_utils.load_json")
@patch("pbir_utils.filter_utils.write_json")
@patch("os.path.exists")
@patch("os.listdir")
def test_sort_report_filters_selected_top(
    mock_listdir, mock_exists, mock_write_json, mock_load_json
):
    mock_listdir.return_value = ["Report1.Report"]
    mock_exists.return_value = True

    mock_load_json.return_value = {
        "filterConfig": {
            "filters": [
                {"field": {"Column": {"Property": "B"}}},  # Unselected
                {"field": {"Column": {"Property": "A"}}, "filter": {}},  # Selected
            ]
        }
    }

    sort_report_filters("dummy_path", sort_order="SelectedFilterTop")

    mock_write_json.assert_called_once()
    args, _ = mock_write_json.call_args
    filter_config = args[1]["filterConfig"]
    assert filter_config["filterSortOrder"] == "Custom"
    # Selected (A) should be first, then Unselected (B)
    assert filter_config["filters"][0]["field"]["Column"]["Property"] == "A"
    assert filter_config["filters"][1]["field"]["Column"]["Property"] == "B"


@patch("pbir_utils.filter_utils.load_json")
@patch("pbir_utils.filter_utils.write_json")
@patch("os.path.exists")
@patch("os.listdir")
def test_sort_report_filters_custom(
    mock_listdir, mock_exists, mock_write_json, mock_load_json
):
    mock_listdir.return_value = ["Report1.Report"]
    mock_exists.return_value = True

    mock_load_json.return_value = {
        "filterConfig": {
            "filters": [
                {"field": {"Column": {"Property": "C"}}},
                {"field": {"Column": {"Property": "A"}}},
                {"field": {"Column": {"Property": "B"}}},
            ]
        }
    }

    sort_report_filters("dummy_path", sort_order="Custom", custom_order=["B", "A"])

    mock_write_json.assert_called_once()
    args, _ = mock_write_json.call_args
    filter_config = args[1]["filterConfig"]
    assert filter_config["filterSortOrder"] == "Custom"
    # B should be first, then A, then C (alphabetical among remaining)
    assert filter_config["filters"][0]["field"]["Column"]["Property"] == "B"
    assert filter_config["filters"][1]["field"]["Column"]["Property"] == "A"
    assert filter_config["filters"][2]["field"]["Column"]["Property"] == "C"


@patch("pbir_utils.filter_utils.load_json")
@patch("pbir_utils.filter_utils.write_json")
@patch("os.path.exists")
@patch("os.listdir")
def test_sort_report_filters_invalid(
    mock_listdir, mock_exists, mock_write_json, mock_load_json
):
    mock_listdir.return_value = ["Report1.Report"]
    mock_exists.return_value = True

    mock_load_json.return_value = {
        "filterConfig": {"filters": [{"field": {"Column": {"Property": "A"}}}]}
    }

    sort_report_filters("dummy_path", sort_order="InvalidOrder")

    mock_write_json.assert_not_called()
