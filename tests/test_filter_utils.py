import os
from unittest.mock import patch

import pytest
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
    configure_filter_pane,
    reset_filter_pane_width,
    clear_filters,
    _parse_condition,
    _get_target_from_field,
    _get_filter_strings,
    _parse_target_components,
    _filter_matches_criteria,
    _get_slicer_filter_data,
)
from pbir_utils.common import load_json


# --- Pytest Fixtures for common filter configs ---


@pytest.fixture
def filter_config_two_tables():
    """Returns a filter config with Table1[Col1] and Table2[Col2]."""
    return {
        "filters": [
            {
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "Table1"}},
                        "Property": "Col1",
                    }
                },
                "filter": {
                    "Where": [
                        {
                            "Condition": {
                                "Comparison": {
                                    "ComparisonKind": 1,
                                    "Right": {"Literal": {"Value": "1L"}},
                                }
                            }
                        }
                    ]
                },
            },
            {
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "Table2"}},
                        "Property": "Col2",
                    }
                },
                "filter": {
                    "Where": [
                        {
                            "Condition": {
                                "Comparison": {
                                    "ComparisonKind": 1,
                                    "Right": {"Literal": {"Value": "1L"}},
                                }
                            }
                        }
                    ]
                },
            },
        ]
    }


# --- Tests for New Helper Functions ---


def test_parse_target_components_column():
    """Test parsing a column target."""
    table, column = _parse_target_components("'Sales'[Amount]")
    assert table == "Sales"
    assert column == "Amount"


def test_parse_target_components_no_table():
    """Test parsing a target without table prefix."""
    table, column = _parse_target_components("[Amount]")
    assert table == ""
    assert column == "Amount"


def test_parse_target_components_empty():
    """Test parsing an empty target."""
    table, column = _parse_target_components("")
    assert table == ""
    assert column == ""


def test_filter_matches_criteria_no_criteria():
    """Test that no criteria matches all filters."""
    result = _filter_matches_criteria(
        "'Sales'[Amount]", "Sales", "Amount", None, None, None
    )
    assert result is True


def test_filter_matches_criteria_table_match():
    """Test table pattern matching."""
    result = _filter_matches_criteria(
        "'Sales'[Amount]", "Sales", "Amount", ["Sales"], None, None
    )
    assert result is True


def test_filter_matches_criteria_table_no_match():
    """Test table pattern not matching."""
    result = _filter_matches_criteria(
        "'Sales'[Amount]", "Sales", "Amount", ["Products"], None, None
    )
    assert result is False


def test_filter_matches_criteria_wildcard():
    """Test wildcard pattern matching."""
    result = _filter_matches_criteria(
        "'Sales'[Amount]", "Sales", "Amount", ["Sal*"], None, None
    )
    assert result is True


def test_filter_matches_criteria_field_pattern():
    """Test field pattern matching with special characters."""
    result = _filter_matches_criteria(
        "'Sales'[Amount]", "Sales", "Amount", None, None, ["'Sales'[*]"]
    )
    assert result is True


def test_get_slicer_filter_data_valid():
    """Test extracting slicer filter data from valid visual data."""
    vis_data = {
        "visual": {
            "visualType": "slicer",
            "query": {
                "queryState": {
                    "Values": {
                        "projections": [
                            {
                                "field": {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Entity": "User"}},
                                        "Property": "Type",
                                    }
                                }
                            }
                        ]
                    }
                }
            },
            "objects": {
                "general": [
                    {
                        "properties": {
                            "filter": {
                                "filter": {
                                    "Where": [{"Condition": {"In": {"Values": []}}}]
                                }
                            }
                        }
                    }
                ]
            },
        }
    }

    result = _get_slicer_filter_data(vis_data)
    assert result is not None
    filter_dict, field_def, target = result
    assert target == "'User'[Type]"


def test_get_slicer_filter_data_no_filter():
    """Test that None is returned when slicer has no filter."""
    vis_data = {
        "visual": {
            "visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": []}}},
            "objects": {"general": [{"properties": {}}]},
        }
    }

    result = _get_slicer_filter_data(vis_data)
    assert result is None


def test_get_slicer_filter_data_empty():
    """Test that None is returned for empty visual data."""
    result = _get_slicer_filter_data({})
    assert result is None


# --- Existing Tests ---


def test_configure_filter_pane_already_collapsed(tmp_path):
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

    result = configure_filter_pane(report_path, visible=True, expanded=False)
    assert result is False


def test_configure_filter_pane_collapse_expanded(tmp_path):
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

    result = configure_filter_pane(report_path, visible=True, expanded=False)
    assert result is True

    report_data = load_json(os.path.join(report_path, "definition/report.json"))
    assert (
        report_data["objects"]["outspacePane"][0]["properties"]["expanded"]["expr"][
            "Literal"
        ]["Value"]
        == "false"
    )


def test_configure_filter_pane_no_outspace_pane(tmp_path):
    """Test that outspacePane is created if it doesn't exist."""
    report_path = str(tmp_path)
    create_dummy_file(
        tmp_path,
        "definition/report.json",
        {},
    )

    result = configure_filter_pane(report_path, visible=True, expanded=False)
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

    sort_report_filters("dummy_path", sort_order="InvalidOrder")

    mock_write_json.assert_not_called()


# --- Filter Extraction Tests ---


def test_parse_condition_not():
    condition = {
        "Not": {"Expression": {"In": {"Values": [[{"Literal": {"Value": "'A'"}}]]}}}
    }
    result = _parse_condition(condition)
    assert result == "NOT (IN [('A')])"


def test_parse_condition_comparison():
    condition = {
        "Comparison": {"ComparisonKind": 1, "Right": {"Literal": {"Value": "10L"}}}
    }
    result = _parse_condition(condition)
    # 1 maps to >
    assert result == "> 10"


def test_parse_condition_and():
    condition = {
        "And": {
            "Left": {
                "Comparison": {
                    "ComparisonKind": 0,
                    "Right": {"Literal": {"Value": "1L"}},
                }
            },
            "Right": {
                "Comparison": {
                    "ComparisonKind": 3,
                    "Right": {"Literal": {"Value": "5L"}},
                }
            },
        }
    }
    result = _parse_condition(condition)
    # 0 -> =, 3 -> <
    assert result == "(= 1 AND < 5)"


def test_get_target_from_field_column():
    field = {
        "Column": {"Expression": {"SourceRef": {"Entity": "Table"}}, "Property": "Col"}
    }
    assert _get_target_from_field(field) == "'Table'[Col]"


def test_get_target_from_field_measure():
    field = {
        "Measure": {
            "Expression": {"SourceRef": {"Entity": "Table"}},
            "Property": "Meas",
        }
    }
    assert _get_target_from_field(field) == "'Table'[Meas]"


@patch("pbir_utils.filter_utils.load_json")
@patch("pbir_utils.filter_utils.console.print_dry_run")
@patch("pbir_utils.filter_utils.console.print_info")
@patch("os.path.exists")
def test_extract_report_filters(
    mock_exists, mock_print_info, mock_print_dry_run, mock_load_json
):
    mock_exists.return_value = True

    mock_load_json.return_value = {
        "filterConfig": {
            "filters": [
                {
                    "field": {
                        "Column": {
                            "Expression": {"SourceRef": {"Entity": "Sales"}},
                            "Property": "Region",
                        }
                    },
                    "filter": {
                        "Where": [
                            {
                                "Condition": {
                                    "In": {
                                        "Values": [[{"Literal": {"Value": "'North'"}}]]
                                    }
                                }
                            }
                        ]
                    },
                }
            ]
        }
    }

    clear_filters("dummy_report_path")

    # Filter values are printed via print_dry_run when dry_run=True (default)
    found = False
    for call in mock_print_dry_run.call_args_list:
        if "'Sales'[Region] : IN [('North')]" in call[0][0]:
            found = True
            break
    assert found


@patch("pbir_utils.common.load_json")
@patch("pbir_utils.filter_utils.load_json")
@patch("pbir_utils.filter_utils.console.print_dry_run")
@patch("pbir_utils.filter_utils.console.print_info")
@patch("os.path.exists")
@patch("os.listdir")
@patch("os.path.isdir")
def test_extract_page_filters(
    mock_isdir,
    mock_listdir,
    mock_exists,
    mock_print_info,
    mock_print_dry_run,
    mock_load_json,
    mock_common_load_json,
):
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_listdir.return_value = ["Page1"]

    # Needs side_effect for load_json to handle report.json and page.json
    def load_json_side_effect(path):
        if "report.json" in path:
            return {}
        if "page.json" in path:
            return {
                "displayName": "My Page",
                "filterConfig": {
                    "filters": [
                        {
                            "field": {
                                "Measure": {
                                    "Expression": {"SourceRef": {"Entity": "Sales"}},
                                    "Property": "Total",
                                }
                            },
                            "filter": {
                                "Where": [
                                    {
                                        "Condition": {
                                            "Comparison": {
                                                "ComparisonKind": 1,
                                                "Right": {"Literal": {"Value": "100L"}},
                                            }
                                        }
                                    }
                                ]
                            },
                        }
                    ]
                },
            }
        return {}

    mock_load_json.side_effect = load_json_side_effect
    mock_common_load_json.side_effect = load_json_side_effect

    clear_filters("dummy_path", show_page_filters=True)

    found_header = False
    found_value = False

    for call in mock_print_info.call_args_list:
        arg = call[0][0]
        if "[Page] My Page (Page1)" in arg:
            found_header = True

    # Filter values are printed via print_dry_run when dry_run=True (default)
    for call in mock_print_dry_run.call_args_list:
        arg = call[0][0]
        # Look for value without 'L' suffix
        if "> 100" in arg and "100L" not in arg:
            found_value = True

    assert found_header
    assert found_value


@patch("pbir_utils.common.load_json")
@patch("pbir_utils.filter_utils.load_json")
@patch("pbir_utils.filter_utils.console.print_info")
@patch("os.path.exists")
@patch("os.listdir")
@patch("os.path.isdir")
def test_extract_page_filters_empty_target(
    mock_isdir,
    mock_listdir,
    mock_exists,
    mock_print,
    mock_load_json,
    mock_common_load_json,
):
    """Test extracting specific page filters when no filters exist."""
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_listdir.return_value = ["Page1"]

    def load_json_side_effect(path):
        if "page.json" in path:
            return {"displayName": "My Page", "filterConfig": {}}  # No filters
        return {}

    mock_load_json.side_effect = load_json_side_effect
    mock_common_load_json.side_effect = load_json_side_effect

    clear_filters("dummy", target_page="Page1")

    # Should print "Page Filters: None"
    has_header = any(
        "[Page] My Page (Page1)" in call[0][0] for call in mock_print.call_args_list
    )
    has_none = any(
        "Page Filters: None" in call[0][0] for call in mock_print.call_args_list
    )
    assert has_header
    assert has_none


@patch("pbir_utils.common.load_json")
@patch("pbir_utils.filter_utils.load_json")
@patch("pbir_utils.filter_utils.console.print_dry_run")
@patch("pbir_utils.filter_utils.console.print_info")
@patch("os.path.exists")
@patch("os.listdir")
@patch("os.path.isdir")
def test_extract_visual_shows_page_filters(
    mock_isdir,
    mock_listdir,
    mock_exists,
    mock_print_info,
    mock_print_dry_run,
    mock_load_json,
    mock_common_load_json,
):
    """Test that targeting a visual automagically shows page filters (context)."""
    mock_exists.return_value = True
    mock_isdir.return_value = True

    # Return "MyVisual" for both pages (as page_id) and visuals (as visual_id) for simplicity
    # This ensures target_visual="MyVisual" matches the visual_id found.
    mock_listdir.return_value = ["MyVisual"]

    # Needs side_effect for load_json to handle report.json, page.json, and visual.json
    def load_json_side_effect(path):
        if "page.json" in path:
            return {
                "displayName": "My Page",
                "filterConfig": {
                    "filters": [
                        {
                            "field": {"Column": {"Property": "PageFilterProp"}},
                            "filter": {
                                "Where": [
                                    {
                                        "Condition": {
                                            "Comparison": {
                                                "ComparisonKind": 1,
                                                "Right": {"Literal": {"Value": "10L"}},
                                            }
                                        }
                                    }
                                ]
                            },
                        }
                    ]
                },
            }
        if "visual.json" in path:
            return {
                "name": "MyVisual",
                "visual": {"visualType": "chart"},
                "filterConfig": {},  # empty visual filter for simplicity, we focus on page filter appearance
            }
        return {}

    mock_load_json.side_effect = load_json_side_effect
    mock_common_load_json.side_effect = load_json_side_effect

    # Target specific visual, NOT explicitly asking for page filters
    clear_filters("dummy", target_visual="MyVisual")

    # We expect "Page Filters:" header in print_info
    has_page_header = any(
        "Page Filters:" in call[0][0] for call in mock_print_info.call_args_list
    )

    # Filter values are printed via print_dry_run
    has_prop = any(
        "PageFilterProp" in call[0][0] for call in mock_print_dry_run.call_args_list
    )

    # We do NOT expect "Page Filters: None"
    has_none = any(
        "Page Filters: None" in call[0][0] for call in mock_print_info.call_args_list
    )

    assert has_page_header
    assert has_prop
    assert not has_none


def test_parse_condition_datespan():
    """Test parsing of DateSpan (Advanced Filtering) conditions."""
    condition = {
        "Comparison": {
            "ComparisonKind": 4,  # LessThanOrEqual
            "Right": {
                "DateSpan": {
                    "Expression": {
                        "Literal": {"Value": "datetime'2025-12-01T00:00:00'"}
                    },
                    "TimeUnit": 5,
                }
            },
        }
    }
    result = _parse_condition(condition)
    # Should extract the datetime value
    assert "2025-12-01" in result
    assert "Expression" not in result


@patch("pbir_utils.common.load_json")
@patch("pbir_utils.filter_utils.load_json")
@patch("pbir_utils.filter_utils.console.print_dry_run")
@patch("pbir_utils.filter_utils.console.print_info")
@patch("os.path.exists")
@patch("os.listdir")
@patch("os.path.isdir")
def test_extract_slicer_filters(
    mock_isdir,
    mock_listdir,
    mock_exists,
    mock_print_info,
    mock_print_dry_run,
    mock_load_json,
    mock_common_load_json,
):
    """Test extracting filters from a Slicer visual."""
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_listdir.return_value = ["SlicerVisual"]

    def load_json_side_effect(path):
        if "visual.json" in path:
            return {
                "name": "MySlicer",
                "visual": {
                    "visualType": "slicer",
                    "query": {
                        "queryState": {
                            "Values": {
                                "projections": [
                                    {
                                        "field": {
                                            "Column": {
                                                "Expression": {
                                                    "SourceRef": {"Entity": "User_TB"}
                                                },
                                                "Property": "user_type",
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    },
                    "objects": {
                        "general": [
                            {
                                "properties": {
                                    "filter": {
                                        "filter": {
                                            "Where": [
                                                {
                                                    "Condition": {
                                                        "In": {
                                                            "Values": [
                                                                [
                                                                    {
                                                                        "Literal": {
                                                                            "Value": "'driver'"
                                                                        }
                                                                    }
                                                                ]
                                                            ]
                                                        }
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        ]
                    },
                },
            }
        # Return minimal dicts for report/page to allow flow to reach visual
        if "page.json" in path:
            return {"displayName": "Page1", "filterConfig": {}}
        return {}

    mock_load_json.side_effect = load_json_side_effect
    mock_common_load_json.side_effect = load_json_side_effect

    # Use MySlicer to match the visual name in the mocked JSON
    clear_filters("dummy", target_visual="MySlicer")

    # Check if the slicer header was printed via print_info
    # And the filter value was printed via print_dry_run
    found_slicer_header = False
    found_slicer_filter = False

    for call in mock_print_info.call_args_list:
        arg = call[0][0]
        if "Slicer Filters:" in arg:
            found_slicer_header = True

    # Filter values are printed via print_dry_run when dry_run=True (default)
    for call in mock_print_dry_run.call_args_list:
        arg = call[0][0]
        if "'User_TB'[user_type]" in arg and "driver" in arg:
            found_slicer_filter = True

    assert found_slicer_header
    assert found_slicer_filter


@patch("pbir_utils.common.load_json")
@patch("pbir_utils.filter_utils.load_json")
@patch("pbir_utils.filter_utils.console.print_dry_run")
@patch("pbir_utils.filter_utils.console.print_info")
@patch("os.path.exists")
@patch("os.listdir")
@patch("os.path.isdir")
def test_extract_page_with_slicers_implicit(
    mock_isdir,
    mock_listdir,
    mock_exists,
    mock_print_info,
    mock_print_dry_run,
    mock_load_json,
    mock_common_load_json,
):
    """Test that requesting a page also shows its slicers' filters implicitly."""
    mock_exists.return_value = True
    mock_isdir.return_value = True

    # Setup mock returns
    def listdir_side_effect(path):
        if path.endswith("visuals"):
            return ["MySlicer", "RegularVisual"]
        if "pages" in path:
            return ["PageWithSlicer"]
        return []

    mock_listdir.side_effect = listdir_side_effect

    def load_json_side_effect(path):
        if "page.json" in path:
            return {"displayName": "PageWithSlicer", "filterConfig": {}}
        if "MySlicer" in path and "visual.json" in path:
            return {
                "name": "MySlicer",
                "visual": {
                    "visualType": "slicer",
                    "query": {
                        "queryState": {
                            "Values": {
                                "projections": [
                                    {
                                        "field": {
                                            "Column": {
                                                "Expression": {
                                                    "SourceRef": {"Entity": "User"}
                                                },
                                                "Property": "UserType",
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    },
                    "objects": {
                        "general": [
                            {
                                "properties": {
                                    "filter": {
                                        "filter": {
                                            "Where": [
                                                {
                                                    "Condition": {
                                                        "In": {
                                                            "Values": [
                                                                [
                                                                    {
                                                                        "Literal": {
                                                                            "Value": "'Driver'"
                                                                        }
                                                                    }
                                                                ]
                                                            ]
                                                        }
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        ]
                    },
                },
            }
        if "RegularVisual" in path and "visual.json" in path:
            return {
                "name": "RegularVisual",
                "visual": {"visualType": "chart"},
                "filterConfig": {
                    "filters": [
                        {
                            "field": {"Column": {"Property": "Sales"}},
                            "filter": {
                                "Where": [
                                    {
                                        "Condition": {
                                            "Comparison": {
                                                "Right": {"Literal": {"Value": "100L"}}
                                            }
                                        }
                                    }
                                ]
                            },
                        }
                    ]
                },
            }
        return {}

    mock_load_json.side_effect = load_json_side_effect
    mock_common_load_json.side_effect = load_json_side_effect

    # Call with target_page ONLY (no visual filters requested explicitly)
    clear_filters("dummy", target_page="PageWithSlicer")

    # Expect:
    # 1. Page Header
    # 2. Slicer filter printed UNDER "Slicer Filters:"
    # 3. Regular Visual filter NOT printed (because show_visual_filters=False)

    has_slicer_header = any(
        "Slicer Filters:" in call[0][0] for call in mock_print_info.call_args_list
    )
    # Slicer filter values are printed via print_dry_run
    has_slicer_filter = any(
        "'User'[UserType] : IN [('Driver')]" in call[0][0]
        for call in mock_print_dry_run.call_args_list
    )
    # Check that regular visual filter is NOT in either output
    has_regular_info = any(
        "Sales" in call[0][0] and ">" in call[0][0]
        for call in mock_print_info.call_args_list
    )
    has_regular_dry = any(
        "Sales" in call[0][0] and ">" in call[0][0]
        for call in mock_print_dry_run.call_args_list
    )

    assert has_slicer_header, "Should see 'Slicer Filters:' header"
    assert has_slicer_filter, "Should see extracted slicer value"
    assert (
        not has_regular_info and not has_regular_dry
    ), "Regular visual filters should be hidden unless requested"


# --- Filtering Criteria Tests ---


def test_filtering_criteria_no_filters():
    """Test filtering when no criteria provided (should return all)."""
    filter_config = {
        "filters": [
            {
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "Table1"}},
                        "Property": "Col1",
                    }
                },
                "filter": {
                    "Where": [
                        {
                            "Condition": {
                                "Comparison": {
                                    "ComparisonKind": 1,
                                    "Right": {"Literal": {"Value": "1L"}},
                                }
                            }
                        }
                    ]
                },
            },
            {
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "Table2"}},
                        "Property": "Col2",
                    }
                },
                "filter": {
                    "Where": [
                        {
                            "Condition": {
                                "Comparison": {
                                    "ComparisonKind": 1,
                                    "Right": {"Literal": {"Value": "1L"}},
                                }
                            }
                        }
                    ]
                },
            },
        ]
    }

    results = _get_filter_strings(filter_config)
    assert len(results) == 2


def test_filtering_criteria_table_match():
    """Test filtering by table name."""
    filter_config = {
        "filters": [
            {
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "Table1"}},
                        "Property": "Col1",
                    }
                },
                "filter": {
                    "Where": [
                        {
                            "Condition": {
                                "Comparison": {
                                    "ComparisonKind": 1,
                                    "Right": {"Literal": {"Value": "1L"}},
                                }
                            }
                        }
                    ]
                },
            },
            {
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "Table2"}},
                        "Property": "Col2",
                    }
                },
                "filter": {
                    "Where": [
                        {
                            "Condition": {
                                "Comparison": {
                                    "ComparisonKind": 1,
                                    "Right": {"Literal": {"Value": "1L"}},
                                }
                            }
                        }
                    ]
                },
            },
        ]
    }

    # Exact match
    results = _get_filter_strings(filter_config, include_tables=["Table1"])
    assert len(results) == 1
    assert "'Table1'[Col1]" in results[0]

    # Wildcard match
    results = _get_filter_strings(filter_config, include_tables=["Table*"])
    assert len(results) == 2


def test_filtering_criteria_column_match():
    """Test filtering by column name."""
    filter_config = {
        "filters": [
            {
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "Table1"}},
                        "Property": "Year",
                    }
                },
                "filter": {
                    "Where": [
                        {
                            "Condition": {
                                "Comparison": {
                                    "ComparisonKind": 1,
                                    "Right": {"Literal": {"Value": "2023L"}},
                                }
                            }
                        }
                    ]
                },
            },
            {
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "Table1"}},
                        "Property": "Month",
                    }
                },
                "filter": {
                    "Where": [
                        {
                            "Condition": {
                                "Comparison": {
                                    "ComparisonKind": 1,
                                    "Right": {"Literal": {"Value": "1L"}},
                                }
                            }
                        }
                    ]
                },
            },
        ]
    }

    results = _get_filter_strings(filter_config, include_columns=["Year"])
    assert len(results) == 1
    assert "'Table1'[Year]" in results[0]


def test_filtering_criteria_multi_match():
    """Test filtering by multiple tables and columns."""
    filter_config = {
        "filters": [
            {
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "Sales"}},
                        "Property": "Amount",
                    }
                },
                "filter": {
                    "Where": [
                        {
                            "Condition": {
                                "Comparison": {
                                    "ComparisonKind": 1,
                                    "Right": {"Literal": {"Value": "100L"}},
                                }
                            }
                        }
                    ]
                },
            },
            {
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "Sales"}},
                        "Property": "Date",
                    }
                },
                "filter": {
                    "Where": [
                        {
                            "Condition": {
                                "Comparison": {
                                    "ComparisonKind": 1,
                                    "Right": {"Literal": {"Value": "1L"}},
                                }
                            }
                        }
                    ]
                },
            },
            {
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "Budget"}},
                        "Property": "Amount",
                    }
                },
                "filter": {
                    "Where": [
                        {
                            "Condition": {
                                "Comparison": {
                                    "ComparisonKind": 1,
                                    "Right": {"Literal": {"Value": "1000L"}},
                                }
                            }
                        }
                    ]
                },
            },
        ]
    }

    # Tables: Sales OR Budget AND Columns: Amount
    results = _get_filter_strings(
        filter_config, include_tables=["Sales", "Budget"], include_columns=["Amount"]
    )
    assert len(results) == 2
    assert any("'Sales'[Amount]" in r for r in results)
    assert any("'Budget'[Amount]" in r for r in results)

    # Tables: Sales AND Columns: Amount OR Date
    results = _get_filter_strings(
        filter_config, include_tables=["Sales"], include_columns=["Amount", "Date"]
    )
    assert len(results) == 2


def test_filtering_measure_match():
    """Test filtering works for measures too."""
    filter_config = {
        "filters": [
            {
                "field": {
                    "Measure": {
                        "Expression": {"SourceRef": {"Entity": "Sales"}},
                        "Property": "Total Amount",
                    }
                },
                "filter": {
                    "Where": [
                        {
                            "Condition": {
                                "Comparison": {
                                    "ComparisonKind": 1,
                                    "Right": {"Literal": {"Value": "100L"}},
                                }
                            }
                        }
                    ]
                },
            },
        ]
    }

    results = _get_filter_strings(filter_config, include_columns=["Total*"])
    assert len(results) == 1
    assert "[Total Amount]" in results[0]
