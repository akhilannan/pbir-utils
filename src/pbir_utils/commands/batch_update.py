"""Batch update command for PBIR Utils CLI."""

import argparse
import textwrap

from ..command_utils import (
    add_dry_run_arg,
    add_error_on_change_arg,
    check_error_on_change,
    validate_error_on_change,
)
from ..pbir_processor import batch_update_pbir_project


def register(subparsers):
    """Register the batch-update command."""
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
          pbir-utils batch-update "C:\\\\PBIR\\\\Project" "C:\\\\Mapping.csv" --dry-run
    """
    )
    parser = subparsers.add_parser(
        "batch-update",
        help="Batch update attributes in PBIR project",
        description=batch_update_desc,
        epilog=batch_update_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "directory_path", help="Path to the root directory of the PBIR project"
    )
    parser.add_argument("csv_path", help="Path to the Attribute_Mapping.csv file")
    add_dry_run_arg(parser)
    add_error_on_change_arg(parser)
    parser.set_defaults(func=handle)


def handle(args):
    """Handle the batch-update command."""
    validate_error_on_change(args)
    has_changes = batch_update_pbir_project(
        args.directory_path, args.csv_path, dry_run=args.dry_run
    )
    check_error_on_change(args, has_changes, "batch-update")
