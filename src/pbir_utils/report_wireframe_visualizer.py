import os
import tempfile
import webbrowser
from pathlib import Path

from .common import iter_pages, extract_visual_info
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


def _get_visual_objects(page_folder: str) -> list[dict]:
    """
    Extract visual information as a list of dictionaries for the template.

    Args:
        page_folder (str): Path to the page folder.

    Returns:
        list[dict]: List of visual objects with properties.
    """
    visuals_info = extract_visual_info(page_folder)
    visuals_list = []

    for vid, info in visuals_info.items():
        visuals_list.append(
            {
                "id": vid,
                "x": _parse_coordinate(info["x"]),
                "y": _parse_coordinate(info["y"]),
                "width": _parse_coordinate(info["width"]),
                "height": _parse_coordinate(info["height"]),
                "visualType": info["visualType"],
                "parentGroupName": info["parentGroupName"],
                "isHidden": info["isHidden"],
            }
        )

    return visuals_list


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
    for page_id, page_folder_path, page_data in iter_pages(report_path):
        try:
            page_name = page_data.get("name")
            display_name = page_data.get("displayName")
            width = page_data.get("width")
            height = page_data.get("height")
            is_hidden = page_data.get("visibility") == "HiddenInViewMode"

            # 1a. Early Page Filter
            if pages and page_name not in pages and display_name not in pages:
                continue

            # Get raw visuals
            raw_visuals = _get_visual_objects(page_folder_path)

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

    # 5. Render Template
    try:
        template_dir = Path(__file__).parent / "templates"
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "htm", "xml", "j2"]),
        )
        template = env.get_template("wireframe.html.j2")

        report_name = Path(report_path).name.replace(".Report", "")

        html_content = template.render(report_name=report_name, pages=filtered_pages)

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
