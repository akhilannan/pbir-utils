"""
Configuration management for sanitize pipeline.

Handles loading, merging, and validating sanitize configs.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


@dataclass
class ActionSpec:
    """Represents an action with optional parameters."""

    id: str
    implementation: str | None = None  # Python function name (if different from id)
    params: dict[str, Any] = field(default_factory=dict)
    description: str | None = None  # Human-readable description for CLI output
    disabled: bool | None = (
        None  # If True, action is skipped unless explicitly included
    )
    severity: str = "warning"  # Severity level for validation: error, warning, info

    @classmethod
    def from_definition(cls, action_id: str, definition: dict | None) -> "ActionSpec":
        """Create ActionSpec from a definitions entry."""
        if definition is None or definition == {}:
            return cls(id=action_id)
        return cls(
            id=action_id,
            implementation=definition.get("implementation"),
            params=definition.get("params", {}),
            description=definition.get("description"),
            disabled=definition.get("disabled"),
            severity=definition.get("severity", "warning"),
        )

    @property
    def func_name(self) -> str:
        """Get the Python function name to call."""
        return self.implementation or self.id

    @property
    def display_name(self) -> str:
        """Get human-readable display name (description or formatted ID)."""
        if self.description:
            return self.description
        return self.id.replace("_", " ").title()


@dataclass
class SanitizeConfig:
    """Complete sanitize configuration."""

    actions: list[ActionSpec]
    definitions: dict[str, ActionSpec] = field(default_factory=dict)
    exclude: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def dry_run(self) -> bool:
        return self.options.get("dry_run", False)

    @property
    def summary(self) -> bool:
        return self.options.get("summary", False)

    def get_action_names(self) -> list[str]:
        """Get list of action IDs in execution order."""
        return [a.id for a in self.actions]

    def get_additional_actions(self) -> list[str]:
        """Get actions defined but not in default list."""
        default_ids = set(self.get_action_names())
        return [
            action_id
            for action_id in self.definitions.keys()
            if action_id not in default_ids
        ]


def get_default_config_path() -> Path:
    """Get path to default config shipped with package."""
    return Path(__file__).parent / "defaults" / "sanitize.yaml"


def find_user_config(report_path: str | None = None) -> Path | None:
    """
    Find user config file in priority order:
    1. Current working directory
    2. Report folder (if provided)
    """
    search_paths = [Path.cwd()]
    if report_path:
        search_paths.append(Path(report_path))

    for base in search_paths:
        config_path = base / "pbir-sanitize.yaml"
        if config_path.exists():
            return config_path
    return None


def _load_yaml(path: Path) -> dict:
    """Load YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _parse_definitions(raw_definitions: dict) -> dict[str, ActionSpec]:
    """Parse definitions section into ActionSpec objects."""
    definitions = {}
    for name, definition in raw_definitions.items():
        definitions[name] = ActionSpec.from_definition(name, definition)
    return definitions


def _merge_configs(default: dict, user: dict) -> SanitizeConfig:
    """
    Merge user config with default.

    Rules:
    1. Definitions: DEEP MERGE (user params merge with default params)
    2. Actions:
       - If user 'actions' exists: REPLACE with user list
       - Else if default 'actions' exists: Use default list
       - Else: Use ALL defined actions (definition order)
       - If user 'include' exists: APPEND to list
       - If user 'exclude' exists: REMOVE from list
       - Disabled actions are skipped unless explicitly included
    3. Options: MERGE (user overrides default)
    """
    # 1. Merge definitions with deep param merge (like Rules config)
    default_defs = _parse_definitions(default.get("definitions", {}))
    user_defs = _parse_definitions(user.get("definitions", {}))

    # User definitions override specific fields (deep merge)
    merged_definitions = {}
    for action_id, spec in default_defs.items():
        if action_id in user_defs:
            user_spec = user_defs[action_id]
            merged_definitions[action_id] = ActionSpec(
                id=action_id,
                implementation=user_spec.implementation or spec.implementation,
                params={**spec.params, **user_spec.params},  # MERGE params
                description=user_spec.description or spec.description,
                disabled=(
                    user_spec.disabled
                    if user_spec.disabled is not None
                    else spec.disabled
                ),
                severity=(
                    user_spec.severity
                    if user_spec.severity != "warning"
                    else spec.severity
                ),
            )
        else:
            merged_definitions[action_id] = spec

    # Add user-only definitions
    for action_id, spec in user_defs.items():
        if action_id not in merged_definitions:
            merged_definitions[action_id] = spec

    # 2. Build action list
    if "actions" in user:
        # User explicitly defines actions -> REPLACE
        action_ids = list(user["actions"])
    elif "actions" in default and default["actions"]:
        # Use default actions list if provided
        action_ids = list(default["actions"])
    else:
        # No explicit actions list -> include ALL defined actions
        action_ids = list(merged_definitions.keys())

    # Apply 'include' (append)
    include_ids = user.get("include", [])
    include_set = set(include_ids)
    for action_id in include_ids:
        if action_id not in action_ids:
            action_ids.append(action_id)

    # Apply 'exclude' (remove)
    exclude_ids = set(user.get("exclude", []))
    action_ids = [action_id for action_id in action_ids if action_id not in exclude_ids]

    # Resolve action IDs to ActionSpec objects, filtering disabled actions
    actions = []
    for action_id in action_ids:
        if action_id in merged_definitions:
            spec = merged_definitions[action_id]
            # Skip disabled actions unless explicitly included
            if not spec.disabled or action_id in include_set:
                actions.append(spec)
        else:
            # Action not in definitions - create implicit spec
            actions.append(ActionSpec(id=action_id, implementation=action_id))

    # 3. Merge options
    options = {**default.get("options", {}), **user.get("options", {})}

    return SanitizeConfig(
        actions=actions,
        definitions=merged_definitions,
        exclude=list(exclude_ids),
        options=options,
    )


def load_config(
    config_path: str | Path | None = None,
    report_path: str | None = None,
) -> SanitizeConfig:
    """
    Load and merge configuration.

    Args:
        config_path: Explicit path to config file (overrides auto-discovery)
        report_path: Report path for config discovery

    Returns:
        Merged SanitizeConfig
    """
    # Load default config (gracefully handle missing)
    default_path = get_default_config_path()
    if default_path.exists():
        default = _load_yaml(default_path)
    else:
        default = {}

    # Find/load user config
    if config_path:
        user_path = Path(config_path)
        if not user_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {user_path}\n"
                "Please check the path and try again."
            )
    else:
        user_path = find_user_config(report_path)

    user = _load_yaml(user_path) if user_path and user_path.exists() else {}

    return _merge_configs(default, user)
