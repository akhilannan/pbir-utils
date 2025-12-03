import os
import re
from .common import load_json


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


def standardize_pbir_folders(report_path: str, dry_run: bool = False):
    """
    Standardizes folder names for pages and visuals in a PBIR report structure.

    Args:
        report_path (str): Path to the root folder of the report.
        dry_run (bool): If True, only prints what would be renamed without making changes.
    """
    pages_dir = os.path.join(report_path, "definition", "pages")
    if not os.path.exists(pages_dir):
        print(f"Pages directory not found: {pages_dir}")
        return

    # Iterate over page folders
    # We list directories first to avoid issues if we rename them while iterating
    page_folders = [
        f for f in os.listdir(pages_dir) if os.path.isdir(os.path.join(pages_dir, f))
    ]

    for page_folder_name in page_folders:
        current_page_path = os.path.join(pages_dir, page_folder_name)
        page_json_path = os.path.join(current_page_path, "page.json")

        if not os.path.exists(page_json_path):
            continue

        page_data = load_json(page_json_path)
        page_name = page_data.get("name")
        display_name = page_data.get("displayName")

        if not page_name or not display_name:
            continue

        sanitized_display_name = _sanitize_name(display_name)
        new_page_folder_name = f"{sanitized_display_name}_{page_name}"

        # Rename page folder if needed
        if page_folder_name != new_page_folder_name:
            new_page_path = os.path.join(pages_dir, new_page_folder_name)
            if dry_run:
                print(
                    f"[Dry Run] Would rename page folder: '{page_folder_name}' -> '{new_page_folder_name}'"
                )
            else:
                try:
                    os.rename(current_page_path, new_page_path)
                    print(
                        f"Renamed page folder: '{page_folder_name}' -> '{new_page_folder_name}'"
                    )
                    current_page_path = (
                        new_page_path  # Update path for visual processing
                    )
                except OSError as e:
                    print(f"Error renaming page folder '{page_folder_name}': {e}")
                    continue

        # Process visuals within the page
        visuals_dir = os.path.join(current_page_path, "visuals")
        if os.path.exists(visuals_dir):
            visual_folders = [
                f
                for f in os.listdir(visuals_dir)
                if os.path.isdir(os.path.join(visuals_dir, f))
            ]

            for visual_folder_name in visual_folders:
                current_visual_path = os.path.join(visuals_dir, visual_folder_name)
                visual_json_path = os.path.join(current_visual_path, "visual.json")

                if not os.path.exists(visual_json_path):
                    continue

                visual_data = load_json(visual_json_path)
                visual_name = visual_data.get("name")
                visual_type = visual_data.get("visual", {}).get("visualType")

                if not visual_name or not visual_type:
                    continue

                new_visual_folder_name = f"{visual_type}_{visual_name}"

                if visual_folder_name != new_visual_folder_name:
                    new_visual_path = os.path.join(visuals_dir, new_visual_folder_name)
                    if dry_run:
                        print(
                            f"[Dry Run] Would rename visual folder in '{new_page_folder_name}': '{visual_folder_name}' -> '{new_visual_folder_name}'"
                        )
                    else:
                        try:
                            os.rename(current_visual_path, new_visual_path)
                            print(
                                f"Renamed visual folder in '{new_page_folder_name}': '{visual_folder_name}' -> '{new_visual_folder_name}'"
                            )
                        except OSError as e:
                            print(
                                f"Error renaming visual folder '{visual_folder_name}': {e}"
                            )
