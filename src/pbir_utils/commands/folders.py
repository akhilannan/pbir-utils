"""Folder standardization commands for PBIR Utils CLI."""

import argparse
import textwrap

from ..command_utils import (
    add_common_args,
    check_error_on_change,
    validate_error_on_change,
)
from ..common import resolve_report_path
from ..folder_standardizer import standardize_pbir_folders


def register(subparsers):
    """Register folder-related commands."""
    _register_standardize_folder_names(subparsers)


def _register_standardize_folder_names(subparsers):
    """Register the standardize-folder-names command."""
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
          pbir-utils standardize-folder-names "C:\\\\Reports\\\\MyReport.Report" --dry-run
    """
    )
    parser = subparsers.add_parser(
        "standardize-folder-names",
        help="Standardize page and visual folder names",
        description=standardize_folders_desc,
        epilog=standardize_folders_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_common_args(parser)
    parser.set_defaults(func=handle_standardize_folder_names)


def handle_standardize_folder_names(args):
    """Handle the standardize-folder-names command."""
    validate_error_on_change(args)
    report_path = resolve_report_path(args.report_path)
    has_changes = standardize_pbir_folders(
        report_path, dry_run=args.dry_run, summary=args.summary
    )
    check_error_on_change(args, has_changes, "standardize-folder-names")
