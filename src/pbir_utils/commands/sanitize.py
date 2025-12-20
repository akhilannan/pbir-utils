"""Sanitize command for PBIR Utils CLI."""

import argparse
import textwrap

from ..command_utils import add_dry_run_arg, add_summary_arg
from ..console_utils import console
from ..sanitize_config import get_default_config_path, _load_yaml


def register(subparsers):
    """Register the sanitize command."""
    # Build description dynamically from defaults/sanitize.yaml
    default_config = _load_yaml(get_default_config_path())

    # Get default action names
    default_action_names = [
        a if isinstance(a, str) else a.get("name", "")
        for a in default_config.get("actions", [])
    ]

    # Get all defined actions (keys in definitions)
    all_defined = set(default_config.get("definitions", {}).keys())

    # Additional actions = defined but not in defaults
    additional_action_names = sorted(all_defined - set(default_action_names))

    # Build dynamic description
    default_actions_list = "\n".join(
        f"          - {name}" for name in default_action_names
    )
    additional_actions_list = "\n".join(
        f"          - {name}" for name in additional_action_names
    )

    sanitize_desc = f"""
        Sanitize a Power BI report by removing unused or unwanted components.
        
        If no --actions specified, runs actions from config file (defaults/sanitize.yaml).
        
        Default Actions (from config):
{default_actions_list}
        
        Additional Actions (opt-in via --include):
{additional_actions_list}
        
        Configuration:
          Create a 'pbir-sanitize.yaml' in your project to customize defaults.
          Or use --config to specify a custom config file path.
    """

    sanitize_epilog = textwrap.dedent(
        r"""
        Examples:
          # Run default actions from config
          pbir-utils sanitize "C:\Reports\MyReport.Report" --dry-run
          
          # Run specific actions only
          pbir-utils sanitize "C:\Reports\MyReport.Report" --actions remove_unused_measures --dry-run
          
          # Exclude specific actions from defaults
          pbir-utils sanitize "C:\Reports\MyReport.Report" --exclude set_first_page_as_active --dry-run
          
          # Include additional actions beyond defaults
          pbir-utils sanitize "C:\Reports\MyReport.Report" --include standardize_pbir_folders --dry-run
          
          # Use a custom config file
          pbir-utils sanitize "C:\Reports\MyReport.Report" --config my-config.yaml --dry-run
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
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to a custom sanitize config YAML file.",
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
    parser.set_defaults(func=handle)


def handle(args):
    """Handle the sanitize command."""
    # Lazy imports to speed up CLI startup
    from ..common import resolve_report_path
    from ..pbir_report_sanitizer import sanitize_powerbi_report
    from ..sanitize_config import load_config

    report_path = resolve_report_path(args.report_path)

    # Load config (from explicit path or auto-discover)
    config = load_config(config_path=args.config, report_path=report_path)

    # Determine final action list
    if args.actions and "all" not in args.actions:
        # Specific actions requested - filter to those
        requested_actions = args.actions
        final_action_names = []
        for action_name in requested_actions:
            if action_name in config.definitions:
                final_action_names.append(action_name)
            else:
                console.print_warning(
                    f"Unknown action '{action_name}' will be skipped."
                )
        actions = final_action_names
    else:
        # Use config defaults
        actions = config.get_action_names()

    # Apply exclusions
    if args.exclude:
        all_defined = set(config.definitions.keys())
        invalid_excludes = [e for e in args.exclude if e not in all_defined]
        if invalid_excludes:
            console.print_warning(
                f"Unknown actions in --exclude will be ignored: {', '.join(invalid_excludes)}"
            )
        actions = [a for a in actions if a not in args.exclude]

    # Apply inclusions
    if args.include:
        all_defined = set(config.definitions.keys())
        for inc in args.include:
            if inc not in all_defined:
                console.print_warning(f"Unknown action in --include: '{inc}'")
            elif inc not in actions:
                actions.append(inc)

    if not actions:
        console.print_warning(
            "No actions to run. Check your config file or use --actions to specify sanitization actions."
        )
        return

    # Build a proper config with resolved action specs
    from ..sanitize_config import SanitizeConfig, ActionSpec

    action_specs = []
    for action_name in actions:
        if action_name in config.definitions:
            action_specs.append(config.definitions[action_name])
        else:
            # Action not in definitions - create implicit spec
            action_specs.append(
                ActionSpec(name=action_name, implementation=action_name)
            )

    run_config = SanitizeConfig(
        actions=action_specs,
        definitions=config.definitions,
        options={"dry_run": args.dry_run, "summary": args.summary},
    )

    # Run sanitization with the full config
    sanitize_powerbi_report(report_path, config=run_config)
