import json
import re
import shutil
from pathlib import Path

from .common import load_json, write_json, iter_pages, iter_visuals
from .console_utils import console


def set_theme(
    report_path: str,
    theme_path: str,
    *,
    config_dir: str | None = None,
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """Apply a theme JSON to the report."""
    console.print_action_heading("Setting report theme", dry_run)
    report_json_path = Path(report_path) / "definition" / "report.json"

    if not report_json_path.exists():
        console.print_warning("No report.json found.")
        return False

    source_theme_path = Path(theme_path)
    if not source_theme_path.is_absolute() and config_dir:
        resolved = (Path(config_dir) / source_theme_path).resolve()

        # If config_dir resolution fails, fall back to CWD resolution.
        # This handles cases where the config lives in a subdirectory
        # (e.g., scripts/) but the theme_path is specified relative to CWD.
        if resolved.exists():
            source_theme_path = resolved
        else:
            cwd_resolved = source_theme_path.resolve()
            source_theme_path = cwd_resolved if cwd_resolved.exists() else resolved
    else:
        source_theme_path = source_theme_path.resolve()

    if not source_theme_path.exists():
        console.print_warning(f"Theme file not found: {source_theme_path}")
        return False

    theme_name = source_theme_path.name
    report_data = load_json(str(report_json_path))

    # Check if this exact theme is already applied with the same content
    existing_theme = report_data.get("themeCollection", {}).get("customTheme", {})
    existing_theme_name = existing_theme.get("name")
    existing_version = existing_theme.get(
        "reportVersionAtImport",
        {
            "visual": "1.8.0",  # default versions just in case
            "report": "2.0.0",
            "page": "1.3.0",
        },
    )

    existing_path = None
    if existing_theme_name:
        existing_path = (
            Path(report_path)
            / "StaticResources"
            / "RegisteredResources"
            / existing_theme_name
        )
        if existing_path.exists():
            try:
                existing_content = load_json(str(existing_path))
                new_content = load_json(str(source_theme_path))
                if (
                    existing_theme_name == theme_name
                    and existing_content == new_content
                ):
                    if summary:
                        console.print_info(
                            f"Theme '{theme_name}' already matches — no changes needed."
                        )
                    else:
                        console.print_info(
                            "Theme already matches existing — no changes needed."
                        )
                    return False
            except (json.JSONDecodeError, OSError):
                # If we fail to load or compare, ignore and proceed to overwrite
                pass

    if "themeCollection" not in report_data:
        report_data["themeCollection"] = {}

    report_data["themeCollection"]["customTheme"] = {
        "name": theme_name,
        "reportVersionAtImport": existing_version,
        "type": "RegisteredResources",
    }

    # Check if we need to update resourcePackages
    packages = report_data.get("resourcePackages", [])
    registered = None
    for pkg in packages:
        if pkg.get("name") == "RegisteredResources":
            registered = pkg
            break

    if not registered:
        registered = {
            "name": "RegisteredResources",
            "type": "RegisteredResources",
            "items": [],
        }
        packages.append(registered)
        report_data["resourcePackages"] = packages

    items = registered.get("items", [])
    # Remove existing custom theme from items
    items = [item for item in items if item.get("type") != "CustomTheme"]

    items.append({"name": theme_name, "path": theme_name, "type": "CustomTheme"})
    registered["items"] = items

    should_remove_old = bool(
        existing_path and existing_path.exists() and existing_theme_name != theme_name
    )

    made_changes = True
    if not dry_run:
        write_json(str(report_json_path), report_data)

        # Copy the theme file
        dest_dir = Path(report_path) / "StaticResources" / "RegisteredResources"
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_theme_path, dest_dir / theme_name)

        # Remove the old theme file if it has a different name
        if should_remove_old:
            try:
                existing_path.unlink()
                if not summary:
                    console.print_info(
                        f"Removed old theme file '{existing_theme_name}'."
                    )
            except OSError as e:
                console.print_warning(
                    f"Failed to remove old theme file '{existing_theme_name}': {e}"
                )

    if summary:
        if dry_run:
            console.print_dry_run(f"Would set theme to '{theme_name}'.")
        else:
            console.print_success(f"Set theme to '{theme_name}'.")
    else:
        if dry_run:
            if should_remove_old:
                console.print_dry_run(
                    f"Would remove old theme file '{existing_theme_name}'."
                )
            console.print_dry_run(f"Would copy {theme_name} and update report.json.")
        else:
            console.print_success(f"Copied {theme_name} and updated report.json.")

    return made_changes


def _is_hardcoded_color(val) -> bool:
    """Check if a value contains a hardcoded hex color or gradient fill rule."""
    if not isinstance(val, dict):
        return False

    # Check for solid color literal
    solid_color = val.get("solid", {}).get("color", {})
    if solid_color:
        expr = solid_color.get("expr", {})
        if "Literal" in expr:
            literal_val = expr["Literal"].get("Value", "")
            if isinstance(literal_val, str):
                clean_val = literal_val.strip("'\"")
                if re.match(r"^#[A-Fa-f0-9]{6,8}$", clean_val):
                    return True
        if "FillRule" in expr:
            inner_rule = expr["FillRule"].get("FillRule", {})
            if "linearGradient2" in inner_rule or "linearGradient3" in inner_rule:
                return True

    return False


def _remove_hardcoded_colors_from_dict(obj: dict | list) -> int:
    """Recursively remove properties that are hardcoded colors. Returns count removed."""
    removed_count = 0

    if isinstance(obj, dict):
        keys_to_remove = []
        for k, v in obj.items():
            if _is_hardcoded_color(v):
                keys_to_remove.append(k)
            elif isinstance(v, (dict, list)):
                removed_count += _remove_hardcoded_colors_from_dict(v)

        for k in keys_to_remove:
            del obj[k]
            removed_count += 1

    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                removed_count += _remove_hardcoded_colors_from_dict(item)

    return removed_count


def reset_hardcoded_colors(
    report_path: str,
    pages: list[str] = None,
    visual_types: list[str] = None,
    visual_ids: list[str] = None,
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Remove hardcoded hex colors from visuals to revert them to theme colors.

    Args:
        report_path: Path to the report.
        pages: List of page names or displayNames to process. If None, process all.
        visual_types: List of visual types (e.g., 'barChart') to process. If None, process all.
        visual_ids: List of specific visual names to process. If None, process all.
        dry_run: Whether to perform a dry run.
        summary: Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading("Resetting hardcoded colors", dry_run)

    pages_to_process = [p.lower() for p in pages] if pages else None
    types_to_process = [t.lower() for t in visual_types] if visual_types else None
    ids_to_process = [i.lower() for i in visual_ids] if visual_ids else None

    total_colors_removed = 0
    visuals_modified = 0
    pages_affected = set()

    for page_id, page_folder, page_data in iter_pages(report_path):
        display_name = page_data.get("displayName", "")

        if pages_to_process:
            if (
                page_id.lower() not in pages_to_process
                and display_name.lower() not in pages_to_process
            ):
                continue

        for vis_id, vis_folder, vis_data in iter_visuals(page_folder):
            if ids_to_process and vis_id.lower() not in ids_to_process:
                continue

            vis_type = vis_data.get("visual", {}).get("visualType", "")
            if types_to_process and vis_type.lower() not in types_to_process:
                continue

            # Process visual objects and visualContainerObjects
            visual_block = vis_data.get("visual", {})
            removed_in_vis = 0

            for section in ["objects", "visualContainerObjects"]:
                if section in visual_block:
                    removed = _remove_hardcoded_colors_from_dict(visual_block[section])
                    removed_in_vis += removed

            if removed_in_vis > 0:
                total_colors_removed += removed_in_vis
                visuals_modified += 1
                pages_affected.add(display_name or page_id)

                if not summary:
                    if dry_run:
                        console.print_dry_run(
                            f"Would remove {removed_in_vis} color(s) from visual '{vis_id}' on page '{display_name or page_id}'"
                        )
                    else:
                        console.print_success(
                            f"Removed {removed_in_vis} color(s) from visual '{vis_id}' on page '{display_name or page_id}'"
                        )

                if not dry_run:
                    vis_json_path = Path(vis_folder) / "visual.json"
                    write_json(str(vis_json_path), vis_data)

    if total_colors_removed == 0:
        console.print_info("No hardcoded colors found matching criteria.")
        return False

    if summary:
        msg = f"removed {total_colors_removed} hardcoded color(s) across {visuals_modified} visual(s) on {len(pages_affected)} page(s)"
        if dry_run:
            console.print_dry_run(f"Would have {msg}")
        else:
            console.print_success(f"Successfully {msg}")

    return True
