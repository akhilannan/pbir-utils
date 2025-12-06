"""Tests for visual_utils module."""

import os
from unittest.mock import patch


from conftest import create_dummy_file
from pbir_utils.visual_utils import (
    remove_unused_custom_visuals,
    disable_show_items_with_no_data,
    remove_hidden_visuals_never_shown,
)
from pbir_utils.common import load_json


class TestRemoveUnusedCustomVisuals:
    """Tests for remove_unused_custom_visuals."""

    def test_no_custom_visuals(self, tmp_path):
        """Test when no custom visuals exist."""
        report_path = str(tmp_path)
        create_dummy_file(
            tmp_path, "definition/report.json", {"publicCustomVisuals": []}
        )
        with patch("builtins.print") as mock_print:
            result = remove_unused_custom_visuals(report_path)
            assert result is False
            assert any(
                "No custom visuals found" in str(call)
                for call in mock_print.call_args_list
            )

    def test_removes_unused(self, tmp_path):
        """Test that unused custom visuals are removed."""
        report_path = str(tmp_path)
        create_dummy_file(
            tmp_path,
            "definition/report.json",
            {"publicCustomVisuals": ["usedVisual", "unusedVisual"]},
        )
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/visuals/v1/visual.json",
            {"name": "v1", "visual": {"visualType": "usedVisual"}},
        )

        result = remove_unused_custom_visuals(report_path)

        assert result is True
        report_data = load_json(os.path.join(report_path, "definition/report.json"))
        assert report_data["publicCustomVisuals"] == ["usedVisual"]


class TestDisableShowItemsWithNoData:
    """Tests for disable_show_items_with_no_data."""

    def test_nested_structure(self, tmp_path):
        """Test nested structure with showAll property."""
        report_path = str(tmp_path)
        visual_json = {
            "visual": {"objects": {"some_obj": [{"properties": {"showAll": True}}]}}
        }
        create_dummy_file(
            tmp_path, "definition/pages/Page1/visuals/visual.json", visual_json
        )

        result = disable_show_items_with_no_data(report_path)

        assert result is True
        updated_data = load_json(
            os.path.join(report_path, "definition/pages/Page1/visuals/visual.json")
        )
        assert (
            "showAll"
            not in updated_data["visual"]["objects"]["some_obj"][0]["properties"]
        )

    def test_no_showAll_property(self, tmp_path):
        """Test when no showAll properties exist."""
        report_path = str(tmp_path)
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/visuals/visual.json",
            {"visual": {"objects": {"some_obj": [{"properties": {}}]}}},
        )

        with patch("builtins.print") as mock_print:
            result = disable_show_items_with_no_data(report_path)
            assert result is False
            assert any(
                "No visuals found" in str(call) for call in mock_print.call_args_list
            )


class TestRemoveHiddenVisualsNeverShown:
    """Tests for remove_hidden_visuals_never_shown."""

    def test_cleanup_hidden_visuals(self, tmp_path):
        """Test that hidden visuals not shown by bookmarks are removed."""
        report_path = str(tmp_path)

        # Create a page with interactions
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {
                "name": "Page1",
                "visualInteractions": [
                    {"source": "v1", "target": "hidden_v"},
                    {"source": "v1", "target": "v2"},
                ],
            },
        )

        # Create visible visuals
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/visuals/v1/visual.json",
            {"name": "v1"},
        )
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/visuals/v2/visual.json",
            {"name": "v2"},
        )

        # Create hidden visual
        hidden_v_path = create_dummy_file(
            tmp_path,
            "definition/pages/Page1/visuals/hidden_v/visual.json",
            {"name": "hidden_v", "isHidden": True},
        )
        hidden_v_folder = os.path.dirname(hidden_v_path)

        # Create empty bookmarks
        create_dummy_file(
            tmp_path, "definition/bookmarks/bookmarks.json", {"items": []}
        )

        remove_hidden_visuals_never_shown(report_path)

        # Hidden visual folder should be removed
        assert not os.path.exists(hidden_v_folder)

        # Interactions should be cleaned
        page_data = load_json(
            os.path.join(report_path, "definition/pages/Page1/page.json")
        )
        interactions = page_data["visualInteractions"]
        assert len(interactions) == 1
        assert interactions[0]["target"] == "v2"

    def test_preserves_shown_by_bookmark(self, tmp_path):
        """Test that hidden visuals shown by bookmarks are preserved."""
        report_path = str(tmp_path)

        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {"name": "Page1", "visualInteractions": []},
        )

        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/visuals/hidden_v/visual.json",
            {"name": "hidden_v", "isHidden": True},
        )

        # Bookmark that shows the hidden visual
        create_dummy_file(
            tmp_path,
            "definition/bookmarks/b1.bookmark.json",
            {
                "name": "b1",
                "explorationState": {
                    "sections": {
                        "Page1": {
                            "visualContainers": {
                                "hidden_v": {
                                    "singleVisual": {"display": {"mode": "visible"}}
                                }
                            }
                        }
                    }
                },
            },
        )
        create_dummy_file(
            tmp_path,
            "definition/bookmarks/bookmarks.json",
            {"items": [{"name": "b1"}]},
        )

        remove_hidden_visuals_never_shown(report_path)

        # Hidden visual should be preserved since it's shown by bookmark
        assert os.path.exists(
            os.path.join(report_path, "definition/pages/Page1/visuals/hidden_v")
        )
