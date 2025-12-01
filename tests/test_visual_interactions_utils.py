import unittest
import os
import sys
import json
from unittest.mock import patch, mock_open, MagicMock

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pbir_utils.visual_interactions_utils import (
    _get_visuals,
    _update_interactions,
    _filter_ids_by_type,
    _process_page,
    disable_visual_interactions
)

class TestVisualInteractionsUtils(unittest.TestCase):

    @patch('os.listdir')
    @patch('os.path.isfile')
    @patch('pbir_utils.visual_interactions_utils._load_json')
    def test_get_visuals(self, mock_load_json, mock_isfile, mock_listdir):
        mock_listdir.return_value = ['visual1', 'visual2']
        mock_isfile.return_value = True
        mock_load_json.side_effect = [
            {"name": "v1", "visual": {"visualType": "barChart"}},
            {"name": "v2", "visualGroup": "group"} # Should be skipped
        ]

        visual_ids, visual_types = _get_visuals("dummy_path")

        self.assertEqual(visual_ids, ["v1"])
        self.assertEqual(visual_types, {"v1": "barChart"})

    def test_update_interactions_overwrite(self):
        existing = []
        source_ids = ["s1"]
        target_ids = ["t1"]
        
        result = _update_interactions(existing, source_ids, target_ids, update_type="Overwrite")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {"source": "s1", "target": "t1", "type": "NoFilter"})

    def test_update_interactions_upsert(self):
        existing = [{"source": "s1", "target": "t1", "type": "Filter"}]
        source_ids = ["s1"]
        target_ids = ["t1", "t2"]
        
        result = _update_interactions(existing, source_ids, target_ids, update_type="Upsert")
        
        self.assertEqual(len(result), 2)
        # s1->t1 should be updated to NoFilter (default interaction_type)
        self.assertTrue(any(i["source"] == "s1" and i["target"] == "t1" and i["type"] == "NoFilter" for i in result))
        # s1->t2 should be added
        self.assertTrue(any(i["source"] == "s1" and i["target"] == "t2" and i["type"] == "NoFilter" for i in result))

    def test_update_interactions_insert(self):
        existing = [{"source": "s1", "target": "t1", "type": "Filter"}]
        source_ids = ["s1"]
        target_ids = ["t1", "t2"]
        
        result = _update_interactions(existing, source_ids, target_ids, update_type="Insert")
        
        self.assertEqual(len(result), 2)
        # s1->t1 should NOT be updated
        self.assertTrue(any(i["source"] == "s1" and i["target"] == "t1" and i["type"] == "Filter" for i in result))
        # s1->t2 should be added
        self.assertTrue(any(i["source"] == "s1" and i["target"] == "t2" and i["type"] == "NoFilter" for i in result))

    def test_filter_ids_by_type(self):
        ids = {"v1", "v2"}
        visual_types = {"v1": "barChart", "v2": "pieChart"}
        
        # No types specified
        self.assertEqual(_filter_ids_by_type(ids, None, visual_types), {"v1", "v2"})
        
        # Filter by type
        self.assertEqual(_filter_ids_by_type(ids, ["barChart"], visual_types), {"v1"})

    @patch('pbir_utils.visual_interactions_utils._load_json')
    @patch('pbir_utils.visual_interactions_utils._get_visuals')
    @patch('pbir_utils.visual_interactions_utils._write_json')
    def test_process_page(self, mock_write_json, mock_get_visuals, mock_load_json):
        mock_load_json.return_value = {"visualInteractions": []}
        mock_get_visuals.return_value = (["v1", "v2"], {"v1": "barChart", "v2": "pieChart"})
        
        _process_page(
            "page.json", "visuals_folder",
            source_ids=None, source_types=["barChart"],
            target_ids=None, target_types=None,
            update_type="Upsert", interaction_type="NoFilter"
        )
        
        mock_write_json.assert_called_once()
        args, _ = mock_write_json.call_args
        mock_write_json.assert_called_once()
        args, _ = mock_write_json.call_args
        self.assertEqual(len(args[1]["visualInteractions"]), 1) # v1->v2. v1->v1 is skipped.
        # Logic check: _update_interactions: if source_id != target_id
        # source_ids (filtered by type barChart) -> v1
        # target_ids (all) -> v1, v2
        # v1->v1 skipped. v1->v2 added.
        # So len should be 1.
        
        # Let's verify the logic in _update_interactions again.
        # loops source_ids, then target_ids. if source != target.
        
        # Wait, I asserted 2 in the comment but logic says 1. Let's check the assertion in run.
        # Actually, let's just assert called for now and trust unit tests for update logic.

    @patch('os.walk')
    @patch('pbir_utils.visual_interactions_utils._load_json')
    @patch('pbir_utils.visual_interactions_utils._process_page')
    @patch('os.path.isdir')
    def test_disable_visual_interactions(self, mock_isdir, mock_process_page, mock_load_json, mock_walk):
        mock_walk.return_value = [("root", [], ["page.json"])]
        mock_load_json.return_value = {"displayName": "Page 1"}
        mock_isdir.return_value = True
        
        disable_visual_interactions("report_path", pages=["Page 1"])
        
        mock_process_page.assert_called_once()

    def test_disable_visual_interactions_invalid_args(self):
        with self.assertRaises(ValueError):
            disable_visual_interactions("report_path", pages="NotAList")

if __name__ == '__main__':
    unittest.main()
