import os
from unittest.mock import patch

from conftest import create_dummy_file
from pbir_utils.bookmark_utils import (
    remove_unused_bookmarks,
    cleanup_invalid_bookmarks,
)
from pbir_utils.visual_utils import (
    remove_unused_custom_visuals,
    disable_show_items_with_no_data,
    remove_hidden_visuals_never_shown,
)
from pbir_utils.page_utils import (
    remove_empty_pages,
    set_first_page_as_active,
)
from pbir_utils.common import load_json


def test_remove_unused_bookmarks_no_file(tmp_path):
    # Test when bookmarks.json doesn't exist
    report_path = str(tmp_path)
    with patch("builtins.print") as mock_print:
        remove_unused_bookmarks(report_path)
        mock_print.assert_called()
        mock_print.assert_called()
        assert any(
            "No bookmarks found" in str(call) for call in mock_print.call_args_list
        )


def test_remove_unused_custom_visuals_none(tmp_path):
    # Test when no custom visuals exist
    report_path = str(tmp_path)
    create_dummy_file(tmp_path, "definition/report.json", {"publicCustomVisuals": []})
    with patch("builtins.print") as mock_print:
        remove_unused_custom_visuals(report_path)
        mock_print.assert_called()
        mock_print.assert_called()
        assert any(
            "No custom visuals found" in str(call) for call in mock_print.call_args_list
        )


def test_disable_show_items_with_no_data_nested(tmp_path):
    # Test nested structure
    report_path = str(tmp_path)
    visual_json = {
        "visual": {"objects": {"some_obj": [{"properties": {"showAll": True}}]}}
    }
    create_dummy_file(
        tmp_path, "definition/pages/Page1/visuals/visual.json", visual_json
    )

    disable_show_items_with_no_data(report_path)

    updated_data = load_json(
        os.path.join(report_path, "definition/pages/Page1/visuals/visual.json")
    )
    assert (
        "showAll" not in updated_data["visual"]["objects"]["some_obj"][0]["properties"]
    )


def test_remove_empty_pages_all_empty(tmp_path):
    report_path = str(tmp_path)
    create_dummy_file(
        tmp_path,
        "definition/pages/pages.json",
        {"pageOrder": ["Page1", "Page2"], "activePageName": "Page1"},
    )
    # Create empty folders (no visuals)
    os.makedirs(
        os.path.join(report_path, "definition/pages/Page1/visuals"), exist_ok=True
    )
    os.makedirs(
        os.path.join(report_path, "definition/pages/Page2/visuals"), exist_ok=True
    )

    with patch("builtins.print") as mock_print:
        remove_empty_pages(report_path)
        mock_print.assert_called()
        # Should keep first page as placeholder
        pages_data = load_json(os.path.join(report_path, "definition/pages/pages.json"))
        assert pages_data["pageOrder"] == ["Page1"]
        assert pages_data["activePageName"] == "Page1"


def test_cleanup_invalid_bookmarks(tmp_path):
    report_path = str(tmp_path)
    # Valid page
    create_dummy_file(tmp_path, "definition/pages/pages.json", {"pageOrder": ["Page1"]})
    # Fix: Create visual.json inside a folder named v1, or just visual.json if it's recursive
    # But to be safe and match structure:
    create_dummy_file(
        tmp_path, "definition/pages/Page1/visuals/v1/visual.json", {"name": "v1"}
    )

    # Bookmark referencing invalid page
    create_dummy_file(
        tmp_path,
        "definition/bookmarks/b1.bookmark.json",
        {"name": "b1", "explorationState": {"activeSection": "InvalidPage"}},
    )

    # Bookmark referencing valid page but invalid visual
    create_dummy_file(
        tmp_path,
        "definition/bookmarks/b2.bookmark.json",
        {
            "name": "b2",
            "explorationState": {
                "activeSection": "Page1",
                "sections": {
                    "Page1": {"visualContainers": {"v1": {}, "invalid_v": {}}}
                },
            },
        },
    )

    create_dummy_file(
        tmp_path,
        "definition/bookmarks/bookmarks.json",
        {"items": [{"name": "b1"}, {"name": "b2"}]},
    )

    cleanup_invalid_bookmarks(report_path)

    # b1 should be removed
    assert not os.path.exists(
        os.path.join(report_path, "definition/bookmarks/b1.bookmark.json")
    )

    # b2 should be cleaned
    b2_data = load_json(
        os.path.join(report_path, "definition/bookmarks/b2.bookmark.json")
    )
    assert "v1" in b2_data["explorationState"]["sections"]["Page1"]["visualContainers"]
    assert (
        "invalid_v"
        not in b2_data["explorationState"]["sections"]["Page1"]["visualContainers"]
    )


def test_remove_hidden_visuals_never_shown_cleanup(tmp_path):
    report_path = str(tmp_path)
    # Create a page with interactions
    create_dummy_file(
        tmp_path,
        "definition/pages/Page1/page.json",
        {
            "name": "Page1",
            "visualInteractions": [
                {
                    "source": "v1",
                    "target": "hidden_v",
                },  # Interaction with hidden visual
                {"source": "v1", "target": "v2"},  # Valid interaction
            ],
        },
    )

    # Create visible visual v1
    create_dummy_file(
        tmp_path, "definition/pages/Page1/visuals/v1/visual.json", {"name": "v1"}
    )

    # Create visible visual v2
    create_dummy_file(
        tmp_path, "definition/pages/Page1/visuals/v2/visual.json", {"name": "v2"}
    )

    # Create hidden visual hidden_v
    hidden_v_path = create_dummy_file(
        tmp_path,
        "definition/pages/Page1/visuals/hidden_v/visual.json",
        {"name": "hidden_v", "isHidden": True},
    )
    hidden_v_folder = os.path.dirname(hidden_v_path)

    # Create bookmarks (none show hidden_v)
    create_dummy_file(tmp_path, "definition/bookmarks/bookmarks.json", {"items": []})

    remove_hidden_visuals_never_shown(report_path)

    # Verify hidden visual folder is removed
    assert not os.path.exists(hidden_v_folder), "Hidden visual folder was not removed"

    # Verify interactions are cleaned up
    page_data = load_json(os.path.join(report_path, "definition/pages/Page1/page.json"))
    interactions = page_data["visualInteractions"]
    assert len(interactions) == 1
    assert interactions[0]["target"] == "v2"


def test_set_first_page_as_active_with_hidden_pages(tmp_path):
    """Test that the first non-hidden page is set as active."""
    report_path = str(tmp_path)

    # Create pages.json with three pages in order
    create_dummy_file(
        tmp_path,
        "definition/pages/pages.json",
        {
            "pageOrder": ["Page1", "Page2", "Page3"],
            "activePageName": "Page1",  # Initially set to first page
        },
    )

    # Page 1: Hidden (Tooltip page)
    create_dummy_file(
        tmp_path,
        "definition/pages/Page1/page.json",
        {
            "name": "Page1",
            "displayName": "Tooltip",
            "visibility": "HiddenInViewMode",
            "type": "Tooltip",
        },
    )

    # Page 2: Also hidden
    create_dummy_file(
        tmp_path,
        "definition/pages/Page2/page.json",
        {
            "name": "Page2",
            "displayName": "Another Hidden Page",
            "visibility": "HiddenInViewMode",
        },
    )

    # Page 3: Visible (this should become the active page)
    create_dummy_file(
        tmp_path,
        "definition/pages/Page3/page.json",
        {
            "name": "Page3",
            "displayName": "Main Page",
            "visibility": "Visible",
        },
    )

    # Run the function
    set_first_page_as_active(report_path)

    # Verify that Page3 is now the active page
    pages_data = load_json(os.path.join(report_path, "definition/pages/pages.json"))
    assert (
        pages_data["activePageName"] == "Page3"
    ), f"Expected 'Page3' to be active, but got '{pages_data['activePageName']}'"


def test_set_first_page_as_active_all_hidden(tmp_path):
    """Test that when all pages are hidden, the first page is still set as active."""
    report_path = str(tmp_path)

    # Create pages.json with two pages, both hidden
    create_dummy_file(
        tmp_path,
        "definition/pages/pages.json",
        {
            "pageOrder": ["Page1", "Page2"],
            "activePageName": "Page2",  # Currently set to second page
        },
    )

    # Page 1: Hidden
    create_dummy_file(
        tmp_path,
        "definition/pages/Page1/page.json",
        {
            "name": "Page1",
            "displayName": "Hidden Page 1",
            "visibility": "HiddenInViewMode",
        },
    )

    # Page 2: Also hidden
    create_dummy_file(
        tmp_path,
        "definition/pages/Page2/page.json",
        {
            "name": "Page2",
            "displayName": "Hidden Page 2",
            "visibility": "HiddenInViewMode",
        },
    )

    # Run the function
    with patch("builtins.print") as mock_print:
        set_first_page_as_active(report_path)
        # Check that a warning was printed
        assert any("Warning" in str(call) for call in mock_print.call_args_list)

    # Verify that Page1 is the active page (fallback to first page)
    pages_data = load_json(os.path.join(report_path, "definition/pages/pages.json"))
    assert (
        pages_data["activePageName"] == "Page1"
    ), f"Expected 'Page1' to be active (fallback), but got '{pages_data['activePageName']}'"


def test_set_first_page_as_active_renamed_folders(tmp_path):
    """Test that it works when folder names don't match page IDs."""
    report_path = str(tmp_path)

    create_dummy_file(
        tmp_path,
        "definition/pages/pages.json",
        {
            "pageOrder": ["Page1", "Page2"],
            "activePageName": "Page2",
        },
    )

    # Page 1: Visible, but folder is named "Folder_Page1"
    create_dummy_file(
        tmp_path,
        "definition/pages/Folder_Page1/page.json",
        {
            "name": "Page1",
            "displayName": "Page 1",
            "visibility": "Visible",
        },
    )

    # Page 2: Hidden
    create_dummy_file(
        tmp_path,
        "definition/pages/Page2/page.json",
        {
            "name": "Page2",
            "displayName": "Page 2",
            "visibility": "HiddenInViewMode",
        },
    )

    set_first_page_as_active(report_path)

    pages_data = load_json(os.path.join(report_path, "definition/pages/pages.json"))
    assert pages_data["activePageName"] == "Page1"


def test_remove_empty_pages_renamed_folders(tmp_path):
    """Test removing empty pages when folders are renamed."""
    report_path = str(tmp_path)
    create_dummy_file(
        tmp_path,
        "definition/pages/pages.json",
        {"pageOrder": ["Page1", "Page2"], "activePageName": "Page1"},
    )

    # Page 1: Valid, has visuals, folder renamed
    create_dummy_file(
        tmp_path, "definition/pages/Folder_Page1/page.json", {"name": "Page1"}
    )
    create_dummy_file(
        tmp_path, "definition/pages/Folder_Page1/visuals/v1/visual.json", {"name": "v1"}
    )

    # Page 2: Empty (no visuals), folder renamed
    create_dummy_file(
        tmp_path, "definition/pages/Folder_Page2/page.json", {"name": "Page2"}
    )
    os.makedirs(
        os.path.join(report_path, "definition/pages/Folder_Page2/visuals"),
        exist_ok=True,
    )

    # Rogue folder (no page.json)
    os.makedirs(
        os.path.join(report_path, "definition/pages/RogueFolder"), exist_ok=True
    )

    with patch("builtins.print") as _mock_print:
        remove_empty_pages(report_path)

        # Check pages.json
        pages_data = load_json(os.path.join(report_path, "definition/pages/pages.json"))
        assert pages_data["pageOrder"] == ["Page1"]

        # Check folders
        assert os.path.exists(
            os.path.join(report_path, "definition/pages/Folder_Page1")
        )
        assert not os.path.exists(
            os.path.join(report_path, "definition/pages/Folder_Page2")
        )
        assert not os.path.exists(
            os.path.join(report_path, "definition/pages/RogueFolder")
        )
