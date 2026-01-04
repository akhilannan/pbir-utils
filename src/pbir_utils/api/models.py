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

    name: str
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
