import os
import re
from datetime import datetime
from fnmatch import fnmatch
from dataclasses import dataclass, field

from .common import (
    load_json,
    write_json,
    get_report_paths,
    process_json_files,
    iter_pages,
    iter_visuals,
)
from .console_utils import console


@dataclass
class _FilterCounts:
    """Tracks filter counts for summary output."""

    report: int = 0
    page: int = 0
    visual: int = 0
    slicer: int = 0
    pages_affected: set[str] = field(default_factory=set)
    visuals_affected: set[str] = field(default_factory=set)
    slicers_affected: set[str] = field(default_factory=set)

    @property
    def total(self) -> int:
        return self.report + self.page + self.slicer + self.visual


def _print_filter_list(
    filters: list[str], indent: str, dry_run: bool, summary: bool
) -> None:
    """Print a list of filter strings with appropriate formatting."""
    if summary:
        return
    for f in filters:
        if dry_run:
            console.print_dry_run(f"{indent}{f}")
        else:
            console.print_cleared(f"{indent}{f}")


def _format_date(date_str: str) -> str:
    """
    Converts a date string in the format '%d-%b-%Y' to an ISO 8601 format string.

    Parameters:
    date_str (str): The date string to format.

    Returns:
    str: Formatted date string in ISO 8601 format.
    """
    return f"datetime'{datetime.strptime(date_str, '%d-%b-%Y').strftime('%Y-%m-%dT00:00:00')}'"


def _is_date(value: any) -> bool:
    """if a value is a date string in the format "dd-Mon-YYYY".

    Parameters:
    value (any): The value to check.

    Returns:
    bool: True if the value is a valid date string, False otherwise.
    """
    if not isinstance(value, str):
        return False

    try:
        datetime.strptime(value, "%d-%b-%Y")
        return True
    except ValueError:
        return False


def _is_number(value: any) -> bool:
    """
    Checks if a value is either an integer or a float.

    Parameters:
    value (any): The value to check.

    Returns:
    bool: True if the value is a number, False otherwise.
    """
    return isinstance(value, (int, float))


def _format_value(value: any) -> str:
    """
    Formats a value based on its type.

    Parameters:
    value (any): The value to format.

    Returns:
    str: Formatted value as a string.
    """
    if _is_date(value):
        return _format_date(value)
    elif isinstance(value, int):
        return f"{value}L"
    else:
        return f"'{value}'"


def _get_existing_or_generate_name(filters: list[dict], table: str) -> str:
    """
    Retrieves an existing name or generates a new one based on filters and table name.

    Parameters:
    filters (list): List of filters.
    table (str): Table name.

    Returns:
    str: Existing or generated name.
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
    """
    Creates a condition dictionary for filtering.

    Parameters:
    condition_type (str): Type of condition.
    column (str): Column name.
    values (list): Values for the condition.
    column_source (str): Source of the column.

    Returns:
    dict: Dictionary representing the condition.
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
    """
    Validates the given filters.

    Parameters:
    filters (list): List of filters to validate.

    Returns:
    tuple: Tuple containing valid filters and ignored filters with reasons.
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
                f"No existing filters found in report: {os.path.basename(report_json_path)}"
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
                        f"Skipping filter update for {table}.{column} in report {os.path.basename(report_json_path)} - filter item not found"
                    )
            else:
                console.print_warning(
                    f"Skipping filter update for {table}.{column} in report {os.path.basename(report_json_path)} - entity or property not found"
                )

        if updated:
            any_changes = True
            if not dry_run:
                write_json(report_json_path, data)
            if not summary:
                if dry_run:
                    console.print_dry_run(
                        f"Would update filters in report: {os.path.basename(report_json_path)}"
                    )
                else:
                    console.print_success(
                        f"Updated filters in report: {os.path.basename(report_json_path)}"
                    )
        elif not summary:
            console.print_info(
                f"No filters were updated in report: {os.path.basename(report_json_path)}"
            )

    if summary:
        if dry_run:
            msg = f"Would update filters in {len(report_json_paths)} reports"
            console.print_dry_run(msg)
        else:
            msg = f"Updated filters in {len(report_json_paths)} reports"
            console.print_success(msg)

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

    for report_json_path in report_json_paths:
        data = load_json(report_json_path)
        if (
            not data
            or "filterConfig" not in data
            or "filters" not in data["filterConfig"]
        ):
            console.print_info(
                f"No existing filters found in report: {os.path.basename(report_json_path)}"
            )
            continue

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

        # Check if any changes were made
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
        if dry_run:
            msg = f"Would sort filters in {len(report_json_paths)} reports"
            console.print_dry_run(msg)
        else:
            msg = f"Sorted filters in {len(report_json_paths)} reports"
            console.print_success(msg)

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

    report_json_path = os.path.join(report_path, "definition", "report.json")
    report_data = load_json(report_json_path)

    objects = report_data.get("objects", {})
    outspace_pane = objects.get("outspacePane", [])

    # Get current values
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

    # Check if changes are needed
    if current_visible == target_visible and current_expanded == target_expanded:
        console.print_info(f"Filter pane is already {state_desc}.")
        return False

    # Ensure objects structure exists
    if "objects" not in report_data:
        report_data["objects"] = {}
    if "outspacePane" not in report_data["objects"]:
        report_data["objects"]["outspacePane"] = [{"properties": {}}]
    if "properties" not in report_data["objects"]["outspacePane"][0]:
        report_data["objects"]["outspacePane"][0]["properties"] = {}

    # Set properties
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

    pages_dir = os.path.join(report_path, "definition", "pages")
    pages_modified = 0

    def _remove_width_property(page_data: dict, file_path: str) -> bool:
        objects = page_data.get("objects", {})
        outspace_pane = objects.get("outspacePane", [])

        if not outspace_pane:
            return False

        properties = outspace_pane[0].get("properties", {})
        if "width" not in properties:
            return False

        # Remove width property
        del properties["width"]

        # If properties is now empty, remove it
        if not properties:
            del outspace_pane[0]["properties"]

        # If outspacePane[0] is now empty, remove outspacePane
        if not outspace_pane[0]:
            del objects["outspacePane"]

        # If objects is now empty, remove it
        if not objects:
            del page_data["objects"]

        return True

    results = process_json_files(
        pages_dir, "page.json", _remove_width_property, process=True, dry_run=dry_run
    )

    pages_modified = results if isinstance(results, int) else len(results)

    if pages_modified > 0:
        if dry_run:
            console.print_dry_run(
                f"Would reset filter pane width on {pages_modified} page(s)."
            )
        else:
            console.print_success(
                f"Reset filter pane width on {pages_modified} page(s)."
            )
        return True
    else:
        console.print_info("No pages found with filter pane width set.")
        return False


def _get_target_from_field(field_data: dict) -> str:
    """
    Extracts the target (Table[Column/Measure/Level]) from the field definition.
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


def _parse_target_components(target: str) -> tuple[str, str]:
    """
    Parses target string like "'TableName'[ColumnName]".
    Returns (table_name, column_name).
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


def _filter_matches_criteria(
    target: str,
    table_name: str,
    column_name: str,
    include_tables: list[str] = None,
    include_columns: list[str] = None,
    include_fields: list[str] = None,
) -> bool:
    """
    Checks if a filter target matches the given criteria patterns.
    Returns True if no criteria specified (match all) or if criteria matches.
    """
    has_criteria = include_tables or include_columns or include_fields
    if not has_criteria:
        return True

    # Check --field patterns first
    if include_fields:
        for pattern in include_fields:
            escaped_pattern = re.sub(r"\[(?!\[\])", "[[]", pattern)
            escaped_pattern = re.sub(r"(?<!\[)\]", "[]]", escaped_pattern)
            if fnmatch(target, escaped_pattern):
                return True

    # Check --table / --column (intersection logic)
    if include_tables or include_columns:
        table_match = not include_tables or any(
            fnmatch(table_name, p) for p in include_tables
        )
        column_match = not include_columns or any(
            fnmatch(column_name, p) for p in include_columns
        )
        if table_match and column_match:
            return True

    return False


def _get_slicer_filter_data(vis_data: dict) -> tuple[dict, dict, str] | None:
    """
    Extracts slicer filter information from a visual.

    Returns (filter_dict, field_def, target_str) or None if not a valid slicer with filter.
    - filter_dict: The filter Where clause from objects.general[0].properties.filter.filter
    - field_def: The field definition from query projections
    - target_str: The formatted target string like 'Table'[Column]
    """
    try:
        general_objs = vis_data.get("visual", {}).get("objects", {}).get("general", [])
        if not general_objs or len(general_objs) == 0:
            return None

        props = general_objs[0].get("properties", {})
        if "filter" not in props or "filter" not in props["filter"]:
            return None

        # Get field from query projections
        query_state = vis_data.get("visual", {}).get("query", {}).get("queryState", {})
        vals = query_state.get("Values", {})
        projections = vals.get("projections", [])

        if not projections:
            return None

        field_def = projections[0].get("field")
        filter_dict = props["filter"]["filter"]
        target = _get_target_from_field(field_def)

        return filter_dict, field_def, target
    except (IndexError, KeyError, AttributeError):
        return None


def _get_literal_display_value(expr: dict) -> str:
    """
    Extracts value from a Literal expression for display.
    """
    if not isinstance(expr, dict):
        return str(expr)

    if "Literal" in expr:
        val = str(expr["Literal"].get("Value", "null"))
        # Remove L (Long) and D (Decimal) suffixes from numeric literals (which are not quoted)
        if val and not val.startswith("'") and (val.endswith("L") or val.endswith("D")):
            return val[:-1]
        return val

    # Handle DateSpan (Advanced filtering)
    if "DateSpan" in expr:
        return _get_literal_display_value(expr["DateSpan"].get("Expression", {}))

    # Handle generic expressions if needed, or fallback
    return "Expression"


def _parse_condition(condition: dict) -> str:
    """
    Recursively parses the filter condition into a readable string.
    """
    if not condition:
        return ""

    if "Not" in condition:
        return f"NOT ({_parse_condition(condition['Not']['Expression'])})"

    if "In" in condition:
        in_cond = condition["In"]
        values = []
        if "Values" in in_cond:
            for val_list in in_cond["Values"]:
                val_strs = [_get_literal_display_value(v) for v in val_list]
                values.append("(" + ", ".join(val_strs) + ")")

        return f"IN [{', '.join(values)}]"

    if "Comparison" in condition:
        comp = condition["Comparison"]
        kind = comp.get("ComparisonKind", 0)
        # Mapping based on typical Power BI behavior (needs verification if exact mapping is critical)
        kinds = {0: "=", 1: ">", 2: ">=", 3: "<", 4: "<="}
        op = kinds.get(kind, f"Op({kind})")

        right = _get_literal_display_value(comp.get("Right", {}))
        return f"{op} {right}"

    if "And" in condition:
        left = _parse_condition(condition["And"]["Left"])
        right = _parse_condition(condition["And"]["Right"])
        return f"({left} AND {right})"

    if "Or" in condition:
        left = _parse_condition(condition["Or"]["Left"])
        right = _parse_condition(condition["Or"]["Right"])
        return f"({left} OR {right})"

    # Fallback for unknown conditions
    return "ComplexCondition()"


def _get_filter_strings(
    filter_config: dict,
    include_tables: list[str] = None,
    include_columns: list[str] = None,
    include_fields: list[str] = None,
) -> list[str]:
    """
    Extracts filters as formatted strings from a filterConfig dictionary.

    Args:
        filter_config: The filterConfig dictionary from report/page/visual JSON.
        include_tables: Optional list of table name patterns to match (supports wildcards).
        include_columns: Optional list of column name patterns to match (supports wildcards).
        include_fields: Optional list of full field patterns like "'Table'[Column]" (supports wildcards).

    Returns:
        List of formatted filter strings matching the criteria.
    """
    results = []
    if not filter_config or "filters" not in filter_config:
        return results

    for f in filter_config["filters"]:
        if "filter" not in f:
            continue

        target = _get_target_from_field(f.get("field"))
        table_name, column_name = _parse_target_components(target)

        # Check if filter matches the criteria
        if not _filter_matches_criteria(
            target,
            table_name,
            column_name,
            include_tables,
            include_columns,
            include_fields,
        ):
            continue

        conditions = []
        where_clauses = f["filter"].get("Where", [])
        for w in where_clauses:
            if "Condition" in w:
                cond_str = _parse_condition(w["Condition"])
                # Filter out empty IN [] which denotes no selection usually
                if cond_str == "IN []":
                    continue
                conditions.append(cond_str)

        if not conditions:
            continue

        condition_str = " AND ".join(conditions)
        results.append(f"{target} : {condition_str}")
    return results


def _clear_matching_filters(
    filter_config: dict,
    include_tables: list[str] = None,
    include_columns: list[str] = None,
    include_fields: list[str] = None,
    clear_all: bool = False,
) -> tuple[list[str], bool]:
    """
    Clears filter conditions from matching filters in a filterConfig.

    Args:
        filter_config: The filterConfig dictionary.
        include_tables, include_columns, include_fields: Matching criteria.
        clear_all: If True, clear all filters regardless of criteria.

    Returns:
        Tuple of (list of cleared filter descriptions, whether any changes were made).
    """
    cleared = []
    changed = False

    if not filter_config or "filters" not in filter_config:
        return cleared, changed

    for f in filter_config["filters"]:
        if "filter" not in f:
            continue  # No condition to clear

        target = _get_target_from_field(f.get("field"))
        table_name, column_name = _parse_target_components(target)

        # Check if this filter matches criteria
        # If no criteria specified, clear all (implicit --all behavior)
        # If criteria specified, only clear matching filters
        has_criteria = include_tables or include_columns or include_fields
        should_clear = (
            clear_all
            or not has_criteria
            or _filter_matches_criteria(
                target,
                table_name,
                column_name,
                include_tables,
                include_columns,
                include_fields,
            )
        )

        if should_clear:
            # Get description before clearing
            conditions = []
            where_clauses = f["filter"].get("Where", [])
            for w in where_clauses:
                if "Condition" in w:
                    cond_str = _parse_condition(w["Condition"])
                    if cond_str != "IN []":
                        conditions.append(cond_str)

            if conditions:
                condition_str = " AND ".join(conditions)
                cleared.append(f"{target} : {condition_str}")

                # Clear the filter
                del f["filter"]
                changed = True

    return cleared, changed


def _collect_page_data(
    page_path: str,
    page_data: dict,
    target_visual: str = None,
    include_tables: list[str] = None,
    include_columns: list[str] = None,
    include_fields: list[str] = None,
    show_visual_filters: bool = False,
    is_target_page: bool = False,
    show_page_filters: bool = False,
) -> dict:
    """
    Single-pass collection of page, visual, and slicer filter data.
    """
    data = {
        "page_filters": [],
        "visual_outputs": [],  # (vis_type, vis_name, vis_filters, visual_json_path, vis_data)
        "slicer_outputs": [],  # (vis_name, [filters], visual_json_path, vis_data)
    }

    # 1. Page Filters
    if show_page_filters or is_target_page:
        data["page_filters"] = _get_filter_strings(
            page_data.get("filterConfig"),
            include_tables=include_tables,
            include_columns=include_columns,
            include_fields=include_fields,
        )

    # 2. Visuals & Slicers
    # We scan visuals if explicit visual filtering is requested, OR if we are processing this page
    # because we want to capture Slicer visuals which act as page filters.
    should_scan_visuals = (
        show_visual_filters or target_visual or show_page_filters or is_target_page
    )

    if should_scan_visuals:
        for visual_id, visual_folder, vis_data in iter_visuals(page_path):
            visual_json_path = os.path.join(visual_folder, "visual.json")
            vis_type = vis_data.get("visual", {}).get("visualType", "unknown")
            vis_name = vis_data.get("name", visual_id)
            is_slicer = "slicer" in vis_type.lower()

            # Filter by visual if requested
            is_target_visual = False
            if target_visual:
                if target_visual.lower() in [visual_id.lower(), vis_type.lower()]:
                    is_target_visual = True
                elif not show_visual_filters:
                    continue

            vis_filters = _get_filter_strings(
                vis_data.get("filterConfig"),
                include_tables=include_tables,
                include_columns=include_columns,
                include_fields=include_fields,
            )

            if is_slicer:
                slicer_data = _get_slicer_filter_data(vis_data)
                slicer_filters = []
                if slicer_data:
                    filter_dict, field_def, target = slicer_data
                    slicer_filters = _get_filter_strings(
                        {"filters": [{"field": field_def, "filter": filter_dict}]},
                        include_tables=include_tables,
                        include_columns=include_columns,
                        include_fields=include_fields,
                    )

                if (slicer_filters or is_target_visual) and (
                    show_page_filters
                    or is_target_page
                    or is_target_visual
                    or show_visual_filters
                ):
                    data["slicer_outputs"].append(
                        (vis_name, slicer_filters, visual_json_path, vis_data)
                    )
            else:
                # Standard Visuals
                if (show_visual_filters or is_target_visual) and (
                    vis_filters or is_target_visual
                ):
                    data["visual_outputs"].append(
                        (vis_type, vis_name, vis_filters, visual_json_path, vis_data)
                    )

    # Context: User wants to see page filters if a visual/slicer is found, even if not explicitly asked
    if (data["visual_outputs"] or data["slicer_outputs"]) and not data["page_filters"]:
        data["page_filters"] = _get_filter_strings(
            page_data.get("filterConfig"),
            include_tables=include_tables,
            include_columns=include_columns,
            include_fields=include_fields,
        )

    return data


def clear_filters(
    report_path: str,
    show_page_filters: bool = False,
    show_visual_filters: bool = False,
    target_page: str = None,
    target_visual: str = None,
    include_tables: list[str] = None,
    include_columns: list[str] = None,
    include_fields: list[str] = None,
    clear_all: bool = False,
    dry_run: bool = True,
    summary: bool = False,
) -> bool:
    """
    Clears filter conditions from report, pages, and visuals.
    """
    if not summary:
        heading = (
            f"[DRY RUN] Inspecting filters in: {report_path}"
            if dry_run
            else f"Clearing filters in: {report_path}"
        )
        console.print_heading(heading)

    counts = _FilterCounts()
    found_any_filters = False

    # 1. Report Level Filters
    report_json_path = os.path.join(report_path, "definition", "report.json")
    if os.path.exists(report_json_path):
        data = load_json(report_json_path)
        report_filters = _get_filter_strings(
            data.get("filterConfig"), include_tables, include_columns, include_fields
        )

        if report_filters:
            found_any_filters = True
            counts.report = len(report_filters)
            if not summary:
                console.print_info("[Report] Report Filters:")

            if not dry_run:
                cleared, changed = _clear_matching_filters(
                    data.get("filterConfig"),
                    include_tables,
                    include_columns,
                    include_fields,
                    clear_all,
                )
                if changed:
                    write_json(report_json_path, data)
                    _print_filter_list(cleared, "  ", dry_run, summary)
            else:
                _print_filter_list(report_filters, "  ", dry_run, summary)
    elif not os.path.basename(report_path).endswith(".Report"):
        console.print_warning(f"report.json not found at {report_json_path}")

    # Exit early if only report filters requested and nothing to do
    if not any([show_page_filters, show_visual_filters, target_page, target_visual]):
        return found_any_filters

    # 2. Page & Visual Level
    for page_id, page_path, page_data in iter_pages(report_path):
        page_name = page_data.get("displayName", page_id)
        is_target_page = target_page and target_page.lower() in [
            page_id.lower(),
            page_name.lower(),
        ]
        if target_page and not is_target_page:
            continue

        page_info = _collect_page_data(
            page_path,
            page_data,
            target_visual,
            include_tables,
            include_columns,
            include_fields,
            show_visual_filters,
            is_target_page,
            show_page_filters,
        )

        if not (
            page_info["page_filters"]
            or page_info["visual_outputs"]
            or page_info["slicer_outputs"]
            or is_target_page
        ):
            continue

        found_any_filters = True
        if not summary:
            console.print_info(f"\n[Page] {page_name} ({page_id})")

        # 2a. Page Filters
        if page_info["page_filters"]:
            counts.page += len(page_info["page_filters"])
            counts.pages_affected.add(page_name)
            if not summary:
                console.print_info("  Page Filters:")

            if not dry_run:
                cleared, changed = _clear_matching_filters(
                    page_data.get("filterConfig"),
                    include_tables,
                    include_columns,
                    include_fields,
                    clear_all,
                )
                if changed:
                    write_json(os.path.join(page_path, "page.json"), page_data)
                    _print_filter_list(cleared, "    ", dry_run, summary)
            else:
                _print_filter_list(page_info["page_filters"], "    ", dry_run, summary)
        elif (show_page_filters or is_target_page) and not summary:
            has_criteria = include_tables or include_columns or include_fields
            if not has_criteria:
                console.print_info("  Page Filters: None")

        # 2b. Slicer Filters
        if page_info["slicer_outputs"]:
            if not summary:
                console.print_info("  Slicer Filters:")

            for s_name, s_filters, vis_path, vis_data in page_info["slicer_outputs"]:
                counts.slicer += len(s_filters)
                counts.slicers_affected.add(s_name)
                if not summary:
                    console.print_info(f"    [Slicer] {s_name}")

                if not dry_run and s_filters:
                    # Clear slicer filter
                    general_objs = vis_data["visual"]["objects"]["general"]
                    if "filter" in general_objs[0]["properties"]:
                        del general_objs[0]["properties"]["filter"]
                        write_json(vis_path, vis_data)
                        _print_filter_list(s_filters, "      ", dry_run, summary)
                else:
                    _print_filter_list(s_filters, "      ", dry_run, summary)

        # 2c. Visual Filters
        if page_info["visual_outputs"]:
            if not summary:
                console.print_info("  Visual Filters:")

            visual_will_clear = not dry_run and (show_visual_filters or target_visual)

            for v_type, v_name, v_filters, vis_path, vis_data in page_info[
                "visual_outputs"
            ]:
                counts.visual += len(v_filters)
                counts.visuals_affected.add(v_name)
                if not summary:
                    console.print_info(f"    [Visual] {v_type} ({v_name})")

                if visual_will_clear and v_filters:
                    cleared, changed = _clear_matching_filters(
                        vis_data.get("filterConfig"),
                        include_tables,
                        include_columns,
                        include_fields,
                        clear_all,
                    )
                    if changed:
                        write_json(vis_path, vis_data)
                        _print_filter_list(cleared, "      ", dry_run, summary)
                else:
                    _print_filter_list(v_filters, "      ", dry_run, summary)

    # 3. Print Summary
    if summary:
        if counts.total > 0:
            parts = []
            if counts.report > 0:
                parts.append(f"{counts.report} report filter(s)")
            if counts.page > 0:
                parts.append(
                    f"{counts.page} page filter(s) across {len(counts.pages_affected)} page(s)"
                )
            if counts.slicer > 0:
                parts.append(
                    f"{counts.slicer} slicer filter(s) across {len(counts.slicers_affected)} slicer(s)"
                )
            if counts.visual > 0:
                parts.append(
                    f"{counts.visual} visual filter(s) across {len(counts.visuals_affected)} visual(s)"
                )

            action_word = "Would clear" if dry_run else "Cleared"
            msg = f"{action_word}: {', '.join(parts)}"
            if dry_run:
                console.print_dry_run(msg)
            else:
                console.print_success(msg)
        else:
            console.print_info("No filters found matching the criteria.")

    return found_any_filters
