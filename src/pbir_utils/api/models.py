"""Pydantic models for API request/response validation."""

from pydantic import BaseModel


class FileItem(BaseModel):
    """File system item."""

    name: str
    path: str
    is_dir: bool
    is_report: bool


class BrowseResponse(BaseModel):
    """Response for file browser endpoint."""

    current_path: str
    parent_path: str | None
    items: list[FileItem]


class WireframeRequest(BaseModel):
    """Request for wireframe data."""

    report_path: str
    pages: list[str] | None = None
    visual_types: list[str] | None = None
    show_hidden: bool = True


class WireframeResponse(BaseModel):
    """Response with wireframe data."""

    report_name: str
    pages: list[dict]
    fields_index: dict
    active_page_id: str | None
    html_content: str | None = None


class ActionInfo(BaseModel):
    """Information about a sanitize action."""

    id: str
    description: str | None = None
    is_default: bool = False


class ActionsResponse(BaseModel):
    """Response listing available actions with metadata."""

    actions: list[ActionInfo]
    config_path: str | None = None


class ConfigResponse(BaseModel):
    """Response with sanitize config."""

    actions: list[str]
    definitions: dict


class RunActionRequest(BaseModel):
    """Request to run sanitize actions."""

    report_path: str
    actions: list[str]
    dry_run: bool = True
    config_data: dict | None = None


class RunActionResponse(BaseModel):
    """Response from running actions."""

    success: bool
    output: list[str]


# Validation models


class RuleInfo(BaseModel):
    """Expression-based validation rule."""

    id: str
    description: str | None = None
    severity: str = "warning"
    scope: str = "report"


class RulesResponse(BaseModel):
    """Response listing expression-based rules."""

    rules: list[RuleInfo]
    config_path: str | None = None


class ValidateRequest(BaseModel):
    """Request for combined validation."""

    report_path: str
    expression_rules: list[str] | None = None
    sanitize_actions: list[str] | None = None
    rules_config_yaml: str | None = None  # Base64 encoded custom rules YAML
    include_sanitizer: bool = True  # Whether to include sanitizer action checks


class ViolationInfo(BaseModel):
    """Single validation violation."""

    rule_id: str
    rule_name: str
    severity: str
    message: str
    rule_type: str = "expression"
    page_name: str | None = None
    visual_name: str | None = None


class ValidateResponse(BaseModel):
    """Validation results."""

    passed: int
    failed: int
    error_count: int
    warning_count: int
    info_count: int
    results: dict[str, bool]
    violations: list[ViolationInfo]
