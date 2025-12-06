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
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(cls, item: str | dict) -> "ActionSpec":
        """Create ActionSpec from config item (string or dict)."""
        if isinstance(item, str):
            return cls(name=item)
        return cls(name=item["name"], params=item.get("params", {}))


@dataclass
class SanitizeConfig:
    """Complete sanitize configuration."""

    actions: list[ActionSpec]
    exclude: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def dry_run(self) -> bool:
        return self.options.get("dry_run", False)

    @property
    def summary(self) -> bool:
        return self.options.get("summary", False)

    @property
    def error_on_change(self) -> list[str]:
        return self.options.get("error_on_change", [])


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


def _merge_configs(default: dict, user: dict) -> SanitizeConfig:
    """
    Merge user config with default.

    Rules:
    - User 'actions' entries override matching default entries (by name)
    - User 'exclude' removes actions from final list
    - User 'options' merge with default options
    """
    # Start with default actions
    actions_by_name = {}
    for item in default.get("actions", []):
        spec = ActionSpec.from_config(item)
        actions_by_name[spec.name] = spec

    # Apply user overrides/additions
    for item in user.get("actions", []):
        spec = ActionSpec.from_config(item)
        if spec.name in actions_by_name:
            # Merge params (user overrides default)
            existing = actions_by_name[spec.name]
            merged_params = {**existing.params, **spec.params}
            actions_by_name[spec.name] = ActionSpec(spec.name, merged_params)
        else:
            actions_by_name[spec.name] = spec

    # Remove excluded actions
    exclude = set(user.get("exclude", []))
    final_actions = [a for a in actions_by_name.values() if a.name not in exclude]

    # Merge options
    options = {**default.get("options", {}), **user.get("options", {})}

    return SanitizeConfig(
        actions=final_actions,
        exclude=list(exclude),
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
    else:
        user_path = find_user_config(report_path)

    user = _load_yaml(user_path) if user_path and user_path.exists() else {}

    return _merge_configs(default, user)
