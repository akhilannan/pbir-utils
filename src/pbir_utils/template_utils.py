"""Shared template rendering utilities for PBIR-Utils."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_env: Environment | None = None


def get_template_env() -> Environment:
    """
    Get the shared Jinja2 environment for rendering templates.

    Returns a cached Environment instance configured with the templates
    and static directories.
    """
    global _env
    if _env is None:
        template_dir = Path(__file__).parent / "templates"
        static_dir = Path(__file__).parent / "static"
        _env = Environment(
            loader=FileSystemLoader([template_dir, static_dir]),
            autoescape=select_autoescape(["html", "htm", "xml", "j2"]),
        )
    return _env


def render_wireframe_html(data: dict) -> str:
    """
    Render the standalone wireframe HTML template.

    Args:
        data: Dictionary containing report_name, pages, fields_index, active_page_id.

    Returns:
        Complete HTML string for the standalone wireframe page.
    """
    template = get_template_env().get_template("wireframe.html.j2")
    return template.render(
        report_name=data["report_name"],
        pages=data["pages"],
        fields_index=data["fields_index"],
        active_page_id=data.get("active_page_id"),
    )


def render_wireframe_content(data: dict) -> str:
    """
    Render just the wireframe content template (for embedding in client).

    Args:
        data: Dictionary containing report_name, pages, fields_index, active_page_id.

    Returns:
        HTML string for the wireframe content partial.
    """
    template = get_template_env().get_template("wireframe_content.html.j2")
    return template.render(
        report_name=data["report_name"],
        pages=data["pages"],
        fields_index=data["fields_index"],
        active_page_id=data.get("active_page_id"),
    )
