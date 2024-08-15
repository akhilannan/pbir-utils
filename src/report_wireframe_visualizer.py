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
        visual_folder = os.path.join(visuals_folder, visual_id)
        visual_json_path = os.path.join(visual_folder, "visual.json")
        if not os.path.exists(visual_json_path):
            continue
        visual_data = load_json(visual_json_path)
        name = visual_data.get("visual", {}).get("visualType", "Group")
        parent_id = visual_data.get("parentGroupName")
        x = visual_data["position"]["x"]
        y = visual_data["position"]["y"]
        width = visual_data["position"]["width"]
        height = visual_data["position"]["height"]
        is_hidden = visual_data.get("isHidden", False)
        visuals[visual_id] = (x, y, width, height, name, parent_id, is_hidden)
    return visuals


def adjust_visual_positions(visuals):
    """
    Adjust visual positions based on parent-child relationships.

    Args:
        visuals (dict): Dictionary with visual information.

    Returns:
        dict: Dictionary with adjusted visual positions.
    """
    adjusted = {}
    for visual_id, (x, y, width, height, name, parent_id, is_hidden) in visuals.items():
        if parent_id and parent_id in visuals:
            parent_x, parent_y, _, _, _, _, _ = visuals[parent_id]
            x += parent_x
            y += parent_y
        adjusted[visual_id] = (x, y, width, height, name, parent_id, is_hidden)
    return adjusted


def create_wireframe_figure(page_name, page_width, page_height, visuals_info):
    """
    Create a Plotly figure for the wireframe of a page.

    Args:
        page_name (str): Name of the page.
        page_width (int): Width of the page.
        page_height (int): Height of the page.
        visuals_info (dict): Dictionary with visual information.

    Returns:
        go.Figure: Plotly figure object for the wireframe.
    """
    fig = go.Figure()

    adjusted_visuals = adjust_visual_positions(visuals_info)
    
    for visual_id, (x, y, width, height, name, parent_id, is_hidden) in adjusted_visuals.items():
        line_style = 'dot' if is_hidden else 'solid'
        
        if name != 'Group':
            fig.add_trace(
                go.Scatter(
                    x=[x, x + width, x + width, x, x],
                    y=[y, y, y + height, y + height, y],
                    mode='lines',
                    line=dict(color='black', dash=line_style),
                    text=name,
                    hovertext=f'ID: {visual_id}',
                    hoverinfo='text'
                )
            )
            fig.add_annotation(
                text=name,
                x=x + width / 2,
                y=y + height / 2,
                showarrow=False,
                font=dict(size=10),
                align='center',
                yshift=5
            )

    fig.update_xaxes(range=[0, page_width], showticklabels=True)
    fig.update_yaxes(range=[page_height, 0], showticklabels=True)

    fig.update_layout(
        title=f'{page_name} Wireframe',
        showlegend=False,
        width=800,
        height=600,
        margin=dict(l=10, r=10, t=30, b=10)
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
        if pages and page_name not in pages:
            continue

        filtered_visuals_info = {}
        for vid, vinfo in visuals_info.items():
            visual_type = vinfo[4]
            if (visual_types and visual_type in visual_types) or (
                visual_ids and vid in visual_ids
            ):
                filtered_visuals_info[vid] = vinfo
                parent_id = vinfo[5]
                if parent_id and parent_id in visuals_info:
                    filtered_visuals_info[parent_id] = visuals_info[parent_id]

        if filtered_visuals_info:
            filtered_pages_info.append(
                (page_name, page_width, page_height, filtered_visuals_info)
            )
        elif not visual_types and not visual_ids:
            filtered_pages_info.append(
                (page_name, page_width, page_height, visuals_info)
            )

    return filtered_pages_info


def display_report_wireframes(
    root_folder, pages=None, visual_types=None, visual_ids=None
):
    """
    Generate and display wireframes for the report with optional filters.

    Args:
        root_folder (str): Path to the root folder of the report.
        pages (list, optional): List of page names to include. Defaults to None.
        visual_types (list, optional): List of visual types to include. Defaults to None.
        visual_ids (list, optional): List of visual IDs to include. Defaults to None.
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
                    page_name, page_width, page_height, visuals_info
                )
                return dcc.Graph(figure=fig)
        return html.Div("Page not found")

    app.run_server(debug=True)