from unittest.mock import patch, MagicMock
import pytest

from pbir_utils.report_wireframe_visualizer import (
    _extract_visual_info,
    _adjust_visual_positions,
    _create_wireframe_figure,
    _apply_filters,
    display_report_wireframes,
)


@pytest.fixture
def mock_page_json():
    return {
        "name": "ReportSection1",
        "displayName": "Page 1",
        "width": 1280,
        "height": 720,
    }


@pytest.fixture
def mock_visual_json():
    return {
        "name": "visual1",
        "position": {"x": 10, "y": 20, "width": 100, "height": 200},
        "visual": {"visualType": "columnChart"},
        "parentGroupName": None,
        "isHidden": False,
    }


@pytest.fixture
def mock_group_json():
    return {
        "name": "group1",
        "position": {"x": 5, "y": 5, "width": 300, "height": 300},
        "visual": {"visualType": "Group"},
        "parentGroupName": None,
        "isHidden": False,
    }


@pytest.fixture
def mock_child_visual_json():
    return {
        "name": "child1",
        "position": {"x": 10, "y": 10, "width": 50, "height": 50},
        "visual": {"visualType": "card"},
        "parentGroupName": "visual_group",
        "isHidden": True,
    }


@patch("pbir_utils.report_wireframe_visualizer.load_json")
@patch("os.path.exists")
@patch("os.listdir")
def test_extract_visual_info(
    mock_listdir, mock_exists, mock_load_json, mock_visual_json, mock_child_visual_json
):
    mock_listdir.return_value = ["visual1", "visual2"]
    mock_exists.return_value = True

    # Return different data for different calls
    def side_effect(path):
        if "visual1" in path:
            return mock_visual_json
        # Create a copy for visual2 with correct name
        v2 = mock_child_visual_json.copy()
        v2["name"] = "visual2"
        return v2

    mock_load_json.side_effect = side_effect

    visuals = _extract_visual_info("dummy/visuals")
    assert len(visuals) == 2
    assert "visual1" in visuals
    assert "visual2" in visuals
    assert visuals["visual1"][4] == "columnChart"


@patch("pbir_utils.report_wireframe_visualizer.load_json")
@patch("os.path.exists")
@patch("os.listdir")
def test_extract_visual_info_renamed_folders(
    mock_listdir, mock_exists, mock_load_json, mock_visual_json
):
    """Test that visual info is extracted correctly even if folder name differs from visual ID."""
    mock_listdir.return_value = ["Folder_Visual1"]
    mock_exists.return_value = True

    # Mock visual.json content where name="Visual1" but folder is "Folder_Visual1"
    visual_data = mock_visual_json.copy()
    visual_data["name"] = "Visual1"
    mock_load_json.return_value = visual_data

    visuals = _extract_visual_info("dummy/visuals")

    assert len(visuals) == 1
    assert "Visual1" in visuals  # Key should be the ID from JSON
    assert "Folder_Visual1" not in visuals  # Key should NOT be the folder name


@patch("pbir_utils.report_wireframe_visualizer.load_json")
@patch("os.path.exists")
@patch("os.listdir")
def test_extract_visual_info_string_and_prefixed_coordinates(
    mock_listdir, mock_exists, mock_load_json
):
    """Test that string coordinates and @@__PRESERVE_FLOAT__@@ prefixes are parsed correctly."""
    mock_listdir.return_value = ["visual1", "visual2"]
    mock_exists.return_value = True

    def side_effect(path):
        if "visual1" in path:
            # String coordinates
            return {
                "name": "visual1",
                "position": {"x": "100", "y": "200", "width": "50", "height": "60"},
                "visual": {"visualType": "chart"},
            }
        # Preserve float prefix coordinates
        return {
            "name": "visual2",
            "position": {
                "x": "@@__PRESERVE_FLOAT__@@123.456",
                "y": "@@__PRESERVE_FLOAT__@@78.9",
                "width": 100,
                "height": 100,
            },
            "visual": {"visualType": "card"},
        }

    mock_load_json.side_effect = side_effect

    visuals = _extract_visual_info("dummy/visuals")

    assert len(visuals) == 2
    # String coordinates should be parsed to floats
    assert visuals["visual1"][0] == 100.0
    assert visuals["visual1"][1] == 200.0
    # Preserved float prefix should be stripped and parsed
    assert visuals["visual2"][0] == pytest.approx(123.456)
    assert visuals["visual2"][1] == pytest.approx(78.9)


def test_adjust_visual_positions():
    visuals = {
        "group1": (10, 10, 200, 200, "Group", None, False),
        "child1": (5, 5, 50, 50, "card", "group1", False),
        "orphan": (100, 100, 50, 50, "card", "missing_parent", False),
    }

    adjusted = _adjust_visual_positions(visuals)

    # Child should be offset by parent position
    assert adjusted["child1"][0] == 15  # 5 + 10
    assert adjusted["child1"][1] == 15  # 5 + 10

    # Orphan should remain as is (or handled gracefully if code allows)
    # Code says: x + visuals[parent][0] if parent in visuals else x
    assert adjusted["orphan"][0] == 100


def test_create_wireframe_figure():
    visuals_info = {
        "v1": (10, 10, 100, 100, "chart", None, False),
        "v2": (200, 200, 50, 50, "card", None, True),
    }

    # Test with show_hidden=True
    fig = _create_wireframe_figure(1000, 800, visuals_info, show_hidden=True)
    assert fig is not None
    # We expect 2 traces (one for each visual)
    assert len(fig.data) == 2

    # Test with show_hidden=False
    fig = _create_wireframe_figure(1000, 800, visuals_info, show_hidden=False)
    assert len(fig.data) == 1


def test_apply_filters():
    pages_info = [
        (
            "p1",
            "Page 1",
            100,
            100,
            {
                "v1": (0, 0, 10, 10, "chart", None, False),
                "v2": (20, 20, 10, 10, "card", None, False),
            },
        ),
        ("p2", "Page 2", 100, 100, {}),
    ]

    # Filter by page
    filtered = _apply_filters(pages_info, pages=["p1"])
    assert len(filtered) == 1
    assert filtered[0][0] == "p1"

    # Filter by visual type
    filtered = _apply_filters(pages_info, visual_types=["chart"])
    assert len(filtered) == 1  # p2 is empty, p1 has chart
    assert len(filtered[0][4]) == 1  # only v1

    # Filter by visual id
    filtered = _apply_filters(pages_info, visual_ids=["v2"])
    assert len(filtered) == 1
    assert "v2" in filtered[0][4]


@patch("dash.Dash")
@patch("pbir_utils.report_wireframe_visualizer._get_page_order")
@patch("pbir_utils.report_wireframe_visualizer._extract_visual_info")
@patch("pbir_utils.report_wireframe_visualizer.iter_pages")
@patch("os.path.exists")
def test_display_report_wireframes(
    mock_exists,
    mock_iter_pages,
    mock_extract_visual,
    mock_get_order,
    mock_dash,
):
    mock_exists.return_value = True
    # iter_pages yields (page_id, page_folder_path, page_data)
    mock_iter_pages.return_value = iter(
        [
            (
                "p1",
                "dummy/report/definition/pages/Page1",
                {"name": "p1", "displayName": "Page 1", "width": 100, "height": 100},
            )
        ]
    )
    mock_extract_visual.return_value = {}
    mock_get_order.return_value = ["p1"]

    mock_app = MagicMock()
    mock_dash.return_value = mock_app

    display_report_wireframes("dummy/report")

    mock_app.run.assert_called_once()
