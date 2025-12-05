"""Bookmark-related commands for PBIR Utils CLI."""

import argparse
import textwrap

from ..command_utils import (
    add_common_args,
    check_error_on_change,
    validate_error_on_change,
)
from ..common import resolve_report_path
from ..bookmark_utils import remove_unused_bookmarks, cleanup_invalid_bookmarks


def register(subparsers):
    """Register bookmark-related commands."""
    _register_remove_unused_bookmarks(subparsers)
    _register_cleanup_invalid_bookmarks(subparsers)


def _register_remove_unused_bookmarks(subparsers):
    """Register the remove-unused-bookmarks command."""
    remove_unused_bookmarks_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils remove-unused-bookmarks "C:\\\\Reports\\\\MyReport.Report" --dry-run
    """
    )
    parser = subparsers.add_parser(
        "remove-unused-bookmarks",
        help="Remove unused bookmarks",
        description="Remove bookmarks which are not activated in report using bookmark navigator or actions.",
        epilog=remove_unused_bookmarks_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_common_args(parser)
    parser.set_defaults(func=handle_remove_unused_bookmarks)


def _register_cleanup_invalid_bookmarks(subparsers):
    """Register the cleanup-invalid-bookmarks command."""
    cleanup_invalid_bookmarks_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils cleanup-invalid-bookmarks "C:\\\\Reports\\\\MyReport.Report" --dry-run
    """
    )
    parser = subparsers.add_parser(
        "cleanup-invalid-bookmarks",
        help="Cleanup invalid bookmarks",
        description="Clean up invalid bookmarks that reference non-existent pages or visuals.",
        epilog=cleanup_invalid_bookmarks_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_common_args(parser)
    parser.set_defaults(func=handle_cleanup_invalid_bookmarks)


# Handlers


def handle_remove_unused_bookmarks(args):
    """Handle the remove-unused-bookmarks command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = remove_unused_bookmarks(
        report_path, dry_run=args.dry_run, summary=args.summary
    )
    check_error_on_change(args, has_changes, "remove-unused-bookmarks")


def handle_cleanup_invalid_bookmarks(args):
    """Handle the cleanup-invalid-bookmarks command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = cleanup_invalid_bookmarks(
        report_path, dry_run=args.dry_run, summary=args.summary
    )
    check_error_on_change(args, has_changes, "cleanup-invalid-bookmarks")
