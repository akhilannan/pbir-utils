import os
import json
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go


def load_json(filepath):
    """
    Load JSON data from a file.

    Args:
        filepath (str): Path to the JSON file.

    Returns:
        dict: Parsed JSON data.
    """
    with open(filepath, "r") as file:
        return json.load(file)


def extract_page_info(page_folder):
    """
    Extract page information from the `page.json` file in a page folder.

    Args:
        page_folder (str): Path to the page folder.

    Returns:
        tuple: A tuple containing page display name, width, and height.

    Raises:
        FileNotFoundError: If `page.json` does not exist in the specified folder.
    """
    page_json_path = os.path.join(page_folder, "page.json")
    if not os.path.exists(page_json_path):
        raise FileNotFoundError(f"{page_json_path} does not exist")
    page_data = load_json(page_json_path)
    return page_data["displayName"], page_data["width"], page_data["height"]


def extract_visual_info(visuals_folder):
    """
    Extract visual information from `visual.json` files in a visuals folder.

    Args:
        visuals_folder (str): Path to the visuals folder.

    Returns:
        dict: A dictionary with visual ID as keys and tuples of visual information as values.
    """
    visuals = {}
    for visual_id in os.listdir(visuals_folder):
        visual_json_path = os.path.join(visuals_folder, visual_id, "visual.json")
        if not os.path.exists(visual_json_path):
            continue
        visual_data = load_json(visual_json_path)
        position = visual_data["position"]
        visuals[visual_id] = (
            position["x"],
            position["y"],
            position["width"],
            position["height"],
            visual_data.get("visual", {}).get("visualType", "Group"),
            visual_data.get("parentGroupName"),
            visual_data.get("isHidden", False)
        )
    return visuals


def adjust_visual_positions(visuals):
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
            is_hidden
        )
        for vid, (x, y, width, height, name, parent, is_hidden) in visuals.items()
    }


def create_wireframe_figure(
    page_name, page_width, page_height, visuals_info, show_hidden=True
):
    """
    Create a Plotly figure for the wireframe of a page.

    Args:
        page_name (str): Name of the page.
        page_width (int): Width of the page.
        page_height (int): Height of the page.
        visuals_info (dict): Dictionary with visual information.
        show_hidden (bool): Flag to determine if hidden visuals should be shown.

    Returns:
        go.Figure: Plotly figure object for the wireframe.
    """

    fig = go.Figure()

    adjusted_visuals = adjust_visual_positions(visuals_info)

    # Sort adjusted_visuals by name and visual_id
    sorted_visuals = sorted(adjusted_visuals.items(), key=lambda x: (x[1][4], x[0]))
    legend_labels = []
    for visual_id, (x, y, width, height, name, _, is_hidden) in sorted_visuals:
        if not show_hidden and is_hidden:
            continue
        line_style = "dot" if is_hidden else "solid"
        # Calculate center of the box
        center_x = x + width / 2
        center_y = y + height / 2

        # Add the rectangle with an invisible line to the center
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
                    showlegend=True
                )
            )

    legend_width_pixel = max(len(label) for label in legend_labels) * 7
    fig.update_xaxes(range=[0, page_width], showticklabels=True)
    fig.update_yaxes(range=[page_height, 0], showticklabels=True)
    fig.update_layout(
        width=page_width + legend_width_pixel,
        height=page_height,
        margin=dict(l=10, r=10, t=25, b=10),
        xaxis=dict(range=[0, page_width], showticklabels=True),
        yaxis=dict(range=[page_height, 0], showticklabels=True)
    )

    return fig


def apply_filters(pages_info, pages=None, visual_types=None, visual_ids=None):
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
            if (visual_types and vinfo[4] in visual_types)
            or (visual_ids and vid in visual_ids)
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
                    filtered_visuals_info or visuals_info
                )
            )

    return filtered_pages_info


def display_report_wireframes(
    root_folder, pages=None, visual_types=None, visual_ids=None, show_hidden=True
):
    """
    Generate and display wireframes for the report with optional filters.

    Args:
        root_folder (str): Path to the root folder of the report.
        pages (list, optional): List of page names to include. Defaults to None.
        visual_types (list, optional): List of visual types to include. Defaults to None.
        visual_ids (list, optional): List of visual IDs to include. Defaults to None.
        show_hidden (bool, optional): Flag to determine if hidden visuals should be shown. Defaults to True.
    """
    pages_info = []
    pages_folder = os.path.join(root_folder, "definition", "pages")
    for page_folder in os.listdir(pages_folder):
        page_folder_path = os.path.join(pages_folder, page_folder)
        if os.path.isdir(page_folder_path):
            try:
                page_name, page_width, page_height = extract_page_info(page_folder_path)
                visuals_folder = os.path.join(page_folder_path, "visuals")
                visuals_info = extract_visual_info(visuals_folder)

                pages_info.append((page_name, page_width, page_height, visuals_info))
            except FileNotFoundError as e:
                print(e)

    if not pages_info:
        print("No pages found.")
        return

    pages_info = apply_filters(pages_info, pages, visual_types, visual_ids)
    if not pages_info:
        print("No pages match the given filters.")
        return

    app = dash.Dash(__name__)

    app.layout = html.Div(
        [
            dcc.Tabs(
                id="tabs",
                value=pages_info[0][0],
                children=[
                    dcc.Tab(label=page_name, value=page_name)
                    for page_name, _, _, _ in pages_info
                ],
            ),
            html.Div(id="tab-content"),
        ]
    )

    @app.callback(Output("tab-content", "children"), Input("tabs", "value"))
    def render_content(selected_tab):
        for page_name, page_width, page_height, visuals_info in pages_info:
            if page_name == selected_tab:
                fig = create_wireframe_figure(
                    page_name, page_width, page_height, visuals_info, show_hidden
                )
                return dcc.Graph(figure=fig)
        return html.Div("Page not found")

    app.run_server(debug=True)