import os

from .common import load_json, iter_pages
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


def _extract_visual_info(visuals_folder: str) -> dict:
    """
    Extract visual information from `visual.json` files in a visuals folder.

    Args:
        visuals_folder (str): Path to the visuals folder containing visual subdirectories.

    Returns:
        dict: A dictionary with visual IDs as keys and tuples of visual information as values.
              Each tuple contains (x, y, width, height, visualType, parentGroupName, isHidden).
    """
    visuals = {}
    for visual_folder_name in os.listdir(visuals_folder):
        visual_json_path = os.path.join(
            visuals_folder, visual_folder_name, "visual.json"
        )
        if not os.path.exists(visual_json_path):
            continue

        visual_data = load_json(visual_json_path)
        visual_id = visual_data.get(
            "name"
        )  # Use the ID from the JSON, not the folder name

        if not visual_id:
            continue

        position = visual_data["position"]

        visuals[visual_id] = (
            _parse_coordinate(position["x"]),
            _parse_coordinate(position["y"]),
            _parse_coordinate(position["width"]),
            _parse_coordinate(position["height"]),
            visual_data.get("visual", {}).get("visualType", "Group"),
            visual_data.get("parentGroupName"),
            visual_data.get("isHidden", False),
        )

    return visuals


def _adjust_visual_positions(visuals: dict) -> dict:
    """
    Adjust visual positions based on parent-child relationships.

    Args:
        visuals (dict): Dictionary with visual information.

    Returns:
        dict: Dictionary with adjusted visual positions.
    """
    return {
        vid: (
            x + visuals[parent][0] if parent in visuals else x,
            y + visuals[parent][1] if parent in visuals else y,
            width,
            height,
            name,
            parent,
            is_hidden,
        )
        for vid, (x, y, width, height, name, parent, is_hidden) in visuals.items()
    }


def _create_wireframe_figure(
    page_width: int, page_height: int, visuals_info: dict, show_hidden: bool = True
):
    """
    Create a Plotly figure for the wireframe of a page.

    Args:
        page_width (int): Width of the page.
        page_height (int): Height of the page.
        visuals_info (dict): Dictionary with visual information.
        show_hidden (bool): Flag to determine if hidden visuals should be shown. Defaults to True.

    Returns:
        go.Figure: Plotly figure object for the wireframe.
    """
    import plotly.graph_objects as go

    fig = go.Figure()

    adjusted_visuals = _adjust_visual_positions(visuals_info)
    sorted_visuals = sorted(adjusted_visuals.items(), key=lambda x: (x[1][4], x[0]))

    legend_labels = []
    for visual_id, (x, y, width, height, name, _, is_hidden) in sorted_visuals:
        if not show_hidden and is_hidden:
            continue

        line_style = "dot" if is_hidden else "solid"
        center_x = x + width / 2
        center_y = y + height / 2

        if name != "Group":
            label = f"{name} ({visual_id})"
            legend_labels.append(label)
            fig.add_trace(
                go.Scatter(
                    x=[x, x + width, x + width, x, x, None, center_x, None],
                    y=[y, y, y + height, y + height, y, None, center_y, None],
                    mode="lines+text",
                    line=dict(color="black", dash=line_style),
                    text=[None, None, None, None, None, None, name, None],
                    textposition="middle center",
                    hovertext=f"Visual ID: {visual_id}<br>Visual Type: {name}",
                    hoverinfo="text",
                    name=label,
                    showlegend=True,
                )
            )

    legend_width_pixel = max((len(label) for label in legend_labels), default=0) * 7
    fig.update_layout(
        width=page_width + legend_width_pixel,
        height=page_height,
        margin=dict(l=10, r=10, t=25, b=10),
        xaxis=dict(range=[0, page_width], showticklabels=True),
        yaxis=dict(range=[page_height, 0], showticklabels=True),
    )

    return fig


def _apply_filters(
    pages_info: list,
    pages: list = None,
    visual_types: list = None,
    visual_ids: list = None,
) -> list:
    """
    Filter pages and visuals based on given criteria.

    Args:
        pages_info (list): List of tuples containing page information.
        pages (list, optional): List of page names to include. Defaults to None.
        visual_types (list, optional): List of visual types to include. Defaults to None.
        visual_ids (list, optional): List of visual IDs to include. Defaults to None.

    Returns:
        list: Filtered list of tuples containing page information.
    """
    filtered_pages_info = []
    for page_id, page_name, page_width, page_height, visuals_info in pages_info:
        if pages and page_id not in pages:
            continue

        filtered_visuals_info = {
            vid: vinfo
            for vid, vinfo in visuals_info.items()
            if (not visual_types or vinfo[4] in visual_types)
            and (not visual_ids or vid in visual_ids)
        }

        parents_to_add = {
            parent_id: visuals_info[parent_id]
            for _, vinfo in filtered_visuals_info.items()
            if (parent_id := vinfo[5]) and parent_id not in filtered_visuals_info
        }

        filtered_visuals_info.update(parents_to_add)

        if filtered_visuals_info or (not visual_types and not visual_ids):
            filtered_pages_info.append(
                (
                    page_id,
                    page_name,
                    page_width,
                    page_height,
                    filtered_visuals_info or visuals_info,
                )
            )

    return filtered_pages_info


def display_report_wireframes(
    report_path: str,
    pages: list = None,
    visual_types: list = None,
    visual_ids: list = None,
    show_hidden: bool = True,
) -> None:
    """
    Generate and display wireframes for the report with optional filters.

    Args:
        report_path (str): Path to the root folder of the report.
        pages (list, optional): List of page IDs to include. Defaults to None.
        visual_types (list, optional): List of visual types to include. Defaults to None.
        visual_ids (list, optional): List of visual IDs to include. Defaults to None.
        show_hidden (bool, optional): Flag to determine if hidden visuals should be shown. Defaults to True.
    """
    console.print_action_heading("Displaying report wireframes", False)
    pages_info = []

    for page_id, page_folder_path, page_data in iter_pages(report_path):
        try:
            page_name = page_data.get("name")
            display_name = page_data.get("displayName")
            width = page_data.get("width")
            height = page_data.get("height")

            visuals_folder_path = os.path.join(page_folder_path, "visuals")
            if os.path.exists(visuals_folder_path):
                visuals_info = _extract_visual_info(visuals_folder_path)
            else:
                visuals_info = {}
            pages_info.append((page_name, display_name, width, height, visuals_info))
        except Exception as e:
            print(e)

    if not pages_info:
        print("No pages found.")
        return

    filtered_pages_info = _apply_filters(pages_info, pages, visual_types, visual_ids)
    if not filtered_pages_info:
        print("No pages match the given filters.")
        return

    page_order = _get_page_order(report_path)
    sorted_pages_info = sorted(
        filtered_pages_info, key=lambda x: page_order.index(x[0])
    )

    # Lazy import heavy dependencies
    import dash
    from dash import dcc, html, Input, Output

    app = dash.Dash(__name__)
    app.layout = html.Div(
        [
            dcc.Tabs(
                id="tabs",
                value=sorted_pages_info[0][0],
                children=[
                    dcc.Tab(label=page_name, value=page_id)
                    for page_id, page_name, _, _, _ in sorted_pages_info
                ],
            ),
            html.Div(id="tab-content"),
        ]
    )

    @app.callback(Output("tab-content", "children"), Input("tabs", "value"))
    def render_content(selected_tab: str):
        for _, _, page_width, page_height, visuals_info in filter(
            lambda item: item[0] == selected_tab, sorted_pages_info
        ):
            fig = _create_wireframe_figure(
                page_width, page_height, visuals_info, show_hidden
            )
            return dcc.Graph(figure=fig)
        return html.Div("Page not found")

    app.run(debug=True, use_reloader=False)
