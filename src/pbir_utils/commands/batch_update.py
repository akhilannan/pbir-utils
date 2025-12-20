"""Batch update command for PBIR Utils CLI."""

import argparse
import textwrap

from ..command_utils import (
    add_dry_run_arg,
)


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
        r"""
        Examples:
          pbir-utils batch-update "C:\PBIR\Project" "C:\Mapping.csv" --dry-run
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
    parser.set_defaults(func=handle)


def handle(args):
    """Handle the batch-update command."""
    # Lazy import to speed up CLI startup
    from ..pbir_processor import batch_update_pbir_project

    batch_update_pbir_project(args.directory_path, args.csv_path, dry_run=args.dry_run)
