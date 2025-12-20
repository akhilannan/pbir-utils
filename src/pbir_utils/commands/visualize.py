"""Visualize command for PBIR Utils CLI."""

import argparse
import textwrap

from ..common import resolve_report_path


def register(subparsers):
    """Register the visualize command."""
    visualize_desc = textwrap.dedent(
        """
        Display report wireframes using Dash and Plotly.
        
        Visualizes the layout of pages and their visual components.
        
        Behavior:
        The `pages`, `visual_types`, and `visual_ids` parameters work with an AND logic, 
        meaning that only visuals matching ALL specified criteria will be shown.
    """
    )
    visualize_epilog = textwrap.dedent(
        r"""
        Examples:
          pbir-utils visualize "C:\Reports\MyReport.Report"
          pbir-utils visualize "C:\Reports\MyReport.Report" --pages "Overview" "Detail" --visual-types slicer
    """
    )
    parser = subparsers.add_parser(
        "visualize",
        help="Display report wireframes",
        description=visualize_desc,
        epilog=visualize_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    parser.add_argument(
        "--pages", nargs="+", help="List of page ids or displayNames to include"
    )
    parser.add_argument(
        "--visual-types", nargs="+", help="List of visual types to include"
    )
    parser.add_argument("--visual-ids", nargs="+", help="List of visual IDs to include")
    parser.add_argument(
        "--no-show-hidden",
        action="store_false",
        dest="show_hidden",
        help="Do not show hidden visuals (default: show them)",
    )
    parser.set_defaults(show_hidden=True, func=handle)


def handle(args):
    """Handle the visualize command."""
    # Lazy import to avoid loading heavy dash/plotly dependencies at CLI startup
    from ..report_wireframe_visualizer import display_report_wireframes

    report_path = resolve_report_path(args.report_path)
    display_report_wireframes(
        report_path,
        pages=args.pages,
        visual_types=args.visual_types,
        visual_ids=args.visual_ids,
        show_hidden=args.show_hidden,
    )
