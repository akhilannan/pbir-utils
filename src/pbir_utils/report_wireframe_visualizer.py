import os
import tempfile
import webbrowser
from pathlib import Path

from .common import (
    iter_pages,
    iter_visuals,
    load_json,
    traverse_pbir_json,
    extract_visual_info,
)
from .metadata_extractor import _get_page_order
from .console_utils import console


def _parse_coordinate(value) -> float:
    """
    Parse a coordinate value, handling potential string prefixes.
    """
    if isinstance(value, str):
        if value.startswith("@@__PRESERVE_FLOAT__@@"):
            value = value.replace("@@__PRESERVE_FLOAT__@@", "")
    return float(value)


def _extract_field_usage(data: dict, context: str, field_usage: dict) -> None:
    """
    Extract field usage from a JSON structure and update the field_usage dict.

    Args:
        data: The JSON data to traverse (bookmark or filterConfig).
        context: The context type ("Bookmarks" or "Filters").
        field_usage: Dict to update with field usage counts.
    """
    pending_table = None
    pending_attr_type = None

    for (
        table,
        field,
        used_in,
        expression,
        used_in_detail,
        attr_type,
    ) in traverse_pbir_json(data, context):
        if table and field:
            field_key = f"{table}.{field}"
            if field_key not in field_usage:
                field_usage[field_key] = {
                    "bookmark_count": 0,
                    "filter_count": 0,
                    "attr_type": attr_type,
                }
            if context == "Bookmarks":
                field_usage[field_key]["bookmark_count"] += 1
            elif context == "Filters":
                field_usage[field_key]["filter_count"] += 1
            pending_table = None
        elif table and not field:
            pending_table = table
            pending_attr_type = attr_type
        elif field and not table and pending_table:
            field_key = f"{pending_table}.{field}"
            if field_key not in field_usage:
                field_usage[field_key] = {
                    "bookmark_count": 0,
                    "filter_count": 0,
                    "attr_type": attr_type or pending_attr_type,
                }
            if context == "Bookmarks":
                field_usage[field_key]["bookmark_count"] += 1
            elif context == "Filters":
                field_usage[field_key]["filter_count"] += 1
            pending_table = None


def _adjust_visual_positions(visuals: list[dict]) -> list[dict]:
    """
    Adjust visual positions based on parent-child relationships (Groups).

    Children coordinates are relative to their parent group.
    """
    # Create a lookup for easy access by ID
    visual_map = {v["id"]: v for v in visuals}
    adjusted_visuals = []

    for visual in visuals:
        # Create a copy to modify
        adj_visual = visual.copy()

        parent_id = visual.get("parentGroupName")
        if parent_id and parent_id in visual_map:
            parent = visual_map[parent_id]
            adj_visual["x"] += parent["x"]
            adj_visual["y"] += parent["y"]

        adjusted_visuals.append(adj_visual)

    return adjusted_visuals


def _apply_wireframe_filters(
    pages_info: list,
    pages: list = None,
    visual_types: list = None,
    visual_ids: list = None,
) -> list:
    """
    Filter pages and visuals based on given criteria.
    """
    filtered_pages_info = []

    for page_obj in pages_info:
        # Filter Pages
        if (
            pages
            and page_obj["id"] not in pages
            and page_obj["display_name"] not in pages
        ):
            continue

        visuals = page_obj["visuals"]

        # Filter Visuals
        filtered_visuals = [
            v
            for v in visuals
            if (not visual_types or v["visualType"] in visual_types)
            and (not visual_ids or v["id"] in visual_ids)
        ]

        if filtered_visuals or (not visual_types and not visual_ids):
            # Update the page object with filtered visuals
            new_page_obj = page_obj.copy()
            new_page_obj["visuals"] = filtered_visuals
            filtered_pages_info.append(new_page_obj)

    return filtered_pages_info


def _build_fields_index(
    pages_data: list[dict], field_usage: dict[str, dict] = None
) -> dict:
    """
    Build a consolidated fields index for the Fields Pane.

    Aggregates visual fields from pages_data and merges with pre-extracted
    field usage from bookmarks/filters.

    Args:
        pages_data: List of page objects with visuals containing field info.
        field_usage: Pre-extracted field usage counts from bookmarks/filters.

    Returns:
        dict: Fields index with tables, fieldToVisuals, and fieldUsage.
    """
    tables: dict[str, dict] = {}
    field_to_visuals: dict[str, list[str]] = {}
    field_usage = field_usage or {}

    # Process visual fields from pages_data
    for page in pages_data:
        page_name = page["display_name"]

        for visual in page["visuals"]:
            visual_id = visual["id"]
            visual_fields = visual.get("fields", {})

            for table_name, table_data in visual_fields.items():
                if table_name not in tables:
                    tables[table_name] = {
                        "columns": set(),
                        "measures": set(),
                        "visualIds": set(),
                        "pageBreakdown": {},
                    }

                table_entry = tables[table_name]

                for col in table_data.get("columns", []):
                    table_entry["columns"].add(col)
                    field_key = f"{table_name}.{col}"
                    if field_key not in field_to_visuals:
                        field_to_visuals[field_key] = []
                    field_to_visuals[field_key].append(visual_id)

                for measure in table_data.get("measures", []):
                    table_entry["measures"].add(measure)
                    field_key = f"{table_name}.{measure}"
                    if field_key not in field_to_visuals:
                        field_to_visuals[field_key] = []
                    field_to_visuals[field_key].append(visual_id)

                table_entry["visualIds"].add(visual_id)
                table_entry["pageBreakdown"][page_name] = (
                    table_entry["pageBreakdown"].get(page_name, 0) + 1
                )

    # Add fields from bookmarks/filters that aren't in any visual
    for field_key, usage in field_usage.items():
        table_name, field_name = field_key.split(".", 1)
        if table_name not in tables:
            tables[table_name] = {
                "columns": set(),
                "measures": set(),
                "visualIds": set(),
                "pageBreakdown": {},
            }
        # Use attr_type if available, default to column
        if usage.get("attr_type") == "Measure":
            tables[table_name]["measures"].add(field_name)
        else:
            tables[table_name]["columns"].add(field_name)

    # Convert sets to sorted lists for JSON serialization
    for table_name, table_data in tables.items():
        tables[table_name] = {
            "columns": sorted(table_data["columns"]),
            "measures": sorted(table_data["measures"]),
            "visualCount": len(table_data["visualIds"]),
            "pageBreakdown": table_data["pageBreakdown"],
        }

    return {
        "tables": tables,
        "fieldToVisuals": field_to_visuals,
        "fieldUsage": field_usage,
    }


def display_report_wireframes(
    report_path: str,
    pages: list = None,
    visual_types: list = None,
    visual_ids: list = None,
    show_hidden: bool = True,
) -> None:
    """
    Generate and display wireframes using static HTML.

    Args:
        report_path (str): Path to the report root folder.
        pages (list, optional): List of page IDs/Names to include.
        visual_types (list, optional): List of visual types to include.
        visual_ids (list, optional): List of visual IDs to include.
        show_hidden (bool, optional): Show hidden visuals. Defaults to True.
    """
    console.print_action_heading("Generating report wireframes", False)
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    pages_data = []

    # 1. Extract Data
    field_usage: dict[str, dict] = {}
    definition_path = Path(report_path) / "definition"

    # 1a. Extract fields from bookmarks
    bookmarks_folder = definition_path / "bookmarks"
    if bookmarks_folder.exists():
        for bookmark_file in bookmarks_folder.glob("*.bookmark.json"):
            try:
                bookmark_data = load_json(str(bookmark_file))
                _extract_field_usage(bookmark_data, "Bookmarks", field_usage)
            except Exception:
                pass

    # 1b. Extract fields from report-level filters
    report_json = definition_path / "report.json"
    if report_json.exists():
        try:
            report_data = load_json(str(report_json))
            filter_config = report_data.get("filterConfig", {})
            if filter_config:
                _extract_field_usage(filter_config, "Filters", field_usage)
        except Exception:
            pass

    # 1c. Extract fields from page filters and page visuals
    for page_id, page_folder_path, page_data in iter_pages(report_path):
        try:
            page_name = page_data.get("name")
            display_name = page_data.get("displayName")
            width = page_data.get("width")
            height = page_data.get("height")
            is_hidden = page_data.get("visibility") == "HiddenInViewMode"

            # Extract fields from page-level filters
            filter_config = page_data.get("filterConfig", {})
            if filter_config:
                _extract_field_usage(filter_config, "Filters", field_usage)

            # Early Page Filter (skips visual processing if page filtered out)
            if pages and page_name not in pages and display_name not in pages:
                continue

            # Get raw visuals using common function
            visuals_map = extract_visual_info(page_folder_path, include_fields=True)

            # Convert dictionary to list format expected by template and position processing
            # Also parse coordinates since they come raw from load_json
            raw_visuals = []
            for vid, vdata in visuals_map.items():
                vdata["id"] = vid
                vdata["x"] = _parse_coordinate(vdata.get("x", 0))
                vdata["y"] = _parse_coordinate(vdata.get("y", 0))
                vdata["width"] = _parse_coordinate(vdata.get("width", 0))
                vdata["height"] = _parse_coordinate(vdata.get("height", 0))
                raw_visuals.append(vdata)

            # Adjust positions (handle groups)
            # We do this BEFORE filtering so that children get correct absolute coordinates
            adjusted_visuals = _adjust_visual_positions(raw_visuals)

            pages_data.append(
                {
                    "id": page_name,
                    "display_name": display_name,
                    "width": width,
                    "height": height,
                    "is_hidden": is_hidden,
                    "visuals": adjusted_visuals,
                }
            )
        except Exception as e:
            console.print_error(f"Error processing page {page_id}: {e}")

    if not pages_data:
        console.print_warning("No pages found in report.")
        return

    # 2. Filter Data
    filtered_pages = _apply_wireframe_filters(
        pages_data, pages, visual_types, visual_ids
    )

    if not filtered_pages:
        console.print_warning("No pages match the given filters.")
        return

    # 3. Sort Pages
    try:
        page_order = _get_page_order(report_path)
        # Create a map for O(1) lookup
        order_map = {pid: idx for idx, pid in enumerate(page_order)}

        filtered_pages.sort(key=lambda x: order_map.get(x["id"], 999))
    except Exception:  # nosec B110
        pass  # Fallback to extraction order

    # 4. Handle Hidden Visuals for Final Output
    if not show_hidden:
        for page in filtered_pages:
            page["visuals"] = [v for v in page["visuals"] if not v["isHidden"]]

    # 5. Build Fields Index for the Fields Pane
    # Includes fields from visuals, bookmarks, and page filters
    fields_index = _build_fields_index(filtered_pages, field_usage)

    # 6. Render Template
    try:
        template_dir = Path(__file__).parent / "templates"
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "htm", "xml", "j2"]),
        )
        template = env.get_template("wireframe.html.j2")

        report_name = Path(report_path).name.replace(".Report", "")

        html_content = template.render(
            report_name=report_name, pages=filtered_pages, fields_index=fields_index
        )

        # 6. Save and Open
        # We create a temporary file that persists so the browser can open it
        # Using delete=False
        fd, path = tempfile.mkstemp(
            suffix=".html", prefix=f"pbir_wireframe_{report_name}_"
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html_content)

        console.print_success(f"Wireframe generated: {path}")
        webbrowser.open(f"file://{path}")

    except Exception as e:
        console.print_error(f"Failed to render wireframe: {e}")
