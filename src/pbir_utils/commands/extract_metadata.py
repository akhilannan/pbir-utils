"""Extract metadata command for PBIR Utils CLI."""

import argparse
import sys
import textwrap

from ..command_utils import parse_filters
from ..console_utils import console


def register(subparsers):
    """Register the extract-metadata command."""
    extract_desc = textwrap.dedent(
        """
        Export attribute metadata from PBIR to CSV.
        
        Extracts detailed information about tables, columns, measures, DAX expressions, and usage contexts.
        Use --visuals-only to export visual-level metadata instead.
        
        If no output path is specified, creates metadata.csv (or visuals.csv with --visuals-only) in the report folder.
    """
    )
    extract_epilog = textwrap.dedent(
        r"""
        Examples:
          pbir-utils extract-metadata "C:\Reports\MyReport.Report"
          pbir-utils extract-metadata "C:\Reports\MyReport.Report" --visuals-only
          pbir-utils extract-metadata "C:\Reports\MyReport.Report" "C:\Output\custom.csv"
          pbir-utils extract-metadata "C:\Reports\MyReport.Report" --filters '{"Page Name": ["Overview"]}'
    """
    )
    parser = subparsers.add_parser(
        "extract-metadata",
        help="Extract metadata to CSV",
        description=extract_desc,
        epilog=extract_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "args",
        nargs="*",
        help="[report_path] [output_path] (both optional if inside a .Report folder)",
    )
    parser.add_argument(
        "--filters",
        help='JSON string representing filters (e.g., \'{"Page Name": ["Page1"]}\').',
    )
    parser.add_argument(
        "--visuals-only",
        action="store_true",
        help="Extract visual-level metadata instead of attribute usage.",
    )
    parser.set_defaults(func=handle)


def handle(args):
    """Handle the extract-metadata command."""
    # Lazy imports to speed up CLI startup
    from ..common import resolve_report_path
    from ..metadata_extractor import export_pbir_metadata_to_csv

    cmd_args = args.args
    report_path = None
    output_path = None

    if len(cmd_args) == 0:
        # No args - resolve report path from CWD, use default output
        report_path = resolve_report_path(None)
    elif len(cmd_args) == 1:
        if cmd_args[0].lower().endswith(".csv"):
            # Single arg is CSV - resolve report path from CWD
            report_path = resolve_report_path(None)
            output_path = cmd_args[0]
        else:
            # Single arg is report path - use default output
            report_path = cmd_args[0]
    elif len(cmd_args) == 2:
        report_path = cmd_args[0]
        output_path = cmd_args[1]
    else:
        console.print_error("Too many arguments.")
        sys.exit(1)
        return

    filters = parse_filters(args.filters)
    export_pbir_metadata_to_csv(
        report_path, output_path, filters=filters, visuals_only=args.visuals_only
    )
