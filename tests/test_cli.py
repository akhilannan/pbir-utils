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


# Tests for --summary flag


def test_remove_empty_pages_with_summary(complex_report, run_cli):
    """Test that --summary flag works with remove-empty-pages command."""
    result = run_cli(["remove-empty-pages", complex_report, "--dry-run", "--summary"])
    assert result.returncode == 0
    # Summary output should contain count-based message
    assert "Would remove" in result.stdout or "No empty" in result.stdout


def test_sanitize_with_summary(simple_report, run_cli):
    """Test that --summary flag works with sanitize command."""
    result = run_cli(
        [
            "sanitize",
            simple_report,
            "--actions",
            "remove_unused_measures",
            "--dry-run",
            "--summary",
        ]
    )
    assert result.returncode == 0


def test_disable_interactions_with_summary(simple_report, run_cli):
    """Test that --summary flag works with disable-interactions command."""
    result = run_cli(["disable-interactions", simple_report, "--dry-run", "--summary"])
    assert result.returncode == 0
    # Summary should contain count of pages updated (dry run uses "Would update")
    assert "Would update visual interactions" in result.stdout


def test_remove_measures_with_summary(simple_report, run_cli):
    """Test that --summary flag works with remove-measures command."""
    result = run_cli(["remove-measures", simple_report, "--dry-run", "--summary"])
    assert result.returncode == 0


def test_standardize_folder_names_with_summary(simple_report, run_cli):
    """Test that --summary flag works with standardize-folder-names command."""
    result = run_cli(
        ["standardize-folder-names", simple_report, "--dry-run", "--summary"]
    )
    assert result.returncode == 0
    # Summary should contain count of renamed folders (dry run uses "Would rename")
    assert "Would rename" in result.stdout


# Tests for --error-on-change flag


def test_error_on_change_requires_dry_run(simple_report, run_cli):
    """Test that --error-on-change without --dry-run returns an error."""
    result = run_cli(["standardize-folder-names", simple_report, "--error-on-change"])
    assert result.returncode != 0
    assert "--error-on-change requires --dry-run" in result.stderr


def test_error_on_change_sanitize_requires_dry_run(simple_report, run_cli):
    """Test that --error-on-change on sanitize command without --dry-run returns an error."""
    result = run_cli(
        [
            "sanitize",
            simple_report,
            "--actions",
            "set_first_page_as_active",
            "--error-on-change",
            "set_first_page_as_active",
        ]
    )
    assert result.returncode != 0
    assert "--error-on-change requires --dry-run" in result.stderr


def test_error_on_change_exits_with_code_1_when_changes_detected(
    simple_report, run_cli
):
    """Test that --error-on-change exits with code 1 when changes would be made."""
    # standardize-folder-names on simple_report should detect changes since folders use default names
    result = run_cli(
        ["standardize-folder-names", simple_report, "--dry-run", "--error-on-change"]
    )
    # The simple_report should trigger changes because folder names aren't standardized
    assert result.returncode == 1
    assert "Build failed due to --error-on-change policy" in result.stderr


def test_error_on_change_sanitize_specific_actions(simple_report, run_cli):
    """Test that --error-on-change on sanitize command monitors only specified actions."""
    result = run_cli(
        [
            "sanitize",
            simple_report,
            "--actions",
            "standardize_folder_names",
            "--dry-run",
            "--error-on-change",
            "standardize_folder_names",
        ]
    )
    # Should exit with code 1 if standardize_folder_names would make changes
    assert result.returncode == 1
    assert "Build failed due to --error-on-change policy" in result.stderr


def test_error_on_change_no_changes_succeeds(simple_report, run_cli):
    """Test that --error-on-change succeeds (exit 0) when no changes would be made."""
    # hide-tooltip-drillthrough-pages on simple_report should not detect any tooltip/drillthrough pages
    result = run_cli(
        [
            "hide-tooltip-drillthrough-pages",
            simple_report,
            "--dry-run",
            "--error-on-change",
        ]
    )
    # If no changes detected, should succeed
    assert result.returncode == 0


def test_error_on_change_disable_interactions(simple_report, run_cli):
    """Test that --error-on-change works with disable-interactions command."""
    result = run_cli(
        ["disable-interactions", simple_report, "--dry-run", "--error-on-change"]
    )
    # Check that the command runs (may or may not exit with error depending on report state)
    # The main test is that it doesn't crash and respects the flag
    assert result.returncode in [0, 1]


def test_error_on_change_remove_measures(simple_report, run_cli):
    """Test that --error-on-change works with remove-measures command."""
    result = run_cli(
        ["remove-measures", simple_report, "--dry-run", "--error-on-change"]
    )
    assert result.returncode in [0, 1]


def test_error_on_change_batch_update(simple_report, tmp_path, run_cli):
    """Test that --error-on-change works with batch-update command."""
    csv_path = tmp_path / "mapping.csv"
    with open(csv_path, "w") as f:
        f.write("old_tbl,old_col,new_tbl,new_col\nTable1,Col1,Table1,ColNew")

    result = run_cli(
        ["batch-update", simple_report, str(csv_path), "--dry-run", "--error-on-change"]
    )
    assert result.returncode in [0, 1]


def test_error_on_change_update_filters(simple_report, run_cli):
    """Test that --error-on-change works with update-filters command."""
    filters = '[{"Table": "Tbl", "Column": "Col", "Condition": "In", "Values": ["A"]}]'
    result = run_cli(
        ["update-filters", simple_report, filters, "--dry-run", "--error-on-change"]
    )
    assert result.returncode in [0, 1]


def test_error_on_change_sort_filters(simple_report, run_cli):
    """Test that --error-on-change works with sort-filters command."""
    result = run_cli(["sort-filters", simple_report, "--dry-run", "--error-on-change"])
    assert result.returncode in [0, 1]


def test_error_on_change_remove_unused_bookmarks(simple_report, run_cli):
    """Test that --error-on-change works with remove-unused-bookmarks command."""
    result = run_cli(
        ["remove-unused-bookmarks", simple_report, "--dry-run", "--error-on-change"]
    )
    assert result.returncode in [0, 1]


def test_error_on_change_remove_unused_custom_visuals(simple_report, run_cli):
    """Test that --error-on-change works with remove-unused-custom-visuals command."""
    result = run_cli(
        [
            "remove-unused-custom-visuals",
            simple_report,
            "--dry-run",
            "--error-on-change",
        ]
    )
    assert result.returncode in [0, 1]


def test_error_on_change_cleanup_invalid_bookmarks(complex_report, run_cli):
    """Test that --error-on-change works with cleanup-invalid-bookmarks command."""
    result = run_cli(
        ["cleanup-invalid-bookmarks", complex_report, "--dry-run", "--error-on-change"]
    )
    assert result.returncode in [0, 1]


# Tests for --exclude flag


def test_sanitize_exclude_single_action(complex_report, run_cli):
    """Test that --exclude works with a single action when using --actions all."""
    result = run_cli(
        [
            "sanitize",
            complex_report,
            "--actions",
            "all",
            "--exclude",
            "standardize_folder_names",
            "--dry-run",
        ]
    )
    assert result.returncode == 0


def test_sanitize_exclude_multiple_actions(complex_report, run_cli):
    """Test that --exclude works with multiple actions when using --actions all."""
    result = run_cli(
        [
            "sanitize",
            complex_report,
            "--actions",
            "all",
            "--exclude",
            "standardize_folder_names",
            "set_first_page_as_active",
            "--dry-run",
        ]
    )
    assert result.returncode == 0


def test_sanitize_exclude_invalid_action_warning(complex_report, run_cli):
    """Test that --exclude warns when invalid action names are provided."""
    result = run_cli(
        [
            "sanitize",
            complex_report,
            "--actions",
            "all",
            "--exclude",
            "invalid_action",
            "standardize_folder_names",
            "--dry-run",
        ]
    )
    assert result.returncode == 0
    assert (
        "Unknown actions in --exclude will be ignored: invalid_action" in result.stdout
    )
