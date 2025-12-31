import pytest
import argparse
from pbir_utils.command_utils import (
    parse_filters,
    parse_json_arg,
    add_report_path_arg,
    add_dry_run_arg,
    add_summary_arg,
    add_common_args,
)


def test_parse_filters_none():
    assert parse_filters("") is None
    assert parse_filters(None) is None


def test_parse_filters_valid():
    valid_json = '{"Table1": ["Val1", "Val2"], "Table2": "Val3"}'
    result = parse_filters(valid_json)
    assert result["Table1"] == {"Val1", "Val2"}
    assert result["Table2"] == {"Val3"}


def test_parse_filters_invalid_json(capsys):
    with pytest.raises(SystemExit):
        parse_filters('{"invalid": json}')
    captured = capsys.readouterr()
    assert "Invalid JSON string" in captured.err


def test_parse_filters_not_dict(capsys):
    with pytest.raises(SystemExit):
        parse_filters('["list", "not", "dict"]')
    captured = capsys.readouterr()
    assert "Parsing filters: Filters must be a JSON object" in captured.err


def test_parse_json_arg_valid():
    assert parse_json_arg('{"key": "value"}', "arg") == {"key": "value"}
    assert parse_json_arg("[1, 2]", "arg") == [1, 2]


def test_parse_json_arg_none():
    assert parse_json_arg(None, "arg") is None
    assert parse_json_arg("", "arg") is None


def test_parse_json_arg_invalid(capsys):
    with pytest.raises(SystemExit):
        parse_json_arg("invalid output", "test_arg")
    captured = capsys.readouterr()
    assert "Invalid JSON string for test_arg" in captured.err


def test_add_report_path_arg():
    parser = argparse.ArgumentParser()
    add_report_path_arg(parser)
    args = parser.parse_args(["path/to/report"])
    assert args.report_path == "path/to/report"


def test_add_dry_run_arg():
    parser = argparse.ArgumentParser()
    add_dry_run_arg(parser)
    args = parser.parse_args(["--dry-run"])
    assert args.dry_run is True
    args = parser.parse_args([])
    assert args.dry_run is False


def test_add_summary_arg():
    parser = argparse.ArgumentParser()
    add_summary_arg(parser)
    args = parser.parse_args(["--summary"])
    assert args.summary is True
    args = parser.parse_args([])
    assert args.summary is False


def test_add_common_args():
    parser = argparse.ArgumentParser()
    add_common_args(parser, include_report_path=True, include_summary=True)
    args = parser.parse_args(["report_path", "--dry-run", "--summary"])
    assert args.report_path == "report_path"
    assert args.dry_run is True
    assert args.summary is True


def test_add_common_args_flags_only():
    parser = argparse.ArgumentParser()
    add_common_args(parser, include_report_path=False, include_summary=False)
    # Should only have dry-run
    args = parser.parse_args(["--dry-run"])
    assert args.dry_run is True
    with pytest.raises(SystemExit):
        parser.parse_args(["path"])  # positional arg shouldn't exist
    with pytest.raises(SystemExit):
        parser.parse_args(["--summary"])  # summary arg shouldn't exist
