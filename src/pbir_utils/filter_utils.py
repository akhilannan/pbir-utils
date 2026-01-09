"""
Filter management utilities for Power BI reports.

Contains functions for updating, sorting, and configuring filters
in PBIR reports.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from .common import (
    load_json,
    write_json,
    get_report_paths,
    process_json_files,
)
from .console_utils import console

__all__ = [
    "update_report_filters",
    "sort_report_filters",
    "configure_filter_pane",
    "reset_filter_pane_width",
    "get_target_from_field",
    "parse_target_components",
]


def get_target_from_field(field_data: dict) -> str:
    """
    Extract the target reference from a field definition.

    Extracts the target (Table[Column/Measure/Level]) from the field definition
    dictionary commonly found in Power BI filter configurations.

    Args:
        field_data: The field definition dictionary from a filter.

    Returns:
        Formatted string like "'TableName'[ColumnName]" or "Unknown" if parsing fails.

    Examples:
        >>> field = {"Column": {"Expression": {"SourceRef": {"Entity": "Sales"}}, "Property": "Amount"}}
        >>> get_target_from_field(field)
        "'Sales'[Amount]"
    """
    if not field_data:
        return "Unknown"

    if "Column" in field_data:
        col = field_data["Column"]
        entity = col.get("Expression", {}).get("SourceRef", {}).get("Entity", "Unknown")
        prop = col.get("Property", "Unknown")
        return f"'{entity}'[{prop}]"

    if "Measure" in field_data:
        meas = field_data["Measure"]
        entity = (
            meas.get("Expression", {}).get("SourceRef", {}).get("Entity", "Unknown")
        )
        prop = meas.get("Property", "Unknown")
        return f"'{entity}'[{prop}]"

    if "HierarchyLevel" in field_data:
        hl = field_data["HierarchyLevel"]

        # Try to drill down to find Entity
        expr = hl.get("Expression", {})
        hierarchy = expr.get("Hierarchy", {})

        # This path can vary, trying a common traversal
        entity = "Unknown"
        if "Expression" in hierarchy:
            var_source = hierarchy["Expression"].get("PropertyVariationSource", {})
            entity = (
                var_source.get("Expression", {})
                .get("SourceRef", {})
                .get("Entity", "Unknown")
            )

        level = hl.get("Level", "Unknown")
        return f"'{entity}'[{level}]"

    return "Unknown"


def parse_target_components(target: str) -> tuple[str, str]:
    """
    Parse a target reference string into table and column components.

    Args:
        target: Target string like "'TableName'[ColumnName]".

    Returns:
        Tuple of (table_name, column_name). Empty strings if parsing fails.

    Examples:
        >>> parse_target_components("'Sales'[Amount]")
        ('Sales', 'Amount')
        >>> parse_target_components("[Amount]")
        ('', 'Amount')
    """
    table_name = ""
    column_name = ""
    if target.startswith("'"):
        try:
            table_name = target.split("'")[1]
            column_name = target.split("[")[1].rstrip("]")
        except IndexError:
            pass
    elif target.startswith("["):
        column_name = target.lstrip("[").rstrip("]")
    return table_name, column_name


def _format_date(date_str: str) -> str:
    """Convert a date string to ISO 8601 format.

    Args:
        date_str: Date string in '%d-%b-%Y' format.

    Returns:
        Formatted date string in ISO 8601 format.
    """
    return f"datetime'{datetime.strptime(date_str, '%d-%b-%Y').strftime('%Y-%m-%dT00:00:00')}'"


def _is_date(value: Any) -> bool:
    """Check if a value is a date string in 'dd-Mon-YYYY' format.

    Args:
        value: The value to check.

    Returns:
        True if the value is a valid date string, False otherwise.
    """
    if not isinstance(value, str):
        return False

    try:
        datetime.strptime(value, "%d-%b-%Y")
        return True
    except ValueError:
        return False


def _is_number(value: Any) -> bool:
    """Check if a value is an integer or float.

    Args:
        value: The value to check.

    Returns:
        True if the value is a number, False otherwise.
    """
    return isinstance(value, (int, float))


def _format_value(value: Any) -> str:
    """Format a value based on its type for filter conditions.

    Args:
        value: The value to format.

    Returns:
        Formatted value as a string.
    """
    if _is_date(value):
        return _format_date(value)
    elif isinstance(value, int):
        return f"{value}L"
    else:
        return f"'{value}'"


def _get_existing_or_generate_name(filters: list[dict], table: str) -> str:
    """Get existing name from filters or generate a new one.

    Args:
        filters: List of filter configurations.
        table: Table name to look up.

    Returns:
        Existing name from filters or first letter of table name.
    """
    for filter_item in filters:
        if "filter" in filter_item:
            for item in filter_item["filter"].get("From", []):
                if item.get("Entity") == table:
                    return item["Name"]
    return table[0].lower()


def _create_condition(
    condition_type: str, column: str, values: list, column_source: str
) -> dict:
    """Create a filter condition dictionary.

    Args:
        condition_type: Type of condition (e.g., 'GreaterThan', 'In').
        column: Column name to filter on.
        values: Values for the condition.
        column_source: Source identifier for the column.

    Returns:
        Dictionary representing the filter condition.
    """
    is_date_column = any(_is_date(v) for v in values)

    comparison_kinds = {
        "GreaterThan": 1,
        "GreaterThanOrEqual": 2,
        "LessThan": 3,
        "LessThanOrEqual": 4,
    }

    def construct_left():
        return {
            "Column": {
                "Expression": {"SourceRef": {"Source": column_source}},
                "Property": column,
            }
        }

    def construct_right(value):
        if is_date_column:
            return {
                "DateSpan": {
                    "Expression": {"Literal": {"Value": _format_value(value)}},
                    "TimeUnit": 5,
                }
            }
        return {"Literal": {"Value": _format_value(value)}}

    if condition_type in comparison_kinds:
        return {
            "Comparison": {
                "ComparisonKind": comparison_kinds[condition_type],
                "Left": construct_left(),
                "Right": construct_right(values[0]),
            }
        }

    if condition_type in ["Between", "NotBetween"]:
        comparisons = [
            {
                "Comparison": {
                    "ComparisonKind": comparison_kinds["GreaterThanOrEqual"],
                    "Left": construct_left(),
                    "Right": construct_right(values[0]),
                }
            },
            {
                "Comparison": {
                    "ComparisonKind": comparison_kinds["LessThanOrEqual"],
                    "Left": construct_left(),
                    "Right": construct_right(values[1]),
                }
            },
        ]
        return {
            "Or" if condition_type == "NotBetween" else "And": {
                "Left": comparisons[0],
                "Right": comparisons[1],
            },
        }

    if condition_type in ["In", "NotIn"]:
        condition = {
            "In": {
                "Expressions": [construct_left()],
                "Values": [[{"Literal": {"Value": _format_value(v)}}] for v in values],
            }
        }
        return (
            {"Not": {"Expression": condition}}
            if condition_type == "NotIn"
            else condition
        )

    if any(key in condition_type for key in ["Contains", "EndsWith", "StartsWith"]):
        conditions = []
        logical_op = "Or" if "Or" in condition_type else "And"
        for value in values:
            single_condition = {
                condition_type.replace("Not", "")
                .replace("Or", "")
                .replace("And", ""): {
                    "Left": construct_left(),
                    "Right": {"Literal": {"Value": _format_value(value)}},
                }
            }
            if condition_type.startswith("Not"):
                single_condition = {"Not": {"Expression": single_condition}}
            conditions.append(single_condition)

        condition = conditions[0]
        for next_condition in conditions[1:]:
            condition = {logical_op: {"Left": condition, "Right": next_condition}}

        return condition

    return {}


def _validate_filters(filters: list[dict]) -> tuple[list, list]:
    """Validate filter configurations and separate valid from invalid.

    Args:
        filters: List of filter configurations to validate.

    Returns:
        Tuple of (valid_filters, ignored_filters_with_reasons).
    """
    valid_filters, ignored_filters = [], []

    base_text_conditions = {"Contains", "StartsWith", "EndsWith"}
    text_conditions = {
        f"{prefix}{condition}"
        for prefix in ("", "Not")
        for condition in base_text_conditions
    }
    multi_value_conditions = {
        f"{condition}{suffix}"
        for condition in text_conditions
        for suffix in ("And", "Or")
    }
    all_text_conditions = text_conditions | multi_value_conditions

    two_value_conditions = {"Between", "NotBetween"}
    one_value_conditions = text_conditions | {
        "LessThan",
        "GreaterThan",
        "LessThanOrEqual",
        "GreaterThanOrEqual",
    }
    numeric_date_conditions = (
        two_value_conditions | one_value_conditions - text_conditions
    )

    for filter_config in filters:
        condition = filter_config.get("Condition")
        values = filter_config.get("Values")

        if values is None:
            valid_filters.append(filter_config)
            continue

        if condition in one_value_conditions and len(values) != 1:
            ignored_filters.append(
                (filter_config, "Condition requires exactly one value")
            )
        elif condition in two_value_conditions and len(values) != 2:
            ignored_filters.append(
                (filter_config, "Condition requires exactly two values")
            )
        elif condition in multi_value_conditions and len(values) < 2:
            ignored_filters.append(
                (filter_config, "Condition requires at least two values")
            )
        elif condition in all_text_conditions and not all(
            isinstance(v, str) for v in values
        ):
            ignored_filters.append(
                (filter_config, "Text condition is applicable only for string values")
            )
        elif condition in numeric_date_conditions and not all(
            _is_date(v) or _is_number(v) for v in values
        ):
            ignored_filters.append(
                (
                    filter_config,
                    "Condition is applicable only for date and number values",
                )
            )
        else:
            valid_filters.append(filter_config)

    return valid_filters, ignored_filters


def update_report_filters(
    report_path: str,
    filters: list,
    reports: list = None,
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Updates report filters based on the given filters.

    Parameters:
    report_path (str): Path to a .Report folder or root folder containing reports.
    filters (list): List of filters to apply.
    reports (list, optional): List of reports to update. Defaults to None.
    summary (bool, optional): Show summary instead of detailed messages. Defaults to False.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading("Updating report filters", dry_run)
    if filters is None or not filters:
        raise ValueError("The 'filters' parameter is required and cannot be empty.")

    valid_filters, ignored_filters = _validate_filters(filters)
    for filter_config, reason in ignored_filters:
        console.print_warning(f"Ignored filter: {filter_config} - Reason: {reason}")

    report_json_paths = get_report_paths(report_path, reports)

    any_changes = False
    for report_json_path in report_json_paths:
        data = load_json(report_json_path)
        if (
            not data
            or "filterConfig" not in data
            or "filters" not in data["filterConfig"]
        ):
            console.print_info(
                f"No existing filters found in report: {Path(report_json_path).name}"
            )
            continue

        existing_entities = {
            f["field"]["Column"]["Expression"]["SourceRef"].get("Entity")
            for f in data["filterConfig"]["filters"]
            if "field" in f and "Column" in f["field"]
        }
        existing_properties = {
            f["field"]["Column"].get("Property")
            for f in data["filterConfig"]["filters"]
            if "field" in f and "Column" in f["field"]
        }

        updated = False
        for filter_config in valid_filters:
            table, column, condition, values = [
                filter_config.get(key, [])
                for key in ["Table", "Column", "Condition", "Values"]
            ]

            if table in existing_entities and column in existing_properties:
                filter_item = next(
                    (
                        f
                        for f in data["filterConfig"]["filters"]
                        if f["field"]["Column"]["Expression"]["SourceRef"]["Entity"]
                        == table
                        and f["field"]["Column"]["Property"] == column
                    ),
                    None,
                )

                if filter_item:
                    if values is None:
                        filter_item.pop("filter", None)
                    else:
                        name = _get_existing_or_generate_name(
                            data["filterConfig"]["filters"], table
                        )
                        filter_item["filter"] = filter_item.get(
                            "filter",
                            {
                                "Version": 2,
                                "From": [{"Name": name, "Entity": table, "Type": 0}],
                                "Where": [{"Condition": {}}],
                            },
                        )
                        filter_item["filter"]["Where"][0]["Condition"] = (
                            _create_condition(condition, column, values, name)
                        )
                    updated = True
                else:
                    console.print_warning(
                        f"Skipping filter update for {table}.{column} in report {Path(report_json_path).name} - filter item not found"
                    )
            else:
                console.print_warning(
                    f"Skipping filter update for {table}.{column} in report {Path(report_json_path).name} - entity or property not found"
                )

        if updated:
            any_changes = True
            if not dry_run:
                write_json(report_json_path, data)
            if not summary:
                if dry_run:
                    console.print_dry_run(
                        f"Would update filters in report: {Path(report_json_path).name}"
                    )
                else:
                    console.print_success(
                        f"Updated filters in report: {Path(report_json_path).name}"
                    )
        elif not summary:
            console.print_info(
                f"No filters were updated in report: {Path(report_json_path).name}"
            )

    if summary:
        if any_changes:
            count = len(report_json_paths)
            printer = console.print_dry_run if dry_run else console.print_success
            if count == 1:
                printer(
                    "Would update report filters"
                    if dry_run
                    else "Updated report filters"
                )
            else:
                printer(
                    f"Would update filters in {count} reports"
                    if dry_run
                    else f"Updated filters in {count} reports"
                )
        else:
            console.print_info("No filters were updated.")

    return any_changes


def sort_report_filters(
    report_path: str,
    reports: list = None,
    sort_order: str = "SelectedFilterTop",
    custom_order: list = None,
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Sorts the report filters in all specified reports based on the given sort order:
    - "Ascending": Sort all filters alphabetically ascending.
    - "Descending": Sort all filters alphabetically descending.
    - "SelectedFilterTop": Selected filters at the top (alphabetically ascending),
      unselected filters at the bottom (alphabetically ascending). If no filters are selected,
      all filters are sorted in ascending order.
    - "Custom": List of filter names to be at the top, everything else alphabetically below.

    Parameters:
    report_path (str): Path to a .Report folder or root folder containing reports.
    reports (list, optional): List of reports to update. Defaults to None.
    sort_order (str, optional): Sorting strategy to use. Defaults to "SelectedFilterTop".
    custom_order (list, optional): List of filter names to prioritize in order (required for "Custom" sort order).
    summary (bool, optional): Show summary instead of detailed messages. Defaults to False.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading("Sorting report filters", dry_run)
    report_json_paths = get_report_paths(report_path, reports)
    any_changes = False
    filters_found = False

    for report_json_path in report_json_paths:
        data = load_json(report_json_path)
        if (
            not data
            or "filterConfig" not in data
            or "filters" not in data["filterConfig"]
        ):
            if not summary:
                console.print_info(
                    f"No existing filters found in report: {Path(report_json_path).name}"
                )
            continue

        filters_found = True
        filters = data["filterConfig"]["filters"]
        original_order = [f.get("ordinal", -1) for f in filters]
        original_sort_order = data["filterConfig"].get("filterSortOrder")

        if sort_order == "SelectedFilterTop":
            selected_filters = [f for f in filters if "filter" in f]
            unselected_filters = [f for f in filters if "filter" not in f]

            if selected_filters and unselected_filters:
                selected_filters.sort(key=lambda x: x["field"]["Column"]["Property"])
                unselected_filters.sort(key=lambda x: x["field"]["Column"]["Property"])

                filters = selected_filters + unselected_filters
                data["filterConfig"]["filters"] = filters

                for index, filter_item in enumerate(filters):
                    filter_item["ordinal"] = index

                data["filterConfig"]["filterSortOrder"] = "Custom"
            else:
                sort_order = "Ascending"

        if sort_order == "Custom" and custom_order:
            custom_order_dict = {name: i for i, name in enumerate(custom_order)}

            filters.sort(
                key=lambda x: (
                    custom_order_dict.get(
                        x["field"]["Column"]["Property"], float("inf")
                    ),
                    x["field"]["Column"]["Property"],
                )
            )

            for index, filter_item in enumerate(filters):
                filter_item["ordinal"] = index

            data["filterConfig"]["filterSortOrder"] = "Custom"

        elif sort_order in ["Ascending", "Descending"]:
            for filter_item in filters:
                if "ordinal" in filter_item:
                    del filter_item["ordinal"]

            data["filterConfig"]["filterSortOrder"] = sort_order

        elif sort_order == "SelectedFilterTop":
            pass

        else:
            console.print_error(
                f"Invalid sort_order: {sort_order}. No changes applied to report: {report_path}"
            )
            continue

        new_order = [f.get("ordinal", -1) for f in filters]
        new_sort_order = data["filterConfig"].get("filterSortOrder")
        has_changes = (
            original_order != new_order or original_sort_order != new_sort_order
        )

        if has_changes:
            any_changes = True
            if not dry_run:
                write_json(report_json_path, data)
            if not summary:
                if dry_run:
                    console.print_dry_run(
                        f"Would sort filters in report: {report_json_path}"
                    )
                else:
                    console.print_success(
                        f"Sorted filters in report: {report_json_path}"
                    )
        elif not summary:
            console.print_info(f"No changes needed for report: {report_json_path}")

    if summary:
        if any_changes:
            count = len(report_json_paths)
            printer = console.print_dry_run if dry_run else console.print_success
            if count == 1:
                printer(
                    "Would sort report filters" if dry_run else "Sorted report filters"
                )
            else:
                printer(
                    f"Would sort filters in {count} reports"
                    if dry_run
                    else f"Sorted filters in {count} reports"
                )
        elif filters_found:
            console.print_info("Filters are already sorted.")
        else:
            console.print_info("No report filters found.")

    return any_changes


def configure_filter_pane(
    report_path: str,
    visible: bool = True,
    expanded: bool = False,
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Configure the filter pane visibility and expanded state.

    Args:
        report_path (str): The path to the report.
        visible (bool): Show/hide the filter pane entirely (default: True).
        expanded (bool): Expand/collapse the pane when visible (default: False).
        dry_run (bool): Whether to perform a dry run.
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    state_desc = "hidden" if not visible else ("expanded" if expanded else "collapsed")
    console.print_action_heading(f"Configuring filter pane ({state_desc})", dry_run)

    report_json_path = Path(report_path) / "definition" / "report.json"
    report_data = load_json(report_json_path)

    objects = report_data.get("objects", {})
    outspace_pane = objects.get("outspacePane", [])

    current_visible = "true"
    current_expanded = "true"
    if outspace_pane:
        properties = outspace_pane[0].get("properties", {})
        current_visible = (
            properties.get("visible", {})
            .get("expr", {})
            .get("Literal", {})
            .get("Value", "true")
        )
        current_expanded = (
            properties.get("expanded", {})
            .get("expr", {})
            .get("Literal", {})
            .get("Value", "true")
        )

    target_visible = "true" if visible else "false"
    target_expanded = "true" if expanded else "false"

    if current_visible == target_visible and current_expanded == target_expanded:
        console.print_info(f"Filter pane is already {state_desc}.")
        return False

    if "objects" not in report_data:
        report_data["objects"] = {}
    if "outspacePane" not in report_data["objects"]:
        report_data["objects"]["outspacePane"] = [{"properties": {}}]
    if "properties" not in report_data["objects"]["outspacePane"][0]:
        report_data["objects"]["outspacePane"][0]["properties"] = {}

    props = report_data["objects"]["outspacePane"][0]["properties"]
    props["visible"] = {"expr": {"Literal": {"Value": target_visible}}}
    props["expanded"] = {"expr": {"Literal": {"Value": target_expanded}}}

    if not dry_run:
        write_json(report_json_path, report_data)

    if dry_run:
        console.print_dry_run(f"Would configure filter pane to {state_desc}.")
    else:
        console.print_success(f"Configured filter pane to {state_desc}.")

    return True


def reset_filter_pane_width(
    report_path: str, dry_run: bool = False, summary: bool = False
) -> bool:
    """
    Reset the filter pane width by removing the width property from outspacePane in all page.json files.

    Args:
        report_path (str): The path to the report.
        dry_run (bool): Whether to perform a dry run.
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading("Resetting filter pane width", dry_run)

    pages_dir = Path(report_path) / "definition" / "pages"
    modified_pages = []

    def _remove_width_property(page_data: dict, file_path: str) -> bool:
        objects = page_data.get("objects", {})
        outspace_pane = objects.get("outspacePane", [])

        if not outspace_pane:
            return False

        properties = outspace_pane[0].get("properties", {})
        if "width" not in properties:
            return False

        del properties["width"]

        if not properties:
            del outspace_pane[0]["properties"]

        if not outspace_pane[0]:
            del objects["outspacePane"]

        if not objects:
            del page_data["objects"]

        return True

    def _check_and_track(page_data: dict, file_path: str) -> bool:
        result = _remove_width_property(page_data, file_path)
        if result:
            page_name = page_data.get("displayName", Path(file_path).parent.name)
            modified_pages.append(page_name)
        return result

    results = process_json_files(
        pages_dir, "page.json", _check_and_track, process=True, dry_run=dry_run
    )

    pages_modified = results if isinstance(results, int) else len(results)

    if pages_modified > 0:
        if summary:
            if dry_run:
                console.print_dry_run(
                    f"Would reset filter pane width on {pages_modified} page(s)."
                )
            else:
                console.print_success(
                    f"Reset filter pane width on {pages_modified} page(s)."
                )
        else:
            for page_name in modified_pages:
                if dry_run:
                    console.print_dry_run(
                        f"Would reset filter pane width on page: {page_name}"
                    )
                else:
                    console.print_success(
                        f"Reset filter pane width on page: {page_name}"
                    )
        return True
    else:
        console.print_info("No pages found with filter pane width set.")
        return False
