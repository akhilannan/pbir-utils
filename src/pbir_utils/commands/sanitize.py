"""Sanitize command for PBIR Utils CLI."""

import argparse
import textwrap

from ..command_utils import add_dry_run_arg, add_summary_arg
from ..common import resolve_report_path
from ..console_utils import console
from ..pbir_report_sanitizer import (
    sanitize_powerbi_report,
    get_available_actions,
    get_simple_actions,
)
from ..sanitize_config import load_config, get_default_config_path, _load_yaml
import sys


def register(subparsers):
    """Register the sanitize command."""
    # Build description dynamically
    default_config = _load_yaml(get_default_config_path())
    default_action_names = [
        a if isinstance(a, str) else a.get("name", "")
        for a in default_config.get("actions", [])
    ]

    # Get simple-signature actions for display (not parameterized ones)
    simple_actions = get_simple_actions()

    # Calculate additional actions (not in defaults, only simple signature)
    additional_action_names = [
        a for a in simple_actions.keys() if a not in default_action_names
    ]

    # Build dynamic description
    default_actions_list = "\n".join(
        f"          - {name}" for name in default_action_names
    )
    additional_actions_list = "\n".join(
        f"          - {name}" for name in sorted(additional_action_names)
    )

    sanitize_desc = f"""
        Sanitize a Power BI report by removing unused or unwanted components.
        
        If no --actions specified, runs actions from config file (defaults/sanitize.yaml).
        
        Default Actions (from config):
{default_actions_list}
        
        Additional Actions (not in defaults):
{additional_actions_list}
        
        Configuration:
          Create a 'pbir-sanitize.yaml' in your project to customize defaults.
    """

    sanitize_epilog = textwrap.dedent(
        """
        Examples:
          # Run default actions from config (--actions all is optional)
          pbir-utils sanitize "C:\\\\Reports\\\\MyReport.Report" --dry-run
          
          # Run specific actions only
          pbir-utils sanitize "C:\\\\Reports\\\\MyReport.Report" --actions remove_unused_measures --dry-run
          
          # Exclude specific actions from defaults
          pbir-utils sanitize "C:\\\\Reports\\\\MyReport.Report" --exclude set_first_page_as_active --dry-run
          
          # Include additional actions beyond defaults
          pbir-utils sanitize "C:\\\\Reports\\\\MyReport.Report" --include standardize_pbir_folders --dry-run
    """
    )

    parser = subparsers.add_parser(
        "sanitize",
        help="Sanitize a Power BI report",
        description=sanitize_desc,
        epilog=sanitize_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    parser.add_argument(
        "--actions",
        nargs="+",
        help="Actions to perform. If omitted, runs config defaults. Use 'all' explicitly if preferred.",
    )
    add_dry_run_arg(parser)
    add_summary_arg(parser)
    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="ACTION",
        help="Actions to exclude from config defaults.",
    )
    parser.add_argument(
        "--include",
        nargs="+",
        metavar="ACTION",
        help="Additional actions to include beyond config defaults.",
    )
    parser.add_argument(
        "--error-on-change",
        nargs="+",
        metavar="ACTION",
        help="Exit with error code 1 if specified actions would make changes during dry run. Only valid with --dry-run.",
    )
    parser.set_defaults(func=handle)


def handle(args):
    """Handle the sanitize command."""
    report_path = resolve_report_path(args.report_path)
    actions = args.actions if args.actions else []

    # If no actions specified or "all", load from config
    if not actions or "all" in actions:
        config = load_config(report_path=report_path)
        config_actions = [a.name for a in config.actions]

        if "all" in actions:
            # "all" means all actions from config file
            actions = config_actions
        else:
            # No actions specified, use config defaults
            actions = config_actions

        # Apply exclusions if specified
        if args.exclude:
            available = get_available_actions()
            invalid_excludes = [e for e in args.exclude if e not in available]
            if invalid_excludes:
                console.print_warning(
                    f"Unknown actions in --exclude will be ignored: {', '.join(invalid_excludes)}"
                )
            actions = [a for a in actions if a not in args.exclude]

        # Apply inclusions if specified (add actions not in config)
        if args.include:
            available = get_available_actions()
            for inc in args.include:
                if inc not in available:
                    console.print_warning(f"Unknown action in --include: '{inc}'")
                elif inc not in actions:
                    actions.append(inc)
    else:
        # Specific actions provided - validate they exist
        available = get_available_actions()
        for action in actions:
            if action not in available:
                console.print_warning(f"Unknown action '{action}' will be skipped.")

    if not actions:
        console.print_warning(
            "No actions to run. Check your config file or use --actions to specify sanitization actions."
        )

    # Validate --error-on-change requires --dry-run
    error_on_change = args.error_on_change if hasattr(args, "error_on_change") else None
    if error_on_change and not args.dry_run:
        console.print_error("--error-on-change requires --dry-run to be specified.")
        sys.exit(1)

    # Run sanitization and get results
    results = sanitize_powerbi_report(
        report_path, actions, dry_run=args.dry_run, summary=args.summary
    )

    # Check if any error_on_change actions would make changes
    if error_on_change:
        actions_with_changes = [
            action
            for action in error_on_change
            if action in results and results[action]
        ]
        if actions_with_changes:
            console.print_error(
                f"Error: The following checks would make changes: {', '.join(actions_with_changes)}"
            )
            console.print_error("Build failed due to --error-on-change policy.")
            sys.exit(1)
