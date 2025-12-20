"""Measure-related commands for PBIR Utils CLI."""

import argparse
import textwrap

from ..command_utils import (
    add_dry_run_arg,
    add_summary_arg,
)


def register(subparsers):
    """Register measure-related commands."""
    _register_remove_measures(subparsers)
    _register_measure_dependencies(subparsers)


def _register_remove_measures(subparsers):
    """Register the remove-measures command."""
    remove_measures_desc = textwrap.dedent(
        """
        Remove report level measures.
        
        Scans through a Power BI PBIR Report and removes report-level measures.
        Can remove all measures or a specified list of measures.
        
        Visual Usage Check:
          - If enabled (default), only removes a measure if neither the measure itself 
            nor any of its dependent measures are used in any visuals.
    """
    )
    remove_measures_epilog = textwrap.dedent(
        r"""
        Examples:
          pbir-utils remove-measures "C:\Reports\MyReport.Report" --dry-run
          pbir-utils remove-measures "C:\Reports\MyReport.Report" --measure-names "Measure1" "Measure2" --no-check-usage
    """
    )
    parser = subparsers.add_parser(
        "remove-measures",
        help="Remove report level measures",
        description=remove_measures_desc,
        epilog=remove_measures_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    parser.add_argument(
        "--measure-names",
        nargs="+",
        help="List of measure names to remove (default: all measures)",
    )
    parser.add_argument(
        "--no-check-usage",
        action="store_false",
        dest="check_visual_usage",
        help="Do not check visual usage before removing (default: check usage)",
    )
    parser.set_defaults(check_visual_usage=True)
    add_dry_run_arg(parser)
    add_summary_arg(parser)
    parser.set_defaults(func=handle_remove_measures)


def _register_measure_dependencies(subparsers):
    """Register the measure-dependencies command."""
    measure_deps_desc = textwrap.dedent(
        """
        Generate measure dependencies report.
        
        Generates a dependency tree for measures, focusing on measures that depend on other measures.
    """
    )
    measure_deps_epilog = textwrap.dedent(
        r"""
        Examples:
          pbir-utils measure-dependencies "C:\Reports\MyReport.Report"
          pbir-utils measure-dependencies "C:\Reports\MyReport.Report" --measure-names "Total Sales" --include-visual-ids
    """
    )
    parser = subparsers.add_parser(
        "measure-dependencies",
        help="Generate measure dependencies report",
        description=measure_deps_desc,
        epilog=measure_deps_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    parser.add_argument(
        "--measure-names",
        nargs="+",
        help="List of measure names to analyze (default: all measures)",
    )
    parser.add_argument(
        "--include-visual-ids",
        action="store_true",
        help="Include visual IDs that use each measure in the output",
    )
    parser.set_defaults(func=handle_measure_dependencies)


def handle_remove_measures(args):
    """Handle the remove-measures command."""
    # Lazy imports to speed up CLI startup
    from ..common import resolve_report_path
    from ..pbir_measure_utils import remove_measures

    report_path = resolve_report_path(args.report_path)
    remove_measures(
        report_path,
        measure_names=args.measure_names,
        check_visual_usage=args.check_visual_usage,
        dry_run=args.dry_run,
        summary=args.summary,
    )


def handle_measure_dependencies(args):
    """Handle the measure-dependencies command."""
    # Lazy imports to speed up CLI startup
    from ..common import resolve_report_path
    from ..pbir_measure_utils import generate_measure_dependencies_report

    report_path = resolve_report_path(args.report_path)
    report = generate_measure_dependencies_report(
        report_path,
        measure_names=args.measure_names,
        include_visual_ids=args.include_visual_ids,
    )
    print(report)
