"""
Configuration management for rule validation pipeline.

Handles loading, merging, and validating rules configs.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


@dataclass
class RuleSpec:
    """Represents a validation rule specification."""

    id: str
    severity: str = "warning"  # error, warning, info
    # For expression-based rules:
    expression: str | None = None
    scope: str = "report"  # report, page, visual
    description: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    disabled: bool | None = None

    @classmethod
    def from_definition(cls, rule_id: str, definition: dict | None) -> "RuleSpec":
        """Create RuleSpec from a definitions entry."""
        if definition is None or definition == {}:
            # Minimal rule - just ID (sanitizer-based)
            return cls(id=rule_id)
        return cls(
            id=rule_id,
            severity=definition.get("severity", "warning"),
            expression=definition.get("expression"),
            scope=definition.get("scope", "report"),
            description=definition.get("description"),
            params=definition.get("params", {}),
            disabled=definition.get("disabled"),
        )

    @property
    def is_expression_rule(self) -> bool:
        """Check if this is an expression-based rule."""
        return self.expression is not None

    @property
    def display_name(self) -> str:
        """Get human-readable display name (description or formatted ID)."""
        if self.description:
            return self.description
        # Convert snake_case ID to title case
        return self.id.replace("_", " ").title()


@dataclass
class RulesConfig:
    """Complete rules configuration."""

    rules: list[RuleSpec]
    definitions: dict[str, RuleSpec] = field(default_factory=dict)
    exclude: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def fail_on_warning(self) -> bool:
        """If True, warnings are treated as failures in strict mode."""
        return self.options.get("fail_on_warning", False)

    def get_rule_ids(self) -> list[str]:
        """Get list of rule IDs in execution order."""
        return [r.id for r in self.rules]


def get_default_rules_path() -> Path:
    """Get path to default rules config shipped with package."""
    return Path(__file__).parent / "defaults" / "rules.yaml"


def find_user_rules(report_path: str | None = None) -> Path | None:
    """
    Find user rules config file in priority order:
    1. Current working directory
    2. Report folder (if provided)
    """
    search_paths = [Path.cwd()]
    if report_path:
        search_paths.append(Path(report_path))

    for base in search_paths:
        config_path = base / "pbir-rules.yaml"
        if config_path.exists():
            return config_path
    return None


def _load_yaml(path: Path) -> dict:
    """Load YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _parse_definitions(raw_definitions: dict) -> dict[str, RuleSpec]:
    """Parse definitions section into RuleSpec objects."""
    definitions = {}
    for rule_id, definition in raw_definitions.items():
        definitions[rule_id] = RuleSpec.from_definition(rule_id, definition)
    return definitions


def _merge_configs(
    default: dict,
    user: dict,
) -> RulesConfig:
    """
    Merge user config with default.

    Rules:
    1. Definitions: MERGE (user overrides default)
    2. Rules:
       - Start with default rules
       - If user 'rules' exists: REPLACE with user list
       - If user 'include' exists: APPEND to list
       - If user 'exclude' exists: REMOVE from list
    3. Options: MERGE (user overrides default)
    """
    # Merge options
    options = {**default.get("options", {}), **user.get("options", {})}

    # 1. Merge definitions
    default_defs = _parse_definitions(default.get("definitions", {}))
    user_defs = _parse_definitions(user.get("definitions", {}))

    # User definitions override default definitions (merge params/fields)
    merged_definitions = {}
    for rule_id, rule_spec in default_defs.items():
        if rule_id in user_defs:
            # Merge: user overrides specific fields
            user_spec = user_defs[rule_id]
            merged_definitions[rule_id] = RuleSpec(
                id=rule_id,
                severity=(
                    user_spec.severity
                    if user_spec.severity != "warning"
                    else rule_spec.severity
                ),
                expression=user_spec.expression or rule_spec.expression,
                scope=(
                    user_spec.scope if user_spec.scope != "report" else rule_spec.scope
                ),
                description=user_spec.description or rule_spec.description,
                params={**rule_spec.params, **user_spec.params},
                disabled=(
                    user_spec.disabled
                    if user_spec.disabled is not None
                    else rule_spec.disabled
                ),
            )
        else:
            merged_definitions[rule_id] = rule_spec

    # Add user-only definitions
    for rule_id, rule_spec in user_defs.items():
        if rule_id not in merged_definitions:
            merged_definitions[rule_id] = rule_spec

    # 2. Build rule list
    if "rules" in user:
        # User explicitly defines rules -> REPLACE
        rule_ids = list(user["rules"])
    elif "rules" in default and default["rules"]:
        # Use default rules list if provided
        rule_ids = list(default["rules"])
    else:
        # No explicit rules list -> include ALL defined rules
        rule_ids = list(merged_definitions.keys())

    # Apply 'include' (append)
    include_ids = user.get("include", [])
    for rule_id in include_ids:
        if rule_id not in rule_ids:
            rule_ids.append(rule_id)

    # Apply 'exclude' (remove)
    exclude_ids = set(user.get("exclude", []))
    rule_ids = [rule_id for rule_id in rule_ids if rule_id not in exclude_ids]

    # Resolve rule IDs to RuleSpec objects, filtering disabled rules
    rules = []
    for rule_id in rule_ids:
        if rule_id in merged_definitions:
            rule_spec = merged_definitions[rule_id]
            # Skip disabled rules unless explicitly included
            if not rule_spec.disabled or rule_id in include_ids:
                rules.append(rule_spec)
        else:
            # Rule not in definitions - skip unknown rules
            pass

    return RulesConfig(
        rules=rules,
        definitions=merged_definitions,
        exclude=list(exclude_ids),
        options=options,
    )


def load_rules(
    config_path: str | Path | None = None,
    report_path: str | None = None,
) -> RulesConfig:
    """
    Load and merge rules configuration.

    Args:
        config_path: Explicit path to config file (overrides auto-discovery)
        report_path: Report path for config discovery

    Returns:
        Merged RulesConfig
    """
    # Load default config
    default_path = get_default_rules_path()
    if default_path.exists():
        default = _load_yaml(default_path)
    else:
        # No default rules yet - return empty config
        default = {}

    # Find/load user config
    if config_path:
        user_path = Path(config_path)
        if not user_path.exists():
            raise FileNotFoundError(
                f"Rules config file not found: {user_path}\n"
                "Please check the path and try again."
            )
    else:
        user_path = find_user_rules(report_path)

    user = _load_yaml(user_path) if user_path and user_path.exists() else {}

    return _merge_configs(default, user)
