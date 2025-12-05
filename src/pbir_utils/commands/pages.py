"""Page-related commands for PBIR Utils CLI."""

import argparse
import textwrap

from ..command_utils import (
    add_common_args,
    add_dry_run_arg,
    add_summary_arg,
    add_error_on_change_arg,
    check_error_on_change,
    validate_error_on_change,
)
from ..common import resolve_report_path
from ..page_utils import (
    hide_tooltip_pages,
    hide_drillthrough_pages,
    hide_tooltip_drillthrough_pages,
    set_first_page_as_active,
    remove_empty_pages,
    set_page_size,
)


def register(subparsers):
    """Register page-related commands."""
    _register_hide_tooltip_drillthrough_pages(subparsers)
    _register_set_first_page_as_active(subparsers)
    _register_remove_empty_pages(subparsers)
    _register_hide_tooltip_pages(subparsers)
    _register_hide_drillthrough_pages(subparsers)
    _register_set_page_size(subparsers)


def _register_hide_tooltip_drillthrough_pages(subparsers):
    """Register the hide-tooltip-drillthrough-pages command."""
    hide_tooltip_drillthrough_pages_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils hide-tooltip-drillthrough-pages "C:\\\\Reports\\\\MyReport.Report" --dry-run
    """
    )
    parser = subparsers.add_parser(
        "hide-tooltip-drillthrough-pages",
        help="Hide tooltip and drillthrough pages",
        description="Hide tooltip and drillthrough pages in the report.",
        epilog=hide_tooltip_drillthrough_pages_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_common_args(parser)
    parser.set_defaults(func=handle_hide_tooltip_drillthrough_pages)


def _register_set_first_page_as_active(subparsers):
    """Register the set-first-page-as-active command."""
    set_first_page_as_active_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils set-first-page-as-active "C:\\\\Reports\\\\MyReport.Report" --dry-run
    """
    )
    parser = subparsers.add_parser(
        "set-first-page-as-active",
        help="Set the first page as active",
        description="Set the first page of the report as active.",
        epilog=set_first_page_as_active_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_common_args(parser)
    parser.set_defaults(func=handle_set_first_page_as_active)


def _register_remove_empty_pages(subparsers):
    """Register the remove-empty-pages command."""
    remove_empty_pages_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils remove-empty-pages "C:\\\\Reports\\\\MyReport.Report" --dry-run
    """
    )
    parser = subparsers.add_parser(
        "remove-empty-pages",
        help="Remove empty pages",
        description="Remove empty pages and clean up rogue folders in the report.",
        epilog=remove_empty_pages_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_common_args(parser)
    parser.set_defaults(func=handle_remove_empty_pages)


def _register_hide_tooltip_pages(subparsers):
    """Register the hide-tooltip-pages command."""
    hide_tooltip_pages_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils hide-tooltip-pages "C:\\\\Reports\\\\MyReport.Report" --dry-run
    """
    )
    parser = subparsers.add_parser(
        "hide-tooltip-pages",
        help="Hide tooltip pages",
        description="Hide tooltip pages in the report.",
        epilog=hide_tooltip_pages_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_common_args(parser)
    parser.set_defaults(func=handle_hide_tooltip_pages)


def _register_hide_drillthrough_pages(subparsers):
    """Register the hide-drillthrough-pages command."""
    hide_drillthrough_pages_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils hide-drillthrough-pages "C:\\\\Reports\\\\MyReport.Report" --dry-run
    """
    )
    parser = subparsers.add_parser(
        "hide-drillthrough-pages",
        help="Hide drillthrough pages",
        description="Hide drillthrough pages in the report.",
        epilog=hide_drillthrough_pages_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_common_args(parser)
    parser.set_defaults(func=handle_hide_drillthrough_pages)


def _register_set_page_size(subparsers):
    """Register the set-page-size command."""
    set_page_size_desc = textwrap.dedent(
        """
        Set page size for all non-tooltip pages.
        
        Sets the width and height dimensions for all pages in the report except tooltip pages.
        Tooltip pages retain their original dimensions.
    """
    )
    set_page_size_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils set-page-size "C:\\\\Reports\\\\MyReport.Report" --dry-run
          pbir-utils set-page-size "C:\\\\Reports\\\\MyReport.Report" --width 1920 --height 1080 --dry-run
    """
    )
    parser = subparsers.add_parser(
        "set-page-size",
        help="Set page size for all non-tooltip pages",
        description=set_page_size_desc,
        epilog=set_page_size_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Target page width (default: 1280)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Target page height (default: 720)",
    )
    add_dry_run_arg(parser)
    add_summary_arg(parser)
    add_error_on_change_arg(parser)
    parser.set_defaults(func=handle_set_page_size)


# Handlers


def handle_hide_tooltip_drillthrough_pages(args):
    """Handle the hide-tooltip-drillthrough-pages command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = hide_tooltip_drillthrough_pages(
        report_path, dry_run=args.dry_run, summary=args.summary
    )
    check_error_on_change(args, has_changes, "hide-tooltip-drillthrough-pages")


def handle_set_first_page_as_active(args):
    """Handle the set-first-page-as-active command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = set_first_page_as_active(
        report_path, dry_run=args.dry_run, summary=args.summary
    )
    check_error_on_change(args, has_changes, "set-first-page-as-active")


def handle_remove_empty_pages(args):
    """Handle the remove-empty-pages command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = remove_empty_pages(
        report_path, dry_run=args.dry_run, summary=args.summary
    )
    check_error_on_change(args, has_changes, "remove-empty-pages")


def handle_hide_tooltip_pages(args):
    """Handle the hide-tooltip-pages command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = hide_tooltip_pages(
        report_path, dry_run=args.dry_run, summary=args.summary
    )
    check_error_on_change(args, has_changes, "hide-tooltip-pages")


def handle_hide_drillthrough_pages(args):
    """Handle the hide-drillthrough-pages command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = hide_drillthrough_pages(
        report_path, dry_run=args.dry_run, summary=args.summary
    )
    check_error_on_change(args, has_changes, "hide-drillthrough-pages")


def handle_set_page_size(args):
    """Handle the set-page-size command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = set_page_size(
        report_path,
        width=args.width,
        height=args.height,
        dry_run=args.dry_run,
        summary=args.summary,
    )
    check_error_on_change(args, has_changes, "set-page-size")
