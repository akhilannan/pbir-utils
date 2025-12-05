"""Shared CLI argument helpers and validation utilities."""

import argparse
import json
import sys
from typing import Dict, Set, Optional

from .console_utils import console


def parse_filters(filters_str: str) -> Optional[Dict[str, Set[str]]]:
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


def add_error_on_change_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --error-on-change argument."""
    parser.add_argument(
        "--error-on-change",
        action="store_true",
        help="Exit with error code 1 if changes would be made during dry run. Only valid with --dry-run.",
    )


def add_common_args(
    parser: argparse.ArgumentParser,
    include_report_path: bool = True,
    include_summary: bool = True,
    include_error_on_change: bool = True,
) -> None:
    """
    Add common CLI arguments to a parser.

    Args:
        parser: The argument parser to add arguments to.
        include_report_path: Whether to add the report_path argument.
        include_summary: Whether to add the --summary argument.
        include_error_on_change: Whether to add the --error-on-change argument.
    """
    if include_report_path:
        add_report_path_arg(parser)
    add_dry_run_arg(parser)
    if include_summary:
        add_summary_arg(parser)
    if include_error_on_change:
        add_error_on_change_arg(parser)


def validate_error_on_change(args) -> None:
    """
    Validate that --error-on-change requires --dry-run.
    Call this at the start of command handlers that support --error-on-change.
    """
    if getattr(args, "error_on_change", False) and not args.dry_run:
        console.print_error("--error-on-change requires --dry-run to be specified.")
        sys.exit(1)


def check_error_on_change(args, has_changes: bool, command_name: str):
    """
    Check if --error-on-change is specified and if changes would be made.
    Exits with code 1 if validation fails.

    Args:
        args: Parsed command line arguments.
        has_changes: Whether changes were made (or would be made in dry run).
        command_name: Name of the command for error messages.
    """
    error_on_change = getattr(args, "error_on_change", False)
    if error_on_change:
        if not args.dry_run:
            console.print_error("--error-on-change requires --dry-run to be specified.")
            sys.exit(1)
        if has_changes:
            console.print_error(f"Error: {command_name} would make changes.")
            console.print_error("Build failed due to --error-on-change policy.")
            sys.exit(1)
