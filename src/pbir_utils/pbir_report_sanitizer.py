"""
Orchestrate sanitization pipeline for Power BI reports.

Individual actions are in:
- bookmark_utils.py
- page_utils.py
- visual_utils.py
- filter_utils.py
- folder_standardizer.py
"""

import inspect
from functools import lru_cache
from pathlib import Path
from typing import Callable, Any

from .console_utils import console
from .sanitize_config import load_config, SanitizeConfig, ActionSpec

# Re-export all action functions for backward compatibility
from .pbir_measure_utils import remove_measures


def remove_unused_measures(
    report_path: str, dry_run: bool = False, summary: bool = False
) -> bool:
    """
    Remove unused measures from the report.

    Args:
        report_path (str): The path to the report.
        dry_run (bool): Whether to perform a dry run.
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_heading(
        f"Action: Removing unused measures{' (Dry Run)' if dry_run else ''}"
    )
    return remove_measures(
        report_path,
        check_visual_usage=True,
        dry_run=dry_run,
        print_heading=False,
        summary=summary,
    )


@lru_cache(maxsize=1)
def get_available_actions() -> dict[str, Callable]:
    """
    Auto-discover all pipeline-compatible functions from pbir_utils.

    A function is compatible if it:
    - Takes report_path (or path, directory_path) as first argument
    - Has dry_run parameter
    - All non-report_path params have default values

    Results are cached for performance.
    """
    import pbir_utils

    actions = {}
    for name in getattr(pbir_utils, "__all__", []):
        func = getattr(pbir_utils, name, None)
        if not callable(func):
            continue
        try:
            sig = inspect.signature(func)
            params = list(sig.parameters.values())
            if not params:
                continue

            # First param must be report_path, path, or directory_path
            first_param = params[0]
            if first_param.name not in ("report_path", "path", "directory_path"):
                continue

            # Must have dry_run parameter
            param_names = {p.name for p in params}
            if "dry_run" not in param_names:
                continue

            # All non-first params must have default values
            has_only_optional_params = all(
                p.default != inspect.Parameter.empty
                or p.kind
                in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
                for p in params[1:]
            )

            if not has_only_optional_params:
                continue

            actions[name] = func
        except (ValueError, TypeError):
            continue
    return actions


def get_simple_actions() -> dict[str, Callable]:
    """
    Get actions with simple signature for CLI display.

    Only includes functions with exact signature: (report_path, dry_run, summary)
    """
    ALLOWED_PARAMS = {"report_path", "path", "directory_path", "dry_run", "summary"}

    return {
        name: func
        for name, func in get_available_actions().items()
        if set(inspect.signature(func).parameters.keys()).issubset(ALLOWED_PARAMS)
    }


def sanitize_powerbi_report(
    report_path: str,
    actions: list[str] | None = None,
    *,
    config: str | Path | dict | SanitizeConfig | None = None,
    dry_run: bool = False,
    summary: bool = False,
) -> dict[str, bool]:
    """
    Sanitize a Power BI report by performing specified actions.

    Args:
        report_path: Path to the report folder.
        actions: List of action names (backward compatible mode).
        config: Config file path, dict, or SanitizeConfig object.
        dry_run: Perform dry run without making changes.
        summary: Show summary instead of detailed messages.

    Returns:
        Dict mapping action names to whether changes were made.
    """
    # Handle backward compatibility
    if actions is not None and config is None:
        # Old-style call: sanitize_powerbi_report(path, ["action1", "action2"])
        cfg = SanitizeConfig(
            actions=[ActionSpec(name=a) for a in actions],
            options={"dry_run": dry_run, "summary": summary},
        )
    elif isinstance(config, SanitizeConfig):
        cfg = config
    elif isinstance(config, dict):
        cfg = SanitizeConfig(
            actions=[ActionSpec.from_config(a) for a in config.get("actions", [])],
            exclude=config.get("exclude", []),
            options=config.get("options", {}),
        )
    else:
        # Load from file (or auto-discover)
        cfg = load_config(config_path=config, report_path=report_path)

    # Override with explicit params
    if dry_run:
        cfg.options["dry_run"] = True
    if summary:
        cfg.options["summary"] = True

    # Get available actions (cached)
    available = get_available_actions()

    # Execute pipeline
    results = {}
    for action_spec in cfg.actions:
        if action_spec.name not in available:
            console.print_warning(
                f"Warning: Unknown action '{action_spec.name}' skipped."
            )
            continue

        func = available[action_spec.name]

        # Build kwargs
        kwargs: dict[str, Any] = {
            "dry_run": cfg.dry_run,
            "summary": cfg.summary,
            **action_spec.params,
        }

        results[action_spec.name] = func(report_path, **kwargs)

    console.print_success("Power BI report sanitization completed.")
    return results
