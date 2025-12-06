"""Tests for bookmark_utils module."""

import os
from unittest.mock import patch


from conftest import create_dummy_file
from pbir_utils.bookmark_utils import remove_unused_bookmarks, cleanup_invalid_bookmarks
from pbir_utils.common import load_json


def test_remove_unused_bookmarks_no_file(tmp_path):
    """Test when bookmarks.json doesn't exist."""
    report_path = str(tmp_path)
    with patch("builtins.print") as mock_print:
        remove_unused_bookmarks(report_path)
        mock_print.assert_called()
        assert any(
            "No bookmarks found" in str(call) for call in mock_print.call_args_list
        )


def test_remove_unused_bookmarks_empty(tmp_path):
    """Test when bookmarks exist but none are used."""
    report_path = str(tmp_path)

    # Create bookmarks.json with some bookmarks
    create_dummy_file(
        tmp_path,
        "definition/bookmarks/bookmarks.json",
        {"items": [{"name": "bookmark1"}, {"name": "bookmark2"}]},
    )

    # Create bookmark files
    create_dummy_file(
        tmp_path,
        "definition/bookmarks/bookmark1.bookmark.json",
        {"name": "bookmark1"},
    )
    create_dummy_file(
        tmp_path,
        "definition/bookmarks/bookmark2.bookmark.json",
        {"name": "bookmark2"},
    )

    # Create a page with no bookmark references
    create_dummy_file(
        tmp_path,
        "definition/pages/Page1/visuals/v1/visual.json",
        {"name": "v1", "visual": {"visualType": "barChart"}},
    )

    result = remove_unused_bookmarks(report_path)

    # All bookmarks should be removed since none are used
    assert result is True


def test_cleanup_invalid_bookmarks(tmp_path):
    """Test cleanup of bookmarks referencing non-existent pages/visuals."""
    report_path = str(tmp_path)

    # Valid page
    create_dummy_file(tmp_path, "definition/pages/pages.json", {"pageOrder": ["Page1"]})
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


def test_cleanup_invalid_bookmarks_no_directory(tmp_path):
    """Test when bookmarks directory doesn't exist."""
    report_path = str(tmp_path)

    with patch("builtins.print") as mock_print:
        result = cleanup_invalid_bookmarks(report_path)
        assert result is False
        assert any(
            "No bookmarks directory" in str(call) for call in mock_print.call_args_list
        )
