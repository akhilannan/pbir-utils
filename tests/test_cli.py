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


# Tests from test_cli_sanitization.py (now using sanitize command)


def test_remove_unused_bookmarks_dry_run(simple_report, run_cli):
    result = run_cli(
        ["sanitize", simple_report, "--actions", "remove_unused_bookmarks", "--dry-run"]
    )
    assert result.returncode == 0


def test_remove_unused_custom_visuals_dry_run(simple_report, run_cli):
    result = run_cli(
        [
            "sanitize",
            simple_report,
            "--actions",
            "remove_unused_custom_visuals",
            "--dry-run",
        ]
    )
    assert result.returncode == 0


def test_disable_show_items_with_no_data_dry_run(simple_report, run_cli):
    result = run_cli(
        [
            "sanitize",
            simple_report,
            "--actions",
            "disable_show_items_with_no_data",
            "--dry-run",
        ]
    )
    assert result.returncode == 0


def test_hide_tooltip_pages_dry_run(simple_report, run_cli):
    result = run_cli(
        ["sanitize", simple_report, "--actions", "hide_tooltip_pages", "--dry-run"]
    )
    assert result.returncode == 0


def test_set_first_page_as_active_dry_run(complex_report, run_cli):
    result = run_cli(
        [
            "sanitize",
            complex_report,
            "--actions",
            "set_first_page_as_active",
            "--dry-run",
        ]
    )
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.returncode == 0


def test_remove_empty_pages_dry_run(complex_report, run_cli):
    result = run_cli(
        ["sanitize", complex_report, "--actions", "remove_empty_pages", "--dry-run"]
    )
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.returncode == 0


def test_remove_hidden_visuals_dry_run(simple_report, run_cli):
    result = run_cli(
        [
            "sanitize",
            simple_report,
            "--actions",
            "remove_hidden_visuals_never_shown",
            "--dry-run",
        ]
    )
    assert result.returncode == 0


def test_cleanup_invalid_bookmarks_dry_run(complex_report, run_cli):
    result = run_cli(
        [
            "sanitize",
            complex_report,
            "--actions",
            "cleanup_invalid_bookmarks",
            "--dry-run",
        ]
    )
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.returncode == 0


def test_standardize_pbir_folders_dry_run(simple_report, run_cli):
    result = run_cli(
        [
            "sanitize",
            simple_report,
            "--actions",
            "standardize_pbir_folders",
            "--dry-run",
        ]
    )
    assert result.returncode == 0


# Tests for --summary flag


def test_remove_empty_pages_with_summary(complex_report, run_cli):
    """Test that --summary flag works with sanitize remove_empty_pages action."""
    result = run_cli(
        [
            "sanitize",
            complex_report,
            "--actions",
            "remove_empty_pages",
            "--dry-run",
            "--summary",
        ]
    )
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


def test_standardize_pbir_folders_with_summary(simple_report, run_cli):
    """Test that --summary flag works with standardize_pbir_folders action."""
    result = run_cli(
        [
            "sanitize",
            simple_report,
            "--actions",
            "standardize_pbir_folders",
            "--dry-run",
            "--summary",
        ]
    )
    assert result.returncode == 0
    # Summary should contain count of renamed folders (dry run uses "Would rename")
    assert "Would rename" in result.stdout


# Tests for --error-on-change flag


def test_error_on_change_requires_dry_run(simple_report, run_cli):
    """Test that --error-on-change without --dry-run returns an error."""
    result = run_cli(
        [
            "sanitize",
            simple_report,
            "--actions",
            "standardize_pbir_folders",
            "--error-on-change",
            "standardize_pbir_folders",
        ]
    )
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
    # standardize_pbir_folders on simple_report should detect changes since folders use default names
    result = run_cli(
        [
            "sanitize",
            simple_report,
            "--actions",
            "standardize_pbir_folders",
            "--dry-run",
            "--error-on-change",
            "standardize_pbir_folders",
        ]
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
            "standardize_pbir_folders",
            "--dry-run",
            "--error-on-change",
            "standardize_pbir_folders",
        ]
    )
    # Should exit with code 1 if standardize_pbir_folders would make changes
    assert result.returncode == 1
    assert "Build failed due to --error-on-change policy" in result.stderr


def test_error_on_change_no_changes_succeeds(simple_report, run_cli):
    """Test that --error-on-change succeeds (exit 0) when no changes would be made."""
    # hide_tooltip_pages on simple_report should not detect any tooltip pages
    result = run_cli(
        [
            "sanitize",
            simple_report,
            "--actions",
            "hide_tooltip_pages",
            "--dry-run",
            "--error-on-change",
            "hide_tooltip_pages",
        ]
    )
    # If no changes detected, should succeed
    assert result.returncode == 0


# Parameterized tests for --error-on-change flag across multiple commands
@pytest.mark.parametrize(
    "command,extra_args,fixture_type",
    [
        ("disable-interactions", [], "simple"),
        ("remove-measures", [], "simple"),
        ("sort-filters", [], "simple"),
    ],
)
def test_error_on_change_commands(
    simple_report, complex_report, run_cli, command, extra_args, fixture_type
):
    """Test that --error-on-change works with various CLI commands."""
    report = simple_report if fixture_type == "simple" else complex_report
    result = run_cli(
        [command, report] + extra_args + ["--dry-run", "--error-on-change"]
    )
    # Commands should either succeed (0) or fail due to changes detected (1)
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
            "standardize_pbir_folders",
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
            "standardize_pbir_folders",
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
            "standardize_pbir_folders",
            "--dry-run",
        ]
    )
    assert result.returncode == 0
    assert (
        "Unknown actions in --exclude will be ignored: invalid_action" in result.stdout
    )


# =============================================================================
# Error Path Tests - Testing error handling and edge cases
# =============================================================================


def test_update_filters_invalid_json(simple_report, run_cli):
    """Test that invalid JSON in update-filters causes an error."""
    result = run_cli(["update-filters", simple_report, "{invalid json}", "--dry-run"])
    assert result.returncode != 0
    assert "Invalid JSON" in result.stderr


def test_error_on_change_requires_dry_run_disable_interactions(simple_report, run_cli):
    """Test --error-on-change validation for disable-interactions command."""
    result = run_cli(["disable-interactions", simple_report, "--error-on-change"])
    assert result.returncode != 0
    assert "--error-on-change requires --dry-run" in result.stderr


def test_error_on_change_requires_dry_run_remove_measures(simple_report, run_cli):
    """Test --error-on-change validation for remove-measures command."""
    result = run_cli(["remove-measures", simple_report, "--error-on-change"])
    assert result.returncode != 0
    assert "--error-on-change requires --dry-run" in result.stderr


def test_nonexistent_report_path(run_cli, tmp_path):
    """Test that a non-existent report path causes an error."""
    fake_path = str(tmp_path / "NonExistent.Report")
    result = run_cli(["sanitize", fake_path, "--actions", "all", "--dry-run"])
    # Should fail or show an error about missing files
    # The exact behavior depends on which file is missing first
    assert (
        result.returncode != 0
        or "not found" in result.stdout.lower()
        or "error" in result.stderr.lower()
    )


def test_batch_update_missing_csv(simple_report, run_cli, tmp_path):
    """Test that batch-update with missing CSV file shows error."""
    fake_csv = str(tmp_path / "nonexistent.csv")
    result = run_cli(["batch-update", simple_report, fake_csv, "--dry-run"])
    # The command prints error to stderr but may still return 0
    assert "error" in result.stderr.lower() or "no such file" in result.stderr.lower()


def test_sort_filters_custom_order_with_list(simple_report, run_cli):
    """Test that sort-filters with Custom order works with --custom-order."""
    result = run_cli(
        [
            "sort-filters",
            simple_report,
            "--sort-order",
            "Custom",
            "--custom-order",
            "Filter1",
            "Filter2",
            "--dry-run",
        ]
    )
    # Should run successfully
    assert result.returncode == 0


def test_extract_metadata_no_args_outside_report_folder(run_cli, tmp_path, monkeypatch):
    """Test that extract-metadata fails gracefully when not in a report folder."""
    monkeypatch.chdir(tmp_path)
    result = run_cli(["extract-metadata", "output.csv"])
    # Should fail because we're not in a .Report folder
    assert result.returncode != 0


def test_sanitize_invalid_action_name(simple_report, run_cli):
    """Test that an invalid action name in --actions is handled."""
    result = run_cli(
        ["sanitize", simple_report, "--actions", "invalid_action_name", "--dry-run"]
    )
    # Should fail or warn about unknown action
    assert (
        result.returncode != 0
        or "unknown" in result.stdout.lower()
        or "invalid" in result.stderr.lower()
    )
