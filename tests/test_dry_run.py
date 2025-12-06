import os
from pbir_utils.pbir_report_sanitizer import sanitize_powerbi_report
from pbir_utils.pbir_processor import batch_update_pbir_project
from pbir_utils.pbir_measure_utils import remove_measures
from pbir_utils.filter_utils import update_report_filters, sort_report_filters
from pbir_utils.visual_interactions_utils import disable_visual_interactions


def get_dir_mtime(directory):
    mtimes = {}
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            mtimes[path] = os.path.getmtime(path)
    return mtimes


def test_sanitize_powerbi_report_dry_run(complex_report):
    initial_mtimes = get_dir_mtime(complex_report)

    actions = [
        "remove_unused_measures",
        "remove_unused_bookmarks",
        "remove_unused_custom_visuals",
        "disable_show_items_with_no_data",
        "hide_tooltip_drillthrough_pages",
        "set_first_page_as_active",
        "remove_empty_pages",
        "remove_hidden_visuals_never_shown",
        "cleanup_invalid_bookmarks",
    ]

    sanitize_powerbi_report(complex_report, actions, dry_run=True)

    final_mtimes = get_dir_mtime(complex_report)
    assert initial_mtimes == final_mtimes, "Files were modified during dry run!"


def test_batch_update_pbir_project_dry_run(complex_report):
    initial_mtimes = get_dir_mtime(complex_report)

    # Create a dummy CSV for mapping
    csv_path = os.path.join(complex_report, "mapping.csv")
    with open(csv_path, "w") as f:
        f.write("old_tbl,old_col,new_tbl,new_col\nTable1,Col1,Table1_New,Col1_New")

    # Exclude the CSV from mtime check
    initial_mtimes = get_dir_mtime(complex_report)

    batch_update_pbir_project(os.path.dirname(complex_report), csv_path, dry_run=True)

    final_mtimes = get_dir_mtime(complex_report)
    assert initial_mtimes == final_mtimes, "Files were modified during dry run!"


def test_remove_measures_dry_run(complex_report):
    initial_mtimes = get_dir_mtime(complex_report)

    remove_measures(complex_report, dry_run=True)

    final_mtimes = get_dir_mtime(complex_report)
    assert initial_mtimes == final_mtimes, "Files were modified during dry run!"


def test_update_report_filters_dry_run(complex_report):
    initial_mtimes = get_dir_mtime(complex_report)

    filters = [
        {
            "Table": "Table1",
            "Column": "Column1",
            "Condition": "GreaterThan",
            "Values": ["100"],
        }
    ]

    update_report_filters(os.path.dirname(complex_report), filters, dry_run=True)

    final_mtimes = get_dir_mtime(complex_report)
    assert initial_mtimes == final_mtimes, "Files were modified during dry run!"


def test_sort_report_filters_dry_run(complex_report):
    initial_mtimes = get_dir_mtime(complex_report)

    sort_report_filters(
        os.path.dirname(complex_report), sort_order="Ascending", dry_run=True
    )

    final_mtimes = get_dir_mtime(complex_report)
    assert initial_mtimes == final_mtimes, "Files were modified during dry run!"


def test_disable_visual_interactions_dry_run(complex_report):
    initial_mtimes = get_dir_mtime(complex_report)

    disable_visual_interactions(complex_report, dry_run=True)

    final_mtimes = get_dir_mtime(complex_report)
    assert initial_mtimes == final_mtimes, "Files were modified during dry run!"
