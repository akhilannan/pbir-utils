import os
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go

from .json_utils import _load_json


def _extract_page_info(page_folder: str) -> tuple:
    """
    Extract page information from the `page.json` file in a page folder.

    Args:
        page_folder (str): Path to the page folder containing the `page.json` file.

    Returns:
        tuple: A tuple containing the page display name, width, and height.

    Raises:
        FileNotFoundError: If the `page.json` file does not exist in the specified folder.
    """
    page_json_path = os.path.join(page_folder, "page.json")

    if not os.path.exists(page_json_path):
        # Raise an error if the `page.json` file is missing
        raise FileNotFoundError(f"{page_json_path} does not exist")

    page_data = _load_json(page_json_path)

    # Return the display name, width, and height from the page data
    return page_data["displayName"], page_data["width"], page_data["height"]


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
    # Iterate through each subdirectory in the visuals folder
    for visual_id in os.listdir(visuals_folder):
        visual_json_path = os.path.join(visuals_folder, visual_id, "visual.json")
        if not os.path.exists(visual_json_path):
            continue  # Skip if the visual.json file does not exist

        visual_data = _load_json(visual_json_path)
        position = visual_data["position"]

        # Extract and store visual information in a tuple
        visuals[visual_id] = (
            position["x"],
            position["y"],
            position["width"],
            position["height"],
            visual_data.get("visual", {}).get("visualType", "Group"),
            visual_data.get("parentGroupName"),
            visual_data.get("isHidden", False),
        )

    return visuals


def _adjust_visual_positions(visuals: dict) -> dict:
    """
    Adjust visual positions based on parent-child relationships.

    Args:
        visuals (dict): Dictionary with visual information. Each key is a visual ID and
                        the value is a tuple containing (x, y, width, height, name, parent, is_hidden).

    Returns:
        dict: Dictionary with adjusted visual positions, where each visual's position is updated
              according to its parent's position.
    """
    return {
        vid: (
            # Adjust position based on parent's coordinates, if parent exists
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
) -> go.Figure:
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

    fig = go.Figure()

    # Adjust visual positions and sort by name and visual_id
    adjusted_visuals = _adjust_visual_positions(visuals_info)
    sorted_visuals = sorted(adjusted_visuals.items(), key=lambda x: (x[1][4], x[0]))

    legend_labels = []
    for visual_id, (x, y, width, height, name, _, is_hidden) in sorted_visuals:
        if not show_hidden and is_hidden:
            continue  # Skip hidden visuals if not showing them

        line_style = "dot" if is_hidden else "solid"
        # Calculate center of the box
        center_x = x + width / 2
        center_y = y + height / 2

        # Add the visual rectangle with an invisible line to the center
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

    # Update layout space to include legend and adjust dimensions
    legend_width_pixel = max(len(label) for label in legend_labels) * 7
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
    for page_name, page_width, page_height, visuals_info in pages_info:

        # Skip this page if it's not in the specified pages list
        if pages and page_name not in pages:
            continue

        # Filter visuals based on visual_types or visual_ids
        filtered_visuals_info = {
            vid: vinfo
            for vid, vinfo in visuals_info.items()
            if (not visual_types or vinfo[4] in visual_types)
            and (not visual_ids or vid in visual_ids)
        }

        # Collect parent visuals to add after the loop
        parents_to_add = {
            parent_id: visuals_info[parent_id]
            for _, vinfo in filtered_visuals_info.items()
            if (parent_id := vinfo[5]) and parent_id not in filtered_visuals_info
        }

        # Add parent visuals to the filtered visuals dictionary
        filtered_visuals_info.update(parents_to_add)

        # Add the page to the result if there are filtered visuals or no visual filters were applied
        if filtered_visuals_info or (not visual_types and not visual_ids):
            filtered_pages_info.append(
                (
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
        pages (list, optional): List of page names to include. Defaults to None.
        visual_types (list, optional): List of visual types to include. Defaults to None.
        visual_ids (list, optional): List of visual IDs to include. Defaults to None.
        show_hidden (bool, optional): Flag to determine if hidden visuals should be shown. Defaults to True.
    """
    # Path to the folder containing page definitions
    pages_folder = os.path.join(report_path, "definition", "pages")
    pages_info = []

    # Collect page and visual information
    for page_folder in filter(
        lambda x: os.path.isdir(os.path.join(pages_folder, x)), os.listdir(pages_folder)
    ):
        page_folder_path = os.path.join(pages_folder, page_folder)
        try:
            page_info = _extract_page_info(page_folder_path)
            visuals_info = _extract_visual_info(
                os.path.join(page_folder_path, "visuals")
            )
            pages_info.append((*page_info, visuals_info))
        except FileNotFoundError as e:
            print(e)

    if not pages_info:
        print("No pages found.")
        return

    # Apply filters to the collected pages_info
    filtered_pages_info = _apply_filters(pages_info, pages, visual_types, visual_ids)
    if not filtered_pages_info:
        print("No pages match the given filters.")
        return

    # Initialize Dash app and layout
    app = dash.Dash(__name__)
    app.layout = html.Div(
        [
            dcc.Tabs(
                id="tabs",
                value=filtered_pages_info[0][0],
                children=[
                    dcc.Tab(label=page_name, value=page_name)
                    for page_name, _, _, _ in filtered_pages_info
                ],
            ),
            html.Div(id="tab-content"),
        ]
    )

    # Callback to render content based on selected tab
    @app.callback(Output("tab-content", "children"), Input("tabs", "value"))
    def render_content(selected_tab: str):
        for _, page_width, page_height, visuals_info in filter(
            lambda item: item[0] == selected_tab, filtered_pages_info
        ):
            fig = _create_wireframe_figure(
                page_width, page_height, visuals_info, show_hidden
            )
            return dcc.Graph(figure=fig)
        return html.Div("Page not found")

    # Run the Dash server
    app.run_server(debug=True)