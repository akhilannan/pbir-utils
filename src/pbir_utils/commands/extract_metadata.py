"""Extract metadata command for PBIR Utils CLI."""

__all__ = ["register", "handle"]

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
          pbir-utils extract-metadata "C:\Reports\MyReport.Report" --pages "Overview" "Detail"
          pbir-utils extract-metadata "C:\Reports" --reports "Report1" "Report2"
          pbir-utils extract-metadata "C:\Reports\MyReport.Report" --visuals-only --visual-types slicer card
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
        "--pages",
        nargs="+",
        help="Filter by page displayName(s)",
    )
    parser.add_argument(
        "--reports",
        nargs="+",
        help="Filter by report name(s) (when path is a directory containing multiple reports)",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        help="Filter by table name(s)",
    )
    parser.add_argument(
        "--visual-types",
        nargs="+",
        help="Filter by visual type(s) (for --visuals-only mode)",
    )
    parser.add_argument(
        "--visual-ids",
        nargs="+",
        help="Filter by visual ID(s) (for --visuals-only mode)",
    )
    parser.add_argument(
        "--visuals-only",
        action="store_true",
        help="Extract visual-level metadata instead of attribute usage.",
    )
    parser.add_argument(
        "--filters",
        help="[Deprecated] JSON string representing filters. Use --pages, --reports, etc. instead.",
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

    # Build filters from legacy --filters and/or new explicit arguments
    filters = parse_filters(args.filters) if args.filters else {}
    if args.pages:
        filters["Page Name"] = set(args.pages)
    if args.reports:
        filters["Report"] = set(args.reports)
    if args.tables:
        filters["Table"] = set(args.tables)
    if getattr(args, "visual_types", None):
        filters["Visual Type"] = set(args.visual_types)
    if getattr(args, "visual_ids", None):
        filters["Visual ID"] = set(args.visual_ids)

    export_pbir_metadata_to_csv(
        report_path,
        output_path,
        filters=filters or None,
        visuals_only=args.visuals_only,
    )
