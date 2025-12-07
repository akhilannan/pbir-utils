"""Filter-related commands for PBIR Utils CLI."""

import argparse
import sys
import textwrap

from ..command_utils import (
    add_dry_run_arg,
    add_summary_arg,
    add_error_on_change_arg,
    check_error_on_change,
    validate_error_on_change,
    parse_json_arg,
)
from ..common import resolve_report_path
from ..console_utils import console
from ..filter_utils import (
    update_report_filters,
    sort_report_filters,
    configure_filter_pane,
)


def register(subparsers):
    """Register filter-related commands."""
    _register_update_filters(subparsers)
    _register_sort_filters(subparsers)
    _register_configure_filter_pane(subparsers)


def _register_update_filters(subparsers):
    """Register the update-filters command."""
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
          pbir-utils update-filters "C:\\\\Reports" '[{"Table": "Sales", "Column": "Region", "Condition": "In", "Values": ["North", "South"]}]' --dry-run
    """
    )
    parser = subparsers.add_parser(
        "update-filters",
        help="Update report level filters",
        description=update_filters_desc,
        epilog=update_filters_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        help="Path to .Report folder or root directory containing reports",
    )
    parser.add_argument(
        "filters", help="JSON string representing list of filter configurations"
    )
    parser.add_argument(
        "--reports", nargs="+", help="List of specific reports to update"
    )
    add_dry_run_arg(parser)
    add_summary_arg(parser)
    add_error_on_change_arg(parser)
    parser.set_defaults(func=handle_update_filters)


def _register_sort_filters(subparsers):
    """Register the sort-filters command."""
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
          pbir-utils sort-filters "C:\\\\Reports" --sort-order Ascending --dry-run
          pbir-utils sort-filters "C:\\\\Reports" --sort-order Custom --custom-order "Region" "Date"
    """
    )
    parser = subparsers.add_parser(
        "sort-filters",
        help="Sort report level filter pane items",
        description=sort_filters_desc,
        epilog=sort_filters_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        help="Path to .Report folder or root directory containing reports",
    )
    parser.add_argument(
        "--reports", nargs="+", help="List of specific reports to update"
    )
    parser.add_argument(
        "--sort-order",
        default="SelectedFilterTop",
        choices=["Ascending", "Descending", "SelectedFilterTop", "Custom"],
        help="Sorting strategy",
    )
    parser.add_argument(
        "--custom-order",
        nargs="+",
        help="Custom list of filter names (required for Custom sort order)",
    )
    add_dry_run_arg(parser)
    add_summary_arg(parser)
    add_error_on_change_arg(parser)
    parser.set_defaults(func=handle_sort_filters)


def _register_configure_filter_pane(subparsers):
    """Register the configure-filter-pane command."""
    configure_filter_pane_desc = textwrap.dedent(
        """
        Configure the filter pane visibility and expanded state.
        
        Use this to show/hide or expand/collapse the filter pane.
    """
    )
    configure_filter_pane_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils configure-filter-pane "C:\\\\Reports\\\\MyReport.Report" --dry-run
          pbir-utils configure-filter-pane "C:\\\\Reports\\\\MyReport.Report" --visible false --dry-run
          pbir-utils configure-filter-pane "C:\\\\Reports\\\\MyReport.Report" --expanded true --dry-run
    """
    )
    parser = subparsers.add_parser(
        "configure-filter-pane",
        help="Configure the filter pane visibility and expanded state",
        description=configure_filter_pane_desc,
        epilog=configure_filter_pane_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    parser.add_argument(
        "--visible",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Show/hide the filter pane (default: true)",
    )
    parser.add_argument(
        "--expanded",
        type=lambda x: x.lower() == "true",
        default=False,
        help="Expand/collapse the filter pane (default: false)",
    )
    add_dry_run_arg(parser)
    add_summary_arg(parser)
    add_error_on_change_arg(parser)
    parser.set_defaults(func=handle_configure_filter_pane)


# Handlers


def handle_update_filters(args):
    """Handle the update-filters command."""
    validate_error_on_change(args)
    filters_list = parse_json_arg(args.filters, "filters")
    if not isinstance(filters_list, list):
        console.print_error("Filters must be a JSON list of objects.")
        sys.exit(1)

    has_changes = update_report_filters(
        args.report_path,
        filters=filters_list,
        reports=args.reports,
        dry_run=args.dry_run,
        summary=args.summary,
    )
    check_error_on_change(args, has_changes, "update-filters")


def handle_sort_filters(args):
    """Handle the sort-filters command."""
    validate_error_on_change(args)
    has_changes = sort_report_filters(
        args.report_path,
        reports=args.reports,
        sort_order=args.sort_order,
        custom_order=args.custom_order,
        dry_run=args.dry_run,
        summary=args.summary,
    )
    check_error_on_change(args, has_changes, "sort-filters")


def handle_configure_filter_pane(args):
    """Handle the configure-filter-pane command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = configure_filter_pane(
        report_path,
        visible=args.visible,
        expanded=args.expanded,
        dry_run=args.dry_run,
        summary=args.summary,
    )
    check_error_on_change(args, has_changes, "configure-filter-pane")
