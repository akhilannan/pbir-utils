import subprocess
import sys
import os
import pytest
import shutil
import json

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
    with open(page_dir / "page.json", "w") as f:
        json.dump({"name": "Page1", "displayName": "Page 1"}, f)
        
    # Create a dummy visual
    visuals_dir = page_dir / "visuals"
    visuals_dir.mkdir()
    with open(visuals_dir / "visual1.json", "w") as f:
        json.dump({"name": "visual1", "type": "slicer"}, f)

    return str(report_dir)

def run_cli_command(args):
    """Helper to run CLI commands."""
    cmd = [sys.executable, '-m', 'pbir_utils.cli'] + args
    env = os.environ.copy()
    env['PYTHONPATH'] = SRC_DIR + os.pathsep + env.get('PYTHONPATH', '')
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result

def test_sanitize_dry_run(dummy_report):
    result = run_cli_command(['sanitize', dummy_report, '--actions', 'remove_unused_measures', '--dry-run'])
    assert result.returncode == 0
    # Output might vary depending on implementation, but it shouldn't crash

def test_extract_metadata(dummy_report, tmp_path):
    output_csv = tmp_path / 'output.csv'
    result = run_cli_command(['extract-metadata', dummy_report, str(output_csv)])
    assert result.returncode == 0

def test_visualize_help():
    result = run_cli_command(['visualize', '--help'])
    assert result.returncode == 0

def test_batch_update_dry_run(dummy_report, tmp_path):
    csv_path = tmp_path / 'mapping.csv'
    with open(csv_path, 'w') as f:
        f.write("old_tbl,old_col,new_tbl,new_col\nTable1,Col1,Table1,ColNew")
    
    # batch_update expects the parent directory of definition usually, or the definition folder itself depending on implementation.
    # Based on code, it walks the directory.
    result = run_cli_command(['batch-update', dummy_report, str(csv_path), '--dry-run'])
    assert result.returncode == 0

def test_disable_interactions_dry_run(dummy_report):
    result = run_cli_command(['disable-interactions', dummy_report, '--dry-run'])
    assert result.returncode == 0

def test_remove_measures_dry_run(dummy_report):
    result = run_cli_command(['remove-measures', dummy_report, '--dry-run'])
    assert result.returncode == 0

def test_measure_dependencies(dummy_report):
    result = run_cli_command(['measure-dependencies', dummy_report])
    assert result.returncode == 0

def test_update_filters_dry_run(dummy_report):
    filters = '[{"Table": "Tbl", "Column": "Col", "Condition": "In", "Values": ["A"]}]'
    result = run_cli_command(['update-filters', dummy_report, filters, '--dry-run'])
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.returncode == 0

def test_sort_filters_dry_run(dummy_report):
    result = run_cli_command(['sort-filters', dummy_report, '--dry-run'])
    assert result.returncode == 0
