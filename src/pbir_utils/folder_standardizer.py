from pathlib import Path
import re
from .common import load_json
from .console_utils import console


def _sanitize_name(name: str) -> str:
    """
    Sanitizes a string to be safe for use as a folder name.
    Replaces non-alphanumeric characters with underscores and collapses multiple underscores.
    """
    # Replace non-alphanumeric characters with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9]", "_", name)
    # Collapse multiple underscores into one
    sanitized = re.sub(r"_+", "_", sanitized)
    # Remove leading/trailing underscores
    return sanitized.strip("_")


def standardize_pbir_folders(
    report_path: str, dry_run: bool = False, summary: bool = False
) -> bool:
    """
    Standardizes folder names for pages and visuals in a PBIR report structure.

    Args:
        report_path (str): Path to the root folder of the report.
        dry_run (bool): If True, only prints what would be renamed without making changes.
        summary (bool): If True, shows a count summary instead of individual renames.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading("Standardizing folder names", dry_run)
    pages_dir = Path(report_path) / "definition" / "pages"
    if not pages_dir.exists():
        console.print_warning(f"Pages directory not found: {pages_dir}")
        return False

    # Iterate over page folders
    # We list directories first to avoid issues if we rename them while iterating
    page_folders = [f for f in pages_dir.iterdir() if f.is_dir()]

    pages_renamed = 0
    visuals_renamed = 0

    for page_folder_path in page_folders:
        page_folder_name = page_folder_path.name
        page_json_path = page_folder_path / "page.json"

        if not page_json_path.exists():
            continue

        page_data = load_json(page_json_path)
        page_name = page_data.get("name")
        display_name = page_data.get("displayName")

        if not page_name or not display_name:
            continue

        sanitized_display_name = _sanitize_name(display_name)
        new_page_folder_name = f"{sanitized_display_name}_{page_name}"

        # Rename page folder if needed
        current_page_path = page_folder_path
        if page_folder_name != new_page_folder_name:
            new_page_path = pages_dir / new_page_folder_name
            if dry_run:
                pages_renamed += 1
                if not summary:
                    console.print_dry_run(
                        f"Would rename page folder: '{page_folder_name}' -> '{new_page_folder_name}'"
                    )
            else:
                try:
                    page_folder_path.rename(new_page_path)
                    pages_renamed += 1
                    if not summary:
                        console.print_success(
                            f"Renamed page folder: '{page_folder_name}' -> '{new_page_folder_name}'"
                        )
                    current_page_path = (
                        new_page_path  # Update path for visual processing
                    )
                except OSError as e:
                    console.print_error(
                        f"Error renaming page folder '{page_folder_name}': {e}"
                    )
                    continue

        # Process visuals within the page
        visuals_dir = current_page_path / "visuals"
        if visuals_dir.exists():
            visual_folders = [f for f in visuals_dir.iterdir() if f.is_dir()]

            for visual_folder_path in visual_folders:
                visual_folder_name = visual_folder_path.name
                visual_json_path = visual_folder_path / "visual.json"

                if not visual_json_path.exists():
                    continue

                visual_data = load_json(visual_json_path)
                visual_name = visual_data.get("name")
                visual_type = visual_data.get("visual", {}).get("visualType")

                if not visual_name or not visual_type:
                    continue

                new_visual_folder_name = f"{visual_type}_{visual_name}"

                if visual_folder_name != new_visual_folder_name:
                    new_visual_path = visuals_dir / new_visual_folder_name
                    if dry_run:
                        visuals_renamed += 1
                        if not summary:
                            console.print_dry_run(
                                f"Would rename visual folder in '{new_page_folder_name}': '{visual_folder_name}' -> '{new_visual_folder_name}'"
                            )
                    else:
                        try:
                            visual_folder_path.rename(new_visual_path)
                            visuals_renamed += 1
                            if not summary:
                                console.print_success(
                                    f"Renamed visual folder in '{new_page_folder_name}': '{visual_folder_name}' -> '{new_visual_folder_name}'"
                                )
                        except OSError as e:
                            console.print_error(
                                f"Error renaming visual folder '{visual_folder_name}': {e}"
                            )

    has_changes = pages_renamed > 0 or visuals_renamed > 0

    if summary:
        if has_changes:
            if dry_run:
                msg = f"Would rename {pages_renamed} page folders and {visuals_renamed} visual folders"
                console.print_dry_run(msg)
            else:
                msg = f"Renamed {pages_renamed} page folders and {visuals_renamed} visual folders"
                console.print_success(msg)
        else:
            console.print_info("All folders are already using standard naming.")
    elif not has_changes:
        console.print_info("All folders are already using standard naming.")

    return has_changes
