import argparse
import json
import sys
import textwrap
from typing import List, Dict, Set, Optional
from .console_utils import console

from .common import resolve_report_path
from .pbir_report_sanitizer import (
    sanitize_powerbi_report,
    AVAILABLE_ACTIONS,
    remove_unused_bookmarks,
    remove_unused_custom_visuals,
    disable_show_items_with_no_data,
    hide_tooltip_drillthrough_pages,
    set_first_page_as_active,
    remove_empty_pages,
    remove_hidden_visuals_never_shown,
    cleanup_invalid_bookmarks,
)
from .metadata_extractor import export_pbir_metadata_to_csv
from .report_wireframe_visualizer import display_report_wireframes
from .pbir_processor import batch_update_pbir_project
from .visual_interactions_utils import disable_visual_interactions
from .pbir_measure_utils import remove_measures, generate_measure_dependencies_report
from .filter_utils import update_report_filters, sort_report_filters
from .folder_standardizer import standardize_pbir_folders


def parse_filters(filters_str: str) -> Optional[Dict[str, Set[str]]]:
    if not filters_str:
        return None
    try:
        data = json.loads(filters_str)
        if not isinstance(data, dict):
            raise ValueError("Filters must be a JSON object.")
        # Convert lists to sets
        return {k: set(v) if isinstance(v, list) else set([v]) for k, v in data.items()}
    except json.JSONDecodeError:
        console.print_error(f"Invalid JSON string for filters: {filters_str}")
        sys.exit(1)
    except Exception as e:
        console.print_error(f"Parsing filters: {e}")
        sys.exit(1)


def parse_list_arg(arg_value: Optional[List[str]]) -> Optional[List[str]]:
    """Helper to handle list arguments that might be passed as a single string or list."""
    if not arg_value:
        return None
    # If it's already a list, return it (argparse nargs='+' produces a list)
    return arg_value


def parse_json_arg(json_str: Optional[str], arg_name: str):
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        console.print_error(f"Invalid JSON string for {arg_name}: {json_str}")
        sys.exit(1)


def _check_error_on_change(args, has_changes: bool, command_name: str):
    """
    Check if --error-on-change is specified and if changes would be made.
    Exits with code 1 if validation fails.

    Args:
        args: Parsed command line arguments.
        has_changes: Whether changes were made (or would be made in dry run).
        command_name: Name of the command for error messages.
    """
    error_on_change = getattr(args, "error_on_change", False)
    if error_on_change:
        if not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        if has_changes:
            console.print_error(f"Error: {command_name} would make changes.")
            console.print_error("Build failed due to --error-on-change policy.")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="PBIR Utilities CLI - A tool for managing Power BI Enhanced Report Format (PBIR) projects.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Sanitize Command
    sanitize_desc = textwrap.dedent(
        """
        Sanitize a Power BI report by removing unused or unwanted components.
        
        Available Actions:
          - all: Performs ALL sanitization actions listed below.
          - remove_unused_measures: Removes measures not used in any visuals.
          - remove_unused_bookmarks: Removes bookmarks not activated by navigators/actions.
          - remove_unused_custom_visuals: Removes unused custom visuals.
          - disable_show_items_with_no_data: Disables "Show items with no data" for all visuals.
          - hide_tooltip_drillthrough_pages: Hides tooltip and drillthrough pages.
          - set_first_page_as_active: Sets the first page as active.
          - remove_empty_pages: Removes pages with no visuals.
          - remove_hidden_visuals_never_shown: Removes permanently hidden visuals.

          - cleanup_invalid_bookmarks: Removes bookmarks referencing non-existent pages/visuals.
          - standardize_folder_names: Standardizes page and visual folder names to be descriptive.
    """
    )
    sanitize_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils sanitize "C:\\Reports\\MyReport.Report" --actions remove_unused_measures cleanup_invalid_bookmarks --dry-run
          pbir-utils sanitize "C:\\Reports\\MyReport.Report" --actions all --dry-run
          pbir-utils sanitize "C:\\Reports\\MyReport.Report" --actions all --exclude set_first_page_as_active standardize_folder_names --dry-run
          pbir-utils sanitize "C:\\Reports\\MyReport.Report" --actions all --dry-run --error-on-change set_first_page_as_active remove_empty_pages
    """
    )
    sanitize_parser = subparsers.add_parser(
        "sanitize",
        help="Sanitize a Power BI report",
        description=sanitize_desc,
        epilog=sanitize_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sanitize_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    sanitize_parser.add_argument(
        "--actions", nargs="+", help="List of sanitization actions to perform"
    )
    sanitize_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    sanitize_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    sanitize_parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="ACTION",
        help="Actions to exclude when using '--actions all'. Ignored if specific actions are listed.",
    )
    sanitize_parser.add_argument(
        "--error-on-change",
        nargs="+",
        metavar="ACTION",
        help="Exit with error code 1 if specified actions would make changes during dry run. Only valid with --dry-run.",
    )

    # Extract Metadata Command
    extract_desc = textwrap.dedent(
        """
        Export attribute metadata from PBIR to CSV.
        
        Extracts detailed information about tables, columns, measures, DAX expressions, and usage contexts.
    """
    )
    extract_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils extract-metadata "C:\\Reports\\MyReport.Report" "C:\\Output\\metadata.csv"
          pbir-utils extract-metadata "C:\\Reports" "C:\\Output\\all_metadata.csv" --filters '{"Page Name": ["Overview"]}'
    """
    )
    extract_parser = subparsers.add_parser(
        "extract-metadata",
        help="Extract metadata to CSV",
        description=extract_desc,
        epilog=extract_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    extract_parser.add_argument(
        "args",
        nargs="*",
        help="[report_path] output_path. If 1 arg provided and it ends in .csv, it is treated as output_path and report_path is inferred.",
    )
    extract_parser.add_argument(
        "--filters",
        help='JSON string representing filters (e.g., \'{"Page Name": ["Page1"]}\'). Keys: Report, Page Name, Page ID, Table, Column or Measure, Expression, Used In, Used In Detail, ID',
    )

    # Visualize Command
    visualize_desc = textwrap.dedent(
        """
        Display report wireframes using Dash and Plotly.
        
        Visualizes the layout of pages and their visual components.
        
        Behavior:
        The `pages`, `visual_types`, and `visual_ids` parameters work with an AND logic, 
        meaning that only visuals matching ALL specified criteria will be shown.
    """
    )
    visualize_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils visualize "C:\\Reports\\MyReport.Report"
          pbir-utils visualize "C:\\Reports\\MyReport.Report" --pages "Overview" "Detail" --visual-types slicer
    """
    )
    visualize_parser = subparsers.add_parser(
        "visualize",
        help="Display report wireframes",
        description=visualize_desc,
        epilog=visualize_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    visualize_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    visualize_parser.add_argument(
        "--pages", nargs="+", help="List of page IDs to include"
    )
    visualize_parser.add_argument(
        "--visual-types", nargs="+", help="List of visual types to include"
    )
    visualize_parser.add_argument(
        "--visual-ids", nargs="+", help="List of visual IDs to include"
    )
    visualize_parser.add_argument(
        "--no-show-hidden",
        action="store_false",
        dest="show_hidden",
        help="Do not show hidden visuals (default: show them)",
    )
    visualize_parser.set_defaults(show_hidden=True)

    # Batch Update Command
    batch_update_desc = textwrap.dedent(
        """
        Batch update attributes in PBIR project.
        
        Performs a batch update on all components of a Power BI Enhanced Report Format (PBIR) project 
        by processing JSON files in the specified directory. Updates table and column references 
        based on mappings provided in a CSV file.
        
        CSV Format (Attribute_Mapping.csv):
          - old_tbl: Old table names
          - old_col: Old column names
          - new_tbl: New table names (optional if unchanged)
          - new_col: New column names
    """
    )
    batch_update_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils batch-update "C:\\PBIR\\Project" "C:\\Mapping.csv" --dry-run
    """
    )
    batch_update_parser = subparsers.add_parser(
        "batch-update",
        help="Batch update attributes in PBIR project",
        description=batch_update_desc,
        epilog=batch_update_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    batch_update_parser.add_argument(
        "directory_path", help="Path to the root directory of the PBIR project"
    )
    batch_update_parser.add_argument(
        "csv_path", help="Path to the Attribute_Mapping.csv file"
    )
    batch_update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    batch_update_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Disable Interactions Command
    disable_interactions_desc = textwrap.dedent(
        """
        Disable visual interactions.
        
        Disables interactions between visuals based on source/target parameters.
        
        Behavior:
          - If only `report_path` is provided, disables interactions between ALL visuals on ALL pages.
          - If `pages` is provided, limits scope to those pages.
          - If source/target visuals are specified, limits scope to those interactions.
        
        Update Types:
          - Upsert: Disables any existing interactions that match the specified source/target parameters and inserts new combinations. Interactions not part of the specified source/target parameters will remain unchanged. (Default)
          - Insert: Inserts new interactions based on the source/target parameters without modifying existing interactions.
          - Overwrite: Replaces all existing interactions with the new ones that match the specified source/target parameters, removing any interactions not part of the new configuration.
    """
    )
    disable_interactions_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils disable-interactions "C:\\Reports\\MyReport.Report" --dry-run
          pbir-utils disable-interactions "C:\\Reports\\MyReport.Report" --pages "Overview" --source-visual-types slicer
    """
    )
    disable_interactions_parser = subparsers.add_parser(
        "disable-interactions",
        help="Disable visual interactions",
        description=disable_interactions_desc,
        epilog=disable_interactions_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    disable_interactions_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    disable_interactions_parser.add_argument(
        "--pages", nargs="+", help="List of page names to process"
    )
    disable_interactions_parser.add_argument(
        "--source-visual-ids", nargs="+", help="List of source visual IDs"
    )
    disable_interactions_parser.add_argument(
        "--source-visual-types", nargs="+", help="List of source visual types"
    )
    disable_interactions_parser.add_argument(
        "--target-visual-ids", nargs="+", help="List of target visual IDs"
    )
    disable_interactions_parser.add_argument(
        "--target-visual-types", nargs="+", help="List of target visual types"
    )
    disable_interactions_parser.add_argument(
        "--update-type",
        default="Upsert",
        choices=["Upsert", "Insert", "Overwrite"],
        help="Update type (Upsert, Insert, Overwrite)",
    )
    disable_interactions_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    disable_interactions_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    disable_interactions_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Remove Measures Command
    remove_measures_desc = textwrap.dedent(
        """
        Remove report level measures.
        
        Scans through a Power BI PBIR Report and removes report-level measures.
        Can remove all measures or a specified list of measures.
        
        Visual Usage Check:
          - If enabled (default), only removes a measure if neither the measure itself 
            nor any of its dependent measures are used in any visuals.
    """
    )
    remove_measures_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils remove-measures "C:\\Reports\\MyReport.Report" --dry-run
          pbir-utils remove-measures "C:\\Reports\\MyReport.Report" --measure-names "Measure1" "Measure2" --no-check-usage
    """
    )
    remove_measures_parser = subparsers.add_parser(
        "remove-measures",
        help="Remove report level measures",
        description=remove_measures_desc,
        epilog=remove_measures_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    remove_measures_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    remove_measures_parser.add_argument(
        "--measure-names",
        nargs="+",
        help="List of measure names to remove (default: all measures)",
    )
    remove_measures_parser.add_argument(
        "--no-check-usage",
        action="store_false",
        dest="check_visual_usage",
        help="Do not check visual usage before removing (default: check usage)",
    )
    remove_measures_parser.set_defaults(check_visual_usage=True)
    remove_measures_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    remove_measures_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    remove_measures_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Measure Dependencies Command
    measure_deps_desc = textwrap.dedent(
        """
        Generate measure dependencies report.
        
        Generates a dependency tree for measures, focusing on measures that depend on other measures.
    """
    )
    measure_deps_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils measure-dependencies "C:\\Reports\\MyReport.Report"
          pbir-utils measure-dependencies "C:\\Reports\\MyReport.Report" --measure-names "Total Sales" --include-visual-ids
    """
    )
    measure_deps_parser = subparsers.add_parser(
        "measure-dependencies",
        help="Generate measure dependencies report",
        description=measure_deps_desc,
        epilog=measure_deps_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    measure_deps_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    measure_deps_parser.add_argument(
        "--measure-names",
        nargs="+",
        help="List of measure names to analyze (default: all measures)",
    )
    measure_deps_parser.add_argument(
        "--include-visual-ids",
        action="store_true",
        help="Include visual IDs in the report",
    )

    # Update Filters Command
    update_filters_desc = textwrap.dedent(
        """
        Update report level filters.
        
        Applies filter configurations to reports.
        
        Filters JSON format: List of objects with:
          - Table: Table name
          - Column: Column name
          - Condition: Condition type
          - Values: List of values (or null to clear filter)
          
        Supported Conditions:
          - Comparison: GreaterThan, GreaterThanOrEqual, LessThan, LessThanOrEqual
          - Range: Between, NotBetween (requires 2 values)
          - Inclusion: In, NotIn
          - Text: Contains, StartsWith, EndsWith, NotContains, etc.
          - Multi-Text: ContainsAnd, StartsWithOr, etc.
          
        Value Formats:
          - Dates: "DD-MMM-YYYY" (e.g., "15-Sep-2023")
          - Numbers: Integers or floats
          - Clear Filter: Set "Values": null
    """
    )
    update_filters_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils update-filters "C:\\Reports" '[{"Table": "Sales", "Column": "Region", "Condition": "In", "Values": ["North", "South"]}]' --dry-run
    """
    )
    update_filters_parser = subparsers.add_parser(
        "update-filters",
        help="Update report level filters",
        description=update_filters_desc,
        epilog=update_filters_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    update_filters_parser.add_argument(
        "directory_path", help="Root directory containing reports"
    )
    update_filters_parser.add_argument(
        "filters", help="JSON string representing list of filter configurations"
    )
    update_filters_parser.add_argument(
        "--reports", nargs="+", help="List of specific reports to update"
    )
    update_filters_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    update_filters_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    update_filters_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Sort Filters Command
    sort_filters_desc = textwrap.dedent(
        """
        Sort report level filter pane items.
        
        Sorting Strategies:
          - Ascending: Alphabetical (A-Z).
          - Descending: Reverse alphabetical (Z-A).
          - SelectedFilterTop: Prioritizes filters that have been selected (have a condition applied). 
            Selected filters are placed at the top (A-Z), followed by unselected filters (A-Z). (Default)
          - Custom: User-defined order using --custom-order.
    """
    )
    sort_filters_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils sort-filters "C:\\Reports" --sort-order Ascending --dry-run
          pbir-utils sort-filters "C:\\Reports" --sort-order Custom --custom-order "Region" "Date"
    """
    )
    sort_filters_parser = subparsers.add_parser(
        "sort-filters",
        help="Sort report level filter pane items",
        description=sort_filters_desc,
        epilog=sort_filters_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sort_filters_parser.add_argument(
        "directory_path", help="Root directory containing reports"
    )
    sort_filters_parser.add_argument(
        "--reports", nargs="+", help="List of specific reports to update"
    )
    sort_filters_parser.add_argument(
        "--sort-order",
        default="SelectedFilterTop",
        choices=["Ascending", "Descending", "SelectedFilterTop", "Custom"],
        help="Sorting strategy",
    )
    sort_filters_parser.add_argument(
        "--custom-order",
        nargs="+",
        help="Custom list of filter names (required for Custom sort order)",
    )
    sort_filters_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    sort_filters_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    sort_filters_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Standardize Folder Names Command
    standardize_folders_desc = textwrap.dedent(
        """
        Standardize page and visual folder names to be descriptive.
        
        Renames page folders to "<DisplayName>_<Name>" and visual folders to "<VisualType>_<Name>".
        Sanitizes display names to be safe for file systems.
    """
    )
    standardize_folders_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils standardize-folder-names "C:\\Reports\\MyReport.Report" --dry-run
    """
    )
    standardize_folders_parser = subparsers.add_parser(
        "standardize-folder-names",
        help="Standardize page and visual folder names",
        description=standardize_folders_desc,
        epilog=standardize_folders_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    standardize_folders_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    standardize_folders_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    standardize_folders_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    standardize_folders_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Remove Unused Bookmarks Command
    remove_unused_bookmarks_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils remove-unused-bookmarks "C:\\Reports\\MyReport.Report" --dry-run
    """
    )
    remove_unused_bookmarks_parser = subparsers.add_parser(
        "remove-unused-bookmarks",
        help="Remove unused bookmarks",
        description="Remove bookmarks which are not activated in report using bookmark navigator or actions.",
        epilog=remove_unused_bookmarks_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    remove_unused_bookmarks_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    remove_unused_bookmarks_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    remove_unused_bookmarks_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    remove_unused_bookmarks_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Remove Unused Custom Visuals Command
    remove_unused_custom_visuals_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils remove-unused-custom-visuals "C:\\Reports\\MyReport.Report" --dry-run
    """
    )
    remove_unused_custom_visuals_parser = subparsers.add_parser(
        "remove-unused-custom-visuals",
        help="Remove unused custom visuals",
        description="Remove unused custom visuals from the report.",
        epilog=remove_unused_custom_visuals_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    remove_unused_custom_visuals_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    remove_unused_custom_visuals_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    remove_unused_custom_visuals_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    remove_unused_custom_visuals_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Disable Show Items With No Data Command
    disable_show_items_with_no_data_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils disable-show-items-with-no-data "C:\\Reports\\MyReport.Report" --dry-run
    """
    )
    disable_show_items_with_no_data_parser = subparsers.add_parser(
        "disable-show-items-with-no-data",
        help="Disable 'Show items with no data'",
        description="Disable the 'Show items with no data' option for visuals.",
        epilog=disable_show_items_with_no_data_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    disable_show_items_with_no_data_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    disable_show_items_with_no_data_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    disable_show_items_with_no_data_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    disable_show_items_with_no_data_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Hide Tooltip Drillthrough Pages Command
    hide_tooltip_drillthrough_pages_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils hide-tooltip-drillthrough-pages "C:\\Reports\\MyReport.Report" --dry-run
    """
    )
    hide_tooltip_drillthrough_pages_parser = subparsers.add_parser(
        "hide-tooltip-drillthrough-pages",
        help="Hide tooltip and drillthrough pages",
        description="Hide tooltip and drillthrough pages in the report.",
        epilog=hide_tooltip_drillthrough_pages_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    hide_tooltip_drillthrough_pages_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    hide_tooltip_drillthrough_pages_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    hide_tooltip_drillthrough_pages_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    hide_tooltip_drillthrough_pages_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Set First Page As Active Command
    set_first_page_as_active_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils set-first-page-as-active "C:\\Reports\\MyReport.Report" --dry-run
    """
    )
    set_first_page_as_active_parser = subparsers.add_parser(
        "set-first-page-as-active",
        help="Set the first page as active",
        description="Set the first page of the report as active.",
        epilog=set_first_page_as_active_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    set_first_page_as_active_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    set_first_page_as_active_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    set_first_page_as_active_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    set_first_page_as_active_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Remove Empty Pages Command
    remove_empty_pages_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils remove-empty-pages "C:\\Reports\\MyReport.Report" --dry-run
    """
    )
    remove_empty_pages_parser = subparsers.add_parser(
        "remove-empty-pages",
        help="Remove empty pages",
        description="Remove empty pages and clean up rogue folders in the report.",
        epilog=remove_empty_pages_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    remove_empty_pages_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    remove_empty_pages_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    remove_empty_pages_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    remove_empty_pages_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Remove Hidden Visuals Command
    remove_hidden_visuals_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils remove-hidden-visuals "C:\\Reports\\MyReport.Report" --dry-run
    """
    )
    remove_hidden_visuals_parser = subparsers.add_parser(
        "remove-hidden-visuals",
        help="Remove hidden visuals never shown",
        description="Remove hidden visuals that are never shown using bookmarks.",
        epilog=remove_hidden_visuals_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    remove_hidden_visuals_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    remove_hidden_visuals_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    remove_hidden_visuals_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    remove_hidden_visuals_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    # Cleanup Invalid Bookmarks Command
    cleanup_invalid_bookmarks_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils cleanup-invalid-bookmarks "C:\\Reports\\MyReport.Report" --dry-run
    """
    )
    cleanup_invalid_bookmarks_parser = subparsers.add_parser(
        "cleanup-invalid-bookmarks",
        help="Cleanup invalid bookmarks",
        description="Clean up invalid bookmarks that reference non-existent pages or visuals.",
        epilog=cleanup_invalid_bookmarks_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    cleanup_invalid_bookmarks_parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    cleanup_invalid_bookmarks_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    cleanup_invalid_bookmarks_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )
    cleanup_invalid_bookmarks_parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )

    args = parser.parse_args()

    if args.command == "sanitize":
        report_path = resolve_report_path(args.report_path)
        actions = args.actions if args.actions else []

        if "all" in actions:
            actions = list(AVAILABLE_ACTIONS.keys())
            # Apply exclusions if specified
            if args.exclude:
                invalid_excludes = [
                    e for e in args.exclude if e not in AVAILABLE_ACTIONS
                ]
                if invalid_excludes:
                    console.print_warning(
                        f"Unknown actions in --exclude will be ignored: {', '.join(invalid_excludes)}"
                    )
                actions = [a for a in actions if a not in args.exclude]

        if not actions:
            console.print_warning(
                "No actions specified. Use --actions to specify sanitization actions."
            )

        # Validate --error-on-change requires --dry-run
        error_on_change = (
            args.error_on_change if hasattr(args, "error_on_change") else None
        )
        if error_on_change and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)

        # Run sanitization and get results
        results = sanitize_powerbi_report(
            report_path, actions, dry_run=args.dry_run, summary=args.summary
        )

        # Check if any error_on_change actions would make changes
        if error_on_change:
            actions_with_changes = [
                action
                for action in error_on_change
                if action in results and results[action]
            ]
            if actions_with_changes:
                console.print_error(
                    f"Error: The following checks would make changes: {', '.join(actions_with_changes)}"
                )
                console.print_error("Build failed due to --error-on-change policy.")
                sys.exit(1)

    elif args.command == "extract-metadata":
        # Argument resolution logic for extract-metadata
        cmd_args = args.args
        report_path = None
        output_path = None

        if len(cmd_args) == 0:
            console.print_error("Output path required.")
            sys.exit(1)
        elif len(cmd_args) == 1:
            if cmd_args[0].lower().endswith(".csv"):
                report_path = resolve_report_path(None)
                output_path = cmd_args[0]
            else:
                report_path = cmd_args[0]
                console.print_error("Output path required.")
                sys.exit(1)
        elif len(cmd_args) == 2:
            report_path = cmd_args[0]
            output_path = cmd_args[1]
        else:
            console.print_error("Too many arguments.")
            sys.exit(1)

        filters = parse_filters(args.filters)
        export_pbir_metadata_to_csv(report_path, output_path, filters=filters)

    elif args.command == "visualize":
        report_path = resolve_report_path(args.report_path)
        display_report_wireframes(
            report_path,
            pages=args.pages,
            visual_types=args.visual_types,
            visual_ids=args.visual_ids,
            show_hidden=args.show_hidden,
        )

    elif args.command == "batch-update":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        has_changes = batch_update_pbir_project(
            args.directory_path, args.csv_path, dry_run=args.dry_run
        )
        _check_error_on_change(args, has_changes, "batch-update")

    elif args.command == "disable-interactions":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        report_path = resolve_report_path(args.report_path)
        has_changes = disable_visual_interactions(
            report_path,
            pages=args.pages,
            source_visual_ids=args.source_visual_ids,
            source_visual_types=args.source_visual_types,
            target_visual_ids=args.target_visual_ids,
            target_visual_types=args.target_visual_types,
            update_type=args.update_type,
            dry_run=args.dry_run,
            summary=args.summary,
        )
        _check_error_on_change(args, has_changes, "disable-interactions")

    elif args.command == "remove-measures":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        report_path = resolve_report_path(args.report_path)
        has_changes = remove_measures(
            report_path,
            measure_names=args.measure_names,
            check_visual_usage=args.check_visual_usage,
            dry_run=args.dry_run,
            summary=args.summary,
        )
        _check_error_on_change(args, has_changes, "remove-measures")

    elif args.command == "measure-dependencies":
        report_path = resolve_report_path(args.report_path)
        report = generate_measure_dependencies_report(
            report_path,
            measure_names=args.measure_names,
            include_visual_ids=args.include_visual_ids,
        )
        print(report)

    elif args.command == "update-filters":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        filters_list = parse_json_arg(args.filters, "filters")
        if not isinstance(filters_list, list):
            print("Error: Filters must be a JSON list of objects.", file=sys.stderr)
            sys.exit(1)

        has_changes = update_report_filters(
            args.directory_path,
            filters=filters_list,
            reports=args.reports,
            dry_run=args.dry_run,
            summary=args.summary,
        )
        _check_error_on_change(args, has_changes, "update-filters")

    elif args.command == "sort-filters":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        has_changes = sort_report_filters(
            args.directory_path,
            reports=args.reports,
            sort_order=args.sort_order,
            custom_order=args.custom_order,
            dry_run=args.dry_run,
            summary=args.summary,
        )
        _check_error_on_change(args, has_changes, "sort-filters")

    elif args.command == "standardize-folder-names":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        report_path = resolve_report_path(args.report_path)
        has_changes = standardize_pbir_folders(
            report_path, dry_run=args.dry_run, summary=args.summary
        )
        _check_error_on_change(args, has_changes, "standardize-folder-names")

    elif args.command == "remove-unused-bookmarks":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        report_path = resolve_report_path(args.report_path)
        has_changes = remove_unused_bookmarks(
            report_path, dry_run=args.dry_run, summary=args.summary
        )
        _check_error_on_change(args, has_changes, "remove-unused-bookmarks")

    elif args.command == "remove-unused-custom-visuals":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        report_path = resolve_report_path(args.report_path)
        has_changes = remove_unused_custom_visuals(
            report_path, dry_run=args.dry_run, summary=args.summary
        )
        _check_error_on_change(args, has_changes, "remove-unused-custom-visuals")

    elif args.command == "disable-show-items-with-no-data":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        report_path = resolve_report_path(args.report_path)
        has_changes = disable_show_items_with_no_data(
            report_path, dry_run=args.dry_run, summary=args.summary
        )
        _check_error_on_change(args, has_changes, "disable-show-items-with-no-data")

    elif args.command == "hide-tooltip-drillthrough-pages":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        report_path = resolve_report_path(args.report_path)
        has_changes = hide_tooltip_drillthrough_pages(
            report_path, dry_run=args.dry_run, summary=args.summary
        )
        _check_error_on_change(args, has_changes, "hide-tooltip-drillthrough-pages")

    elif args.command == "set-first-page-as-active":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        report_path = resolve_report_path(args.report_path)
        has_changes = set_first_page_as_active(
            report_path, dry_run=args.dry_run, summary=args.summary
        )
        _check_error_on_change(args, has_changes, "set-first-page-as-active")

    elif args.command == "remove-empty-pages":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        report_path = resolve_report_path(args.report_path)
        has_changes = remove_empty_pages(
            report_path, dry_run=args.dry_run, summary=args.summary
        )
        _check_error_on_change(args, has_changes, "remove-empty-pages")

    elif args.command == "remove-hidden-visuals":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        report_path = resolve_report_path(args.report_path)
        has_changes = remove_hidden_visuals_never_shown(
            report_path, dry_run=args.dry_run, summary=args.summary
        )
        _check_error_on_change(args, has_changes, "remove-hidden-visuals")

    elif args.command == "cleanup-invalid-bookmarks":
        # Validate --error-on-change requires --dry-run
        if getattr(args, "error_on_change", False) and not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        report_path = resolve_report_path(args.report_path)
        has_changes = cleanup_invalid_bookmarks(
            report_path, dry_run=args.dry_run, summary=args.summary
        )
        _check_error_on_change(args, has_changes, "cleanup-invalid-bookmarks")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
