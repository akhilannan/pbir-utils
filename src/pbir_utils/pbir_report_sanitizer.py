"""
Orchestrate sanitization pipeline for Power BI reports.

Individual actions are in:
- bookmark_utils.py
- page_utils.py
- visual_utils.py
- filter_utils.py
- folder_standardizer.py
- pbir_measure_utils.py
"""

import inspect
from functools import lru_cache
from pathlib import Path
from typing import Callable, Any

from .console_utils import console
from .sanitize_config import load_config, SanitizeConfig, ActionSpec


@lru_cache(maxsize=1)
def get_available_actions() -> dict[str, Callable]:
    """
    Auto-discover all pipeline-compatible functions from pbir_utils.

    A function is compatible if it:
    - Takes report_path (or path, directory_path) as first argument
    - Has dry_run parameter

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

            actions[name] = func
        except (ValueError, TypeError):
            continue
    return actions


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
        # Load config to get definitions, then filter to requested actions
        full_cfg = load_config(report_path=report_path)
        filtered_actions = []
        for action_name in actions:
            if action_name in full_cfg.definitions:
                filtered_actions.append(full_cfg.definitions[action_name])
            else:
                # Not in definitions - create implicit spec
                filtered_actions.append(
                    ActionSpec(name=action_name, implementation=action_name)
                )
        cfg = SanitizeConfig(
            actions=filtered_actions,
            definitions=full_cfg.definitions,
            options={"dry_run": dry_run, "summary": summary},
        )
    elif isinstance(config, SanitizeConfig):
        cfg = config
    elif isinstance(config, dict):
        # Direct dict config (rare case)
        from .sanitize_config import _parse_definitions

        definitions = _parse_definitions(config.get("definitions", {}))
        action_specs = []
        for a in config.get("actions", []):
            if isinstance(a, str) and a in definitions:
                action_specs.append(definitions[a])
            elif isinstance(a, str):
                action_specs.append(ActionSpec(name=a, implementation=a))
            else:
                action_specs.append(ActionSpec.from_definition(a.get("name", ""), a))
        cfg = SanitizeConfig(
            actions=action_specs,
            definitions=definitions,
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
        # Use func_name to resolve the actual Python function
        func_name = action_spec.func_name
        if func_name not in available:
            console.print_warning(
                f"Warning: Unknown action '{action_spec.name}' (func: {func_name}) skipped."
            )
            continue

        func = available[func_name]

        # Print action heading from config description if available
        # and suppress the function's default heading
        if action_spec.description:
            console.print_action_heading(action_spec.description, cfg.dry_run)
            # Suppress the action function's default heading
            with console.suppress_heading():
                # Build kwargs
                kwargs: dict[str, Any] = {
                    "dry_run": cfg.dry_run,
                    "summary": cfg.summary,
                    **action_spec.params,
                }
                results[action_spec.name] = func(report_path, **kwargs)
        else:
            # No custom description - let function print its default heading
            kwargs: dict[str, Any] = {
                "dry_run": cfg.dry_run,
                "summary": cfg.summary,
                **action_spec.params,
            }
            results[action_spec.name] = func(report_path, **kwargs)

    print()  # Add blank line before final status
    console.print_success("Power BI report sanitization completed.")
    return results
