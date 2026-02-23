"""Theme-related commands for PBIR Utils CLI."""

__all__ = ["register", "handle_set_theme", "handle_reset_colors"]

import argparse
import textwrap

from ..command_utils import (
    add_dry_run_arg,
    add_summary_arg,
)


def register(subparsers):
    """Register theme-related commands."""
    _register_set_theme(subparsers)
    _register_reset_colors(subparsers)


def _register_set_theme(subparsers):
    """Register the set-theme command."""
    desc = "Apply a theme JSON to the report."

    epilog = textwrap.dedent(
        r"""
        Examples:
          # Set report theme
          pbir-utils set-theme "C:\Reports\MyReport.Report" --theme-file "C:\Themes\Corporate.json"
    """
    )

    parser = subparsers.add_parser(
        "set-theme",
        help="Apply a theme JSON to the report",
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
        "--theme-file",
        required=True,
        help="Path to the theme component JSON file to apply",
    )
    add_dry_run_arg(parser)
    add_summary_arg(parser)
    parser.set_defaults(func=handle_set_theme)


def _register_reset_colors(subparsers):
    """Register the reset-colors command."""
    desc = "Remove hardcoded hex colors from visuals to fall back to theme colors."

    epilog = textwrap.dedent(
        r"""
        Examples:
          # Reset all colors in a report
          pbir-utils reset-colors "C:\Reports\MyReport.Report"
          
          # Reset colors only on specific pages
          pbir-utils reset-colors "C:\Reports\MyReport.Report" --pages "Sales" "Marketing"
          
          # Reset colors only for specific visual types
          pbir-utils reset-colors "C:\Reports\MyReport.Report" --visual-types lineChart columnChart
    """
    )

    parser = subparsers.add_parser(
        "reset-colors",
        help="Remove hardcoded colors from visuals",
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
        "--pages", nargs="+", help="List of page names or display names to process"
    )
    parser.add_argument(
        "--visual-types", nargs="+", help="List of visual types to process"
    )
    parser.add_argument("--visual-ids", nargs="+", help="List of visual IDs to process")

    add_dry_run_arg(parser)
    add_summary_arg(parser)
    parser.set_defaults(func=handle_reset_colors)


# Handlers


def handle_set_theme(args):
    """Handle the set-theme command."""
    from ..common import resolve_report_path
    from ..theme_utils import set_theme

    report_path = resolve_report_path(args.report_path)
    set_theme(
        report_path,
        theme_path=args.theme_file,
        dry_run=args.dry_run,
        summary=args.summary,
    )


def handle_reset_colors(args):
    """Handle the reset-colors command."""
    from ..common import resolve_report_path
    from ..theme_utils import reset_hardcoded_colors

    report_path = resolve_report_path(args.report_path)
    reset_hardcoded_colors(
        report_path,
        pages=args.pages,
        visual_types=args.visual_types,
        visual_ids=args.visual_ids,
        dry_run=args.dry_run,
        summary=args.summary,
    )
