"""
Filter clearing and inspection utilities for Power BI reports.

Contains functions for viewing and clearing filters at report, page, visual,
and slicer levels.
"""

from pathlib import Path
import re
from dataclasses import dataclass, field
from fnmatch import fnmatch

from .common import (
    load_json,
    write_json,
    iter_pages,
    iter_visuals,
)
from .console_utils import console
from .filter_utils import get_target_from_field, parse_target_components

__all__ = ["clear_filters"]


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


def _filter_matches_criteria(
    target: str,
    table_name: str,
    column_name: str,
    include_tables: list[str] | None = None,
    include_columns: list[str] | None = None,
    include_fields: list[str] | None = None,
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
        target = get_target_from_field(field_def)

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
    include_tables: list[str] | None = None,
    include_columns: list[str] | None = None,
    include_fields: list[str] | None = None,
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

        target = get_target_from_field(f.get("field"))
        table_name, column_name = parse_target_components(target)

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
    include_tables: list[str] | None = None,
    include_columns: list[str] | None = None,
    include_fields: list[str] | None = None,
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

        target = get_target_from_field(f.get("field"))
        table_name, column_name = parse_target_components(target)

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
    target_visual: str | None = None,
    include_tables: list[str] | None = None,
    include_columns: list[str] | None = None,
    include_fields: list[str] | None = None,
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
            visual_json_path = Path(visual_folder) / "visual.json"
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
    target_page: str | None = None,
    target_visual: str | None = None,
    include_tables: list[str] | None = None,
    include_columns: list[str] | None = None,
    include_fields: list[str] | None = None,
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
    report_json_path = Path(report_path) / "definition" / "report.json"
    if report_json_path.exists():
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
    elif not Path(report_path).name.endswith(".Report"):
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
                    write_json(Path(page_path) / "page.json", page_data)
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
