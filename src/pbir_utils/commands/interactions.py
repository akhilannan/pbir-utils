"""Disable interactions command for PBIR Utils CLI."""

import argparse
import textwrap

from ..command_utils import (
    add_dry_run_arg,
    add_summary_arg,
)


def register(subparsers):
    """Register the disable-interactions command."""
    disable_interactions_desc = textwrap.dedent(
        """
        Disable visual interactions.
        
        Disables interactions between visuals based on source/target parameters.
        
        Behavior:
          - If only `report_path` is provided, disables interactions between ALL visuals on ALL pages.
          - If `pages` is provided, limits scope to those pages.
          - If source/target visuals are specified, limits scope to those interactions.
        
        Update Types:
          - Upsert: Disables any existing interactions that match the specified source/target parameters and inserts new combinations. Interactions not part of the specified source/target parameters will remain unchanged. (Default)
          - Insert: Inserts new interactions based on the source/target parameters without modifying existing interactions.
          - Overwrite: Replaces all existing interactions with the new ones that match the specified source/target parameters, removing any interactions not part of the new configuration.
    """
    )
    disable_interactions_epilog = textwrap.dedent(
        r"""
        Examples:
          pbir-utils disable-interactions "C:\Reports\MyReport.Report" --dry-run
          pbir-utils disable-interactions "C:\Reports\MyReport.Report" --pages "Overview" --source-visual-types slicer
    """
    )
    parser = subparsers.add_parser(
        "disable-interactions",
        help="Disable visual interactions",
        description=disable_interactions_desc,
        epilog=disable_interactions_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    parser.add_argument("--pages", nargs="+", help="List of page names to process")
    parser.add_argument(
        "--source-visual-ids", nargs="+", help="List of source visual IDs"
    )
    parser.add_argument(
        "--source-visual-types", nargs="+", help="List of source visual types"
    )
    parser.add_argument(
        "--target-visual-ids", nargs="+", help="List of target visual IDs"
    )
    parser.add_argument(
        "--target-visual-types", nargs="+", help="List of target visual types"
    )
    parser.add_argument(
        "--update-type",
        default="Upsert",
        choices=["Upsert", "Insert", "Overwrite"],
        help="Update type (Upsert, Insert, Overwrite)",
    )
    add_dry_run_arg(parser)
    add_summary_arg(parser)
    parser.set_defaults(func=handle)


def handle(args):
    """Handle the disable-interactions command."""
    # Lazy imports to speed up CLI startup
    from ..common import resolve_report_path
    from ..visual_interactions_utils import disable_visual_interactions

    report_path = resolve_report_path(args.report_path)
    disable_visual_interactions(
        report_path,
        pages=args.pages,
        source_visual_ids=args.source_visual_ids,
        source_visual_types=args.source_visual_types,
        target_visual_ids=args.target_visual_ids,
        target_visual_types=args.target_visual_types,
        update_type=args.update_type,
        dry_run=args.dry_run,
        summary=args.summary,
    )
