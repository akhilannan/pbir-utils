import unittest
import os
import sys
import json
import shutil
import tempfile
from unittest.mock import patch, MagicMock

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pbir_utils.json_utils import _load_json

class TestJsonUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_dummy_file(self, path, content):
        full_path = os.path.join(self.test_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            if isinstance(content, dict) or isinstance(content, list):
                json.dump(content, f)
            else:
                f.write(content)
        return full_path

    def test_load_json_errors(self):
        # Test malformed JSON
        json_path = self.create_dummy_file("bad.json", "{bad json")
        with patch('builtins.print') as mock_print:
            data = _load_json(json_path)
            self.assertEqual(data, {})
            mock_print.assert_called()
            self.assertTrue("Error: Unable to parse JSON" in mock_print.call_args[0][0])

        # Test non-existent file
        with patch('builtins.print') as mock_print:
            data = _load_json("non_existent.json")
            self.assertEqual(data, {})
            mock_print.assert_called()
            self.assertTrue("Error: Unable to read or write file" in mock_print.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
