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

    name: str
    implementation: str | None = None  # Python function name (if different from name)
    params: dict[str, Any] = field(default_factory=dict)
    description: str | None = None  # Human-readable description for CLI output

    @classmethod
    def from_definition(cls, name: str, definition: dict | None) -> "ActionSpec":
        """Create ActionSpec from a definitions entry."""
        if definition is None or definition == {}:
            # Implicit: function name matches action name
            return cls(name=name, implementation=name)
        return cls(
            name=name,
            implementation=definition.get("implementation", name),
            params=definition.get("params", {}),
            description=definition.get("description"),
        )

    @property
    def func_name(self) -> str:
        """Get the Python function name to call."""
        return self.implementation or self.name


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
        """Get list of action names in execution order."""
        return [a.name for a in self.actions]

    def get_additional_actions(self) -> list[str]:
        """Get actions defined but not in default list."""
        default_names = set(self.get_action_names())
        return [name for name in self.definitions.keys() if name not in default_names]


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
    1. Definitions: MERGE (user overrides default)
    2. Actions:
       - Start with default actions
       - If user 'actions' exists: REPLACE with user list
       - If user 'include' exists: APPEND to list
       - If user 'exclude' exists: REMOVE from list
    3. Options: MERGE (user overrides default)
    """
    # 1. Merge definitions
    default_defs = _parse_definitions(default.get("definitions", {}))
    user_defs = _parse_definitions(user.get("definitions", {}))

    # User definitions override default definitions
    merged_definitions = {**default_defs, **user_defs}

    # 2. Build action list
    if "actions" in user:
        # User explicitly defines actions -> REPLACE
        action_names = user["actions"]
    else:
        # Use default actions
        action_names = list(default.get("actions", []))

    # Apply 'include' (append)
    include_names = user.get("include", [])
    for name in include_names:
        if name not in action_names:
            action_names.append(name)

    # Apply 'exclude' (remove)
    exclude_names = set(user.get("exclude", []))
    action_names = [name for name in action_names if name not in exclude_names]

    # Resolve action names to ActionSpec objects
    actions = []
    for name in action_names:
        if name in merged_definitions:
            actions.append(merged_definitions[name])
        else:
            # Action not in definitions - create implicit spec
            actions.append(ActionSpec(name=name, implementation=name))

    # 3. Merge options
    options = {**default.get("options", {}), **user.get("options", {})}

    return SanitizeConfig(
        actions=actions,
        definitions=merged_definitions,
        exclude=list(exclude_names),
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
    # Load default config
    default = _load_yaml(get_default_config_path())

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
