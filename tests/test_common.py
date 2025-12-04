import os
import sys
import json
from unittest.mock import patch
import pytest

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from pbir_utils.common import load_json


def create_dummy_file(test_dir, path, content):
    full_path = test_dir / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        if isinstance(content, dict) or isinstance(content, list):
            json.dump(content, f)
        else:
            f.write(content)
    return str(full_path)


def test_load_json_errors(tmp_path):
    # Test malformed JSON
    json_path = create_dummy_file(tmp_path, "bad.json", "{bad json")
    with patch("builtins.print") as mock_print:
        data = load_json(json_path)
        assert data == {}
        mock_print.assert_called()
        assert "Error: Unable to parse JSON" in mock_print.call_args[0][0]

    # Test non-existent file
    with patch("builtins.print") as mock_print:
        data = load_json("non_existent.json")
        assert data == {}
        mock_print.assert_called()
        assert "Error: Unable to read or write file" in mock_print.call_args[0][0]


def test_get_report_paths(tmp_path):
    from pbir_utils.common import get_report_paths

    # Create dummy report structure
    report1_dir = tmp_path / "Report1.Report" / "definition"
    report1_dir.mkdir(parents=True)
    (report1_dir / "report.json").touch()

    report2_dir = tmp_path / "Report2.Report" / "definition"
    report2_dir.mkdir(parents=True)
    (report2_dir / "report.json").touch()

    # Test finding all reports in root
    paths = get_report_paths(str(tmp_path))
    assert len(paths) == 2
    assert any("Report1.Report" in p for p in paths)
    assert any("Report2.Report" in p for p in paths)

    # Test finding specific report by folder path (The Fix)
    report1_path = tmp_path / "Report1.Report"
    paths = get_report_paths(str(report1_path))
    assert len(paths) == 1
    assert "Report1.Report" in paths[0]
    assert paths[0].endswith("report.json")
