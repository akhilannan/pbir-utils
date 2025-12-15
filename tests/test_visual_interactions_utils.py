from unittest.mock import patch
import pytest

from pbir_utils.visual_interactions_utils import (
    _get_visuals,
    _update_interactions,
    _filter_ids_by_type,
    _process_page,
    disable_visual_interactions,
)


@patch("os.listdir")
@patch("os.path.isfile")
@patch("pbir_utils.visual_interactions_utils.load_json")
def test_get_visuals(mock_load_json, mock_isfile, mock_listdir):
    mock_listdir.return_value = ["visual1", "visual2"]
    mock_isfile.return_value = True
    mock_load_json.side_effect = [
        {"name": "v1", "visual": {"visualType": "barChart"}},
        {"name": "v2", "visualGroup": "group"},  # Should be skipped
    ]

    visual_ids, visual_types = _get_visuals("dummy_path")

    assert visual_ids == ["v1"]
    assert visual_types == {"v1": "barChart"}


def test_update_interactions_overwrite():
    existing = []
    source_ids = ["s1"]
    target_ids = ["t1"]

    result = _update_interactions(
        existing, source_ids, target_ids, update_type="Overwrite"
    )

    assert len(result) == 1
    assert result[0] == {"source": "s1", "target": "t1", "type": "NoFilter"}


def test_update_interactions_upsert():
    existing = [{"source": "s1", "target": "t1", "type": "Filter"}]
    source_ids = ["s1"]
    target_ids = ["t1", "t2"]

    result = _update_interactions(
        existing, source_ids, target_ids, update_type="Upsert"
    )

    assert len(result) == 2
    # s1->t1 should be updated to NoFilter (default interaction_type)
    assert any(
        i["source"] == "s1" and i["target"] == "t1" and i["type"] == "NoFilter"
        for i in result
    )
    # s1->t2 should be added
    assert any(
        i["source"] == "s1" and i["target"] == "t2" and i["type"] == "NoFilter"
        for i in result
    )


def test_update_interactions_insert():
    existing = [{"source": "s1", "target": "t1", "type": "Filter"}]
    source_ids = ["s1"]
    target_ids = ["t1", "t2"]

    result = _update_interactions(
        existing, source_ids, target_ids, update_type="Insert"
    )

    assert len(result) == 2
    # s1->t1 should NOT be updated
    assert any(
        i["source"] == "s1" and i["target"] == "t1" and i["type"] == "Filter"
        for i in result
    )
    # s1->t2 should be added
    assert any(
        i["source"] == "s1" and i["target"] == "t2" and i["type"] == "NoFilter"
        for i in result
    )


def test_filter_ids_by_type():
    ids = {"v1", "v2"}
    visual_types = {"v1": "barChart", "v2": "pieChart"}

    # No types specified
    assert _filter_ids_by_type(ids, None, visual_types) == {"v1", "v2"}

    # Filter by type
    assert _filter_ids_by_type(ids, ["barChart"], visual_types) == {"v1"}


@patch("pbir_utils.visual_interactions_utils.load_json")
@patch("pbir_utils.visual_interactions_utils._get_visuals")
@patch("pbir_utils.visual_interactions_utils.write_json")
def test_process_page(mock_write_json, mock_get_visuals, mock_load_json):
    mock_load_json.return_value = {"visualInteractions": []}
    mock_get_visuals.return_value = (
        ["v1", "v2"],
        {"v1": "barChart", "v2": "pieChart"},
    )

    _process_page(
        "page.json",
        "visuals_folder",
        source_ids=None,
        source_types=["barChart"],
        target_ids=None,
        target_types=None,
        update_type="Upsert",
        interaction_type="NoFilter",
    )

    mock_write_json.assert_called_once()
    args, _ = mock_write_json.call_args
    assert len(args[1]["visualInteractions"]) == 1
    # v1->v2. v1->v1 is skipped.


@patch("pbir_utils.visual_interactions_utils.iter_pages")
@patch("pbir_utils.visual_interactions_utils._process_page")
@patch("os.path.isdir")
def test_disable_visual_interactions(mock_isdir, mock_process_page, mock_iter_pages):
    # iter_pages yields (page_id, page_folder_path, page_data)
    mock_iter_pages.return_value = iter([("page1", "root", {"displayName": "Page 1"})])
    mock_isdir.return_value = True

    disable_visual_interactions("report_path", pages=["Page 1"])

    mock_process_page.assert_called_once()


def test_disable_visual_interactions_invalid_args():
    with pytest.raises(ValueError):
        disable_visual_interactions("report_path", pages="NotAList")
