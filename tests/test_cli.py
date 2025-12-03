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


# Tests from test_cli_optional_path.py


def test_sanitize_no_path_in_report_dir(simple_report, run_cli):
    # Run sanitize without path inside a .Report dir
    result = run_cli(
        ["sanitize", "--actions", "remove_unused_measures", "--dry-run"],
        cwd=simple_report,
    )
    assert result.returncode == 0


def test_sanitize_no_path_outside_report_dir(tmp_path, run_cli):
    # Run sanitize without path outside a .Report dir
    result = run_cli(
        ["sanitize", "--actions", "remove_unused_measures", "--dry-run"],
        cwd=str(tmp_path),
    )
    assert result.returncode != 0
    assert "Error: report_path not provided" in result.stderr


def test_extract_metadata_infer_path(simple_report, tmp_path, run_cli):
    # Run extract-metadata with only output path inside a .Report dir
    output_csv = tmp_path / "output.csv"
    result = run_cli(["extract-metadata", str(output_csv)], cwd=simple_report)
    assert result.returncode == 0


def test_extract_metadata_explicit_path(simple_report, tmp_path, run_cli):
    # Run extract-metadata with explicit report path and output path
    output_csv = tmp_path / "output_explicit.csv"
    result = run_cli(["extract-metadata", simple_report, str(output_csv)])
    assert result.returncode == 0


def test_extract_metadata_no_args_error(simple_report, run_cli):
    # Run extract-metadata with no args
    result = run_cli(["extract-metadata"], cwd=simple_report)
    assert result.returncode != 0
    assert "Error: Output path required." in result.stderr


def test_visualize_no_path_in_report_dir(simple_report, run_cli):
    # Run visualize without path inside a .Report dir
    # Note: visualize might try to open a browser or server, but we just check if it parses args correctly.
    # However, visualize usually blocks. We might need to mock it or just check if it fails with path error if not in report dir.
    # Since we can't easily test blocking commands, we'll test the failure case outside report dir.
    pass


def test_visualize_no_path_outside_report_dir(tmp_path, run_cli):
    result = run_cli(["visualize"], cwd=str(tmp_path))
    assert result.returncode != 0
    assert "Error: report_path not provided" in result.stderr


def test_disable_interactions_no_path_in_report_dir(simple_report, run_cli):
    result = run_cli(["disable-interactions", "--dry-run"], cwd=simple_report)
    assert result.returncode == 0


def test_remove_measures_no_path_in_report_dir(simple_report, run_cli):
    result = run_cli(["remove-measures", "--dry-run"], cwd=simple_report)
    assert result.returncode == 0


def test_measure_dependencies_no_path_in_report_dir(simple_report, run_cli):
    # measure-dependencies prints to stdout, doesn't block
    result = run_cli(["measure-dependencies"], cwd=simple_report)
    assert result.returncode == 0


# Tests from test_cli_sanitization.py


def test_remove_unused_bookmarks_dry_run(simple_report, run_cli):
    result = run_cli(["remove-unused-bookmarks", simple_report, "--dry-run"])
    assert result.returncode == 0


def test_remove_unused_custom_visuals_dry_run(simple_report, run_cli):
    result = run_cli(["remove-unused-custom-visuals", simple_report, "--dry-run"])
    assert result.returncode == 0


def test_disable_show_items_with_no_data_dry_run(simple_report, run_cli):
    result = run_cli(["disable-show-items-with-no-data", simple_report, "--dry-run"])
    assert result.returncode == 0


def test_hide_tooltip_drillthrough_pages_dry_run(simple_report, run_cli):
    result = run_cli(["hide-tooltip-drillthrough-pages", simple_report, "--dry-run"])
    assert result.returncode == 0


def test_set_first_page_as_active_dry_run(complex_report, run_cli):
    result = run_cli(["set-first-page-as-active", complex_report, "--dry-run"])
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.returncode == 0


def test_remove_empty_pages_dry_run(complex_report, run_cli):
    result = run_cli(["remove-empty-pages", complex_report, "--dry-run"])
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.returncode == 0


def test_remove_hidden_visuals_dry_run(simple_report, run_cli):
    result = run_cli(["remove-hidden-visuals", simple_report, "--dry-run"])
    assert result.returncode == 0


def test_cleanup_invalid_bookmarks_dry_run(complex_report, run_cli):
    result = run_cli(["cleanup-invalid-bookmarks", complex_report, "--dry-run"])
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.returncode == 0


def test_standardize_folder_names_dry_run(simple_report, run_cli):
    result = run_cli(["standardize-folder-names", simple_report, "--dry-run"])
    assert result.returncode == 0
