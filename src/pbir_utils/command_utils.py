"""Shared CLI argument helpers and validation utilities."""

import argparse
import json
import sys
from typing import Optional

from .console_utils import console


def parse_filters(filters_str: str) -> dict[str, set[str]] | None:
    """Parse a JSON string into a filters dictionary."""
    if not filters_str:
        return None
    try:
        data = json.loads(filters_str)
        if not isinstance(data, dict):
            raise ValueError("Filters must be a JSON object.")
        # Convert lists to sets
        return {k: set(v) if isinstance(v, list) else set([v]) for k, v in data.items()}
    except json.JSONDecodeError:
        console.print_error(f"Invalid JSON string for filters: {filters_str}")
        sys.exit(1)
    except Exception as e:
        console.print_error(f"Parsing filters: {e}")
        sys.exit(1)


def parse_json_arg(json_str: Optional[str], arg_name: str):
    """Parse an optional JSON string argument."""
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        console.print_error(f"Invalid JSON string for {arg_name}: {json_str}")
        sys.exit(1)


# =============================================================================
# CLI Argument Helpers - Consolidate common argument patterns
# =============================================================================


def add_report_path_arg(parser: argparse.ArgumentParser) -> None:
    """Add the standard optional report_path argument."""
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )


def add_dry_run_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --dry-run argument."""
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )


def add_summary_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --summary argument."""
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of detailed messages",
    )


def add_common_args(
    parser: argparse.ArgumentParser,
    include_report_path: bool = True,
    include_summary: bool = True,
) -> None:
    """
    Add common CLI arguments to a parser.

    Args:
        parser: The argument parser to add arguments to.
        include_report_path: Whether to add the report_path argument.
        include_summary: Whether to add the --summary argument.
    """
    if include_report_path:
        add_report_path_arg(parser)
    add_dry_run_arg(parser)
    if include_summary:
        add_summary_arg(parser)
