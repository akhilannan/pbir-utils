import os
import json
import pytest

from pbir_utils.visual_utils import remove_hidden_visuals_never_shown


@pytest.fixture
def temp_report_with_hidden_slicer(tmp_path):
    report_path = tmp_path / "HiddenSlicer.Report"
    report_path.mkdir()

    definition_dir = report_path / "definition"
    definition_dir.mkdir()

    pages_dir = definition_dir / "pages"
    pages_dir.mkdir()

    bookmarks_dir = definition_dir / "bookmarks"
    bookmarks_dir.mkdir()

    # Create a page with a hidden slicer and a hidden generic visual
    page_dir = pages_dir / "Page1"
    page_dir.mkdir()
    visuals_dir = page_dir / "visuals"
    visuals_dir.mkdir()

    # Hidden Slicer with Default Selection (Should be kept)
    slicer_with_default = {
        "name": "HiddenSlicerWithDefault",
        "isHidden": True,
        "visual": {
            "visualType": "slicer",
            "name": "HiddenSlicerWithDefault",
            "objects": {"general": [{"properties": {"filter": {"some": "filter"}}}]},
        },
    }

    # Hidden Slicer with Bookmark Filter (Should be kept)
    slicer_with_bookmark = {
        "name": "HiddenSlicerWithBookmark",
        "isHidden": True,
        "visual": {"visualType": "slicer", "name": "HiddenSlicerWithBookmark"},
    }

    # Hidden Slicer with NO Selection (Should be removed)
    slicer_no_selection = {
        "name": "HiddenSlicerNoSelection",
        "isHidden": True,
        "visual": {"visualType": "slicer", "name": "HiddenSlicerNoSelection"},
    }

    # Create directories and files
    for visual_data in [slicer_with_default, slicer_with_bookmark, slicer_no_selection]:
        v_dir = visuals_dir / visual_data["name"]
        v_dir.mkdir()
        with open(v_dir / "visual.json", "w") as f:
            json.dump(visual_data, f)

    # Create page.json
    page_json = {"name": "Page1", "displayName": "Page 1", "visualInteractions": []}
    with open(page_dir / "page.json", "w") as f:
        json.dump(page_json, f)

    # Create Bookmark with filter for HiddenSlicerWithBookmark
    bookmark_data = {
        "name": "Bookmark1",
        "displayName": "Bookmark 1",
        "explorationState": {
            "sections": {
                "Page1": {
                    "visualContainers": {
                        "HiddenSlicerWithBookmark": {"filters": [{"some": "filter"}]}
                    }
                }
            }
        },
    }
    with open(bookmarks_dir / "Bookmark1.bookmark.json", "w") as f:
        json.dump(bookmark_data, f)

    return str(report_path)


def test_remove_hidden_visuals_preserves_slicers(temp_report_with_hidden_slicer):
    report_path = temp_report_with_hidden_slicer

    # Run the sanitizer
    remove_hidden_visuals_never_shown(report_path)

    # Check results
    page_visuals_dir = os.path.join(
        report_path, "definition", "pages", "Page1", "visuals"
    )

    # Slicer with default should exist
    assert os.path.exists(
        os.path.join(page_visuals_dir, "HiddenSlicerWithDefault", "visual.json")
    ), "Hidden slicer with default selection should be preserved"

    # Slicer with bookmark should exist
    assert os.path.exists(
        os.path.join(page_visuals_dir, "HiddenSlicerWithBookmark", "visual.json")
    ), "Hidden slicer with bookmark filter should be preserved"

    # Slicer with NO selection should be removed
    assert not os.path.exists(
        os.path.join(page_visuals_dir, "HiddenSlicerNoSelection", "visual.json")
    ), "Hidden slicer with NO selection should be removed"
