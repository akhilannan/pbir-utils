"""Visual-related commands for PBIR Utils CLI."""

import argparse
import textwrap

from ..command_utils import (
    add_common_args,
    check_error_on_change,
    validate_error_on_change,
)
from ..common import resolve_report_path
from ..visual_utils import (
    remove_unused_custom_visuals,
    disable_show_items_with_no_data,
    remove_hidden_visuals_never_shown,
)


def register(subparsers):
    """Register visual-related commands."""
    _register_remove_unused_custom_visuals(subparsers)
    _register_disable_show_items_with_no_data(subparsers)
    _register_remove_hidden_visuals(subparsers)


def _register_remove_unused_custom_visuals(subparsers):
    """Register the remove-unused-custom-visuals command."""
    remove_unused_custom_visuals_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils remove-unused-custom-visuals "C:\\\\Reports\\\\MyReport.Report" --dry-run
    """
    )
    parser = subparsers.add_parser(
        "remove-unused-custom-visuals",
        help="Remove unused custom visuals",
        description="Remove unused custom visuals from the report.",
        epilog=remove_unused_custom_visuals_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_common_args(parser)
    parser.set_defaults(func=handle_remove_unused_custom_visuals)


def _register_disable_show_items_with_no_data(subparsers):
    """Register the disable-show-items-with-no-data command."""
    disable_show_items_with_no_data_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils disable-show-items-with-no-data "C:\\\\Reports\\\\MyReport.Report" --dry-run
    """
    )
    parser = subparsers.add_parser(
        "disable-show-items-with-no-data",
        help="Disable 'Show items with no data'",
        description="Disable the 'Show items with no data' option for visuals.",
        epilog=disable_show_items_with_no_data_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_common_args(parser)
    parser.set_defaults(func=handle_disable_show_items_with_no_data)


def _register_remove_hidden_visuals(subparsers):
    """Register the remove-hidden-visuals command."""
    remove_hidden_visuals_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils remove-hidden-visuals "C:\\\\Reports\\\\MyReport.Report" --dry-run
    """
    )
    parser = subparsers.add_parser(
        "remove-hidden-visuals",
        help="Remove hidden visuals never shown",
        description="Remove hidden visuals that are never shown using bookmarks.",
        epilog=remove_hidden_visuals_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_common_args(parser)
    parser.set_defaults(func=handle_remove_hidden_visuals)


# Handlers


def handle_remove_unused_custom_visuals(args):
    """Handle the remove-unused-custom-visuals command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = remove_unused_custom_visuals(
        report_path, dry_run=args.dry_run, summary=args.summary
    )
    check_error_on_change(args, has_changes, "remove-unused-custom-visuals")


def handle_disable_show_items_with_no_data(args):
    """Handle the disable-show-items-with-no-data command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = disable_show_items_with_no_data(
        report_path, dry_run=args.dry_run, summary=args.summary
    )
    check_error_on_change(args, has_changes, "disable-show-items-with-no-data")


def handle_remove_hidden_visuals(args):
    """Handle the remove-hidden-visuals command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = remove_hidden_visuals_never_shown(
        report_path, dry_run=args.dry_run, summary=args.summary
    )
    check_error_on_change(args, has_changes, "remove-hidden-visuals")
