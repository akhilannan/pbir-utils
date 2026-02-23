"""Page-related commands for PBIR Utils CLI."""

__all__ = [
    "register",
    "handle_set_display_option",
    "handle_set_page_order",
    "handle_set_active_page",
]

import argparse
import textwrap

from ..command_utils import (
    add_dry_run_arg,
    add_summary_arg,
)


def register(subparsers):
    """Register page-related commands."""
    _register_set_display_option(subparsers)
    _register_set_page_order(subparsers)
    _register_set_active_page(subparsers)


def _register_set_display_option(subparsers):
    """Register the set-display-option command."""
    desc = textwrap.dedent(
        """
        Set the display option for pages in a Power BI report.
        
        The display option controls how pages are rendered:
          - ActualSize: Pages display at their actual size
          - FitToPage: Pages scale to fit the entire page in the viewport
          - FitToWidth: Pages scale to fit the width of the viewport
        
        If --page is omitted, the display option is applied to all pages.
        The --page argument matches against both the page 'name' and 'displayName'.
    """
    )

    epilog = textwrap.dedent(
        r"""
        Examples:
          # Set all pages to FitToWidth (dry run)
          pbir-utils set-display-option "C:\Reports\MyReport.Report" --option FitToWidth --dry-run
          
          # Set a specific page by display name
          pbir-utils set-display-option "C:\Reports\MyReport.Report" --page "Trends" --option ActualSize
          
          # Set a specific page by internal name
          pbir-utils set-display-option "C:\Reports\MyReport.Report" --page "bb40336091625ae0070a" --option FitToPage
    """
    )

    parser = subparsers.add_parser(
        "set-display-option",
        help="Set the display option for pages",
        description=desc,
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    parser.add_argument(
        "--page",
        metavar="NAME",
        help="Page name or displayName to filter (omit for all pages)",
    )
    parser.add_argument(
        "--option",
        required=True,
        choices=["ActualSize", "FitToPage", "FitToWidth"],
        help="Display option to set",
    )
    add_dry_run_arg(parser)
    add_summary_arg(parser)
    parser.set_defaults(func=handle_set_display_option)


def _register_set_page_order(subparsers):
    """Register the set-page-order command."""
    desc = "Set the specific order of pages in the report."

    epilog = textwrap.dedent(
        r"""
        Examples:
          # Set explicit page order
          pbir-utils set-page-order "C:\Reports\MyReport.Report" --order "Home" "Overview" "Details" --dry-run
    """
    )

    parser = subparsers.add_parser(
        "set-page-order",
        help="Set the specific order of pages",
        description=desc,
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder",
    )
    parser.add_argument(
        "--order",
        nargs="+",
        required=True,
        help="List of page names or displayNames in the desired order",
    )
    add_dry_run_arg(parser)
    add_summary_arg(parser)
    parser.set_defaults(func=handle_set_page_order)


def _register_set_active_page(subparsers):
    """Register the set-active-page command."""
    desc = "Set a specific page or the first non-hidden page as active."

    epilog = textwrap.dedent(
        r"""
        Examples:
          # Set first non-hidden page as active
          pbir-utils set-active-page "C:\Reports\MyReport.Report" --dry-run
          
          # Set specific page as active
          pbir-utils set-active-page "C:\Reports\MyReport.Report" --page "Overview"
    """
    )

    parser = subparsers.add_parser(
        "set-active-page",
        help="Set the active page",
        description=desc,
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder",
    )
    parser.add_argument(
        "--page",
        help="Page name or displayName to target. If omitted, sets the first non-hidden page.",
    )
    add_dry_run_arg(parser)
    add_summary_arg(parser)
    parser.set_defaults(func=handle_set_active_page)


# Handlers


def handle_set_display_option(args):
    """Handle the set-display-option command."""
    # Lazy imports to speed up CLI startup
    from ..common import resolve_report_path
    from ..page_utils import set_page_display_option

    report_path = resolve_report_path(args.report_path)
    set_page_display_option(
        report_path,
        display_option=args.option,
        page=args.page,
        dry_run=args.dry_run,
        summary=args.summary,
    )


def handle_set_page_order(args):
    """Handle the set-page-order command."""
    from ..common import resolve_report_path
    from ..page_utils import set_page_order

    report_path = resolve_report_path(args.report_path)
    set_page_order(
        report_path,
        page_order=args.order,
        dry_run=args.dry_run,
        summary=args.summary,
    )


def handle_set_active_page(args):
    """Handle the set-active-page command."""
    from ..common import resolve_report_path
    from ..page_utils import set_active_page

    report_path = resolve_report_path(args.report_path)
    set_active_page(
        report_path,
        page=args.page,
        dry_run=args.dry_run,
        summary=args.summary,
    )
