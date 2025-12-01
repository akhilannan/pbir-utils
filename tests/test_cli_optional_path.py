import subprocess
import sys
import os
import pytest
import shutil

# Path to the src directory
SRC_DIR = os.path.join(os.path.dirname(__file__), '..', 'src')

@pytest.fixture
def dummy_report(tmp_path):
    report_dir = tmp_path / "Dummy.Report"
    report_dir.mkdir()
    definition_dir = report_dir / "definition"
    definition_dir.mkdir()
    pages_dir = definition_dir / "pages"
    pages_dir.mkdir()
    
    # Create a dummy page
    page_dir = pages_dir / "Page1"
    page_dir.mkdir()
    # Create a dummy visual
    visuals_dir = page_dir / "visuals"
    visuals_dir.mkdir()

    return str(report_dir)

def run_cli_command(args, cwd=None):
    """Helper to run CLI commands."""
    cmd = [sys.executable, '-m', 'pbir_utils.cli'] + args
    env = os.environ.copy()
    env['PYTHONPATH'] = SRC_DIR + os.pathsep + env.get('PYTHONPATH', '')
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=cwd)
    return result

def test_sanitize_no_path_in_report_dir(dummy_report):
    # Run sanitize without path inside a .Report dir
    result = run_cli_command(['sanitize', '--actions', 'remove_unused_measures', '--dry-run'], cwd=dummy_report)
    assert result.returncode == 0

def test_sanitize_no_path_outside_report_dir(tmp_path):
    # Run sanitize without path outside a .Report dir
    result = run_cli_command(['sanitize', '--actions', 'remove_unused_measures', '--dry-run'], cwd=str(tmp_path))
    assert result.returncode != 0
    assert "Error: report_path not provided" in result.stderr

def test_extract_metadata_infer_path(dummy_report, tmp_path):
    # Run extract-metadata with only output path inside a .Report dir
    output_csv = tmp_path / 'output.csv'
    result = run_cli_command(['extract-metadata', str(output_csv)], cwd=dummy_report)
    assert result.returncode == 0

def test_extract_metadata_explicit_path(dummy_report, tmp_path):
    # Run extract-metadata with explicit report path and output path
    output_csv = tmp_path / 'output_explicit.csv'
    result = run_cli_command(['extract-metadata', dummy_report, str(output_csv)])
    assert result.returncode == 0

def test_extract_metadata_no_args_error(dummy_report):
    # Run extract-metadata with no args
    result = run_cli_command(['extract-metadata'], cwd=dummy_report)
    assert result.returncode != 0
    assert "Error: Output path required." in result.stderr

def test_visualize_no_path_in_report_dir(dummy_report):
    # Run visualize without path inside a .Report dir
    # Note: visualize might try to open a browser or server, but we just check if it parses args correctly.
    # However, visualize usually blocks. We might need to mock it or just check if it fails with path error if not in report dir.
    # Since we can't easily test blocking commands, we'll test the failure case outside report dir.
    pass

def test_visualize_no_path_outside_report_dir(tmp_path):
    result = run_cli_command(['visualize'], cwd=str(tmp_path))
    assert result.returncode != 0
    assert "Error: report_path not provided" in result.stderr

def test_disable_interactions_no_path_in_report_dir(dummy_report):
    result = run_cli_command(['disable-interactions', '--dry-run'], cwd=dummy_report)
    assert result.returncode == 0

def test_remove_measures_no_path_in_report_dir(dummy_report):
    result = run_cli_command(['remove-measures', '--dry-run'], cwd=dummy_report)
    assert result.returncode == 0

def test_measure_dependencies_no_path_in_report_dir(dummy_report):
    # measure-dependencies prints to stdout, doesn't block
    result = run_cli_command(['measure-dependencies'], cwd=dummy_report)
    assert result.returncode == 0
