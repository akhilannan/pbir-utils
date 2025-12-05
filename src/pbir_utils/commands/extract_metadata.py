"""Extract metadata command for PBIR Utils CLI."""

import argparse
import sys
import textwrap

from ..command_utils import parse_filters
from ..common import resolve_report_path
from ..console_utils import console
from ..metadata_extractor import export_pbir_metadata_to_csv


def register(subparsers):
    """Register the extract-metadata command."""
    extract_desc = textwrap.dedent(
        """
        Export attribute metadata from PBIR to CSV.
        
        Extracts detailed information about tables, columns, measures, DAX expressions, and usage contexts.
    """
    )
    extract_epilog = textwrap.dedent(
        """
        Examples:
          pbir-utils extract-metadata "C:\\\\Reports\\\\MyReport.Report" "C:\\\\Output\\\\metadata.csv"
          pbir-utils extract-metadata "C:\\\\Reports" "C:\\\\Output\\\\all_metadata.csv" --filters '{"Page Name": ["Overview"]}'
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
        help="[report_path] output_path. If 1 arg provided and it ends in .csv, it is treated as output_path and report_path is inferred.",
    )
    parser.add_argument(
        "--filters",
        help='JSON string representing filters (e.g., \'{"Page Name": ["Page1"]}\').',
    )
    parser.set_defaults(func=handle)


def handle(args):
    """Handle the extract-metadata command."""
    cmd_args = args.args
    report_path = None
    output_path = None

    if len(cmd_args) == 0:
        console.print_error("Output path required.")
        sys.exit(1)
    elif len(cmd_args) == 1:
        if cmd_args[0].lower().endswith(".csv"):
            report_path = resolve_report_path(None)
            output_path = cmd_args[0]
        else:
            report_path = cmd_args[0]
            console.print_error("Output path required.")
            sys.exit(1)
    elif len(cmd_args) == 2:
        report_path = cmd_args[0]
        output_path = cmd_args[1]
    else:
        console.print_error("Too many arguments.")
        sys.exit(1)

    filters = parse_filters(args.filters)
    export_pbir_metadata_to_csv(report_path, output_path, filters=filters)
