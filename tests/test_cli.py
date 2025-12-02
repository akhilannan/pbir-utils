import os
import pytest


def test_sanitize_dry_run(simple_report, run_cli):
    result = run_cli(
        ["sanitize", simple_report, "--actions", "remove_unused_measures", "--dry-run"]
    )
    assert result.returncode == 0


def test_extract_metadata(simple_report, tmp_path, run_cli):
    output_csv = tmp_path / "output.csv"
    result = run_cli(["extract-metadata", simple_report, str(output_csv)])
    assert result.returncode == 0


def test_visualize_help(run_cli):
    result = run_cli(["visualize", "--help"])
    assert result.returncode == 0


def test_batch_update_dry_run(simple_report, tmp_path, run_cli):
    csv_path = tmp_path / "mapping.csv"
    with open(csv_path, "w") as f:
        f.write("old_tbl,old_col,new_tbl,new_col\nTable1,Col1,Table1,ColNew")

    result = run_cli(["batch-update", simple_report, str(csv_path), "--dry-run"])
    assert result.returncode == 0


def test_disable_interactions_dry_run(simple_report, run_cli):
    result = run_cli(["disable-interactions", simple_report, "--dry-run"])
    assert result.returncode == 0


def test_remove_measures_dry_run(simple_report, run_cli):
    result = run_cli(["remove-measures", simple_report, "--dry-run"])
    assert result.returncode == 0


def test_measure_dependencies(simple_report, run_cli):
    result = run_cli(["measure-dependencies", simple_report])
    assert result.returncode == 0


def test_update_filters_dry_run(simple_report, run_cli):
    filters = '[{"Table": "Tbl", "Column": "Col", "Condition": "In", "Values": ["A"]}]'
    result = run_cli(["update-filters", simple_report, filters, "--dry-run"])
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.returncode == 0


def test_sort_filters_dry_run(simple_report, run_cli):
    result = run_cli(["sort-filters", simple_report, "--dry-run"])
    assert result.returncode == 0
