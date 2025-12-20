"""
Page utilities for Power BI report sanitization.

Contains functions for managing pages in PBIR reports.
"""

import os
import shutil

from .common import load_json, write_json, process_json_files, iter_pages
from .console_utils import console


def hide_pages_by_type(
    report_path: str,
    page_type: str,
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Hide pages by binding type.

    Args:
        report_path: The path to the report.
        page_type: The page binding type to hide (e.g., "Tooltip", "Drillthrough").
        dry_run: Whether to perform a dry run.
        summary: Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made, False otherwise.
    """

    def _check_page(page_data: dict, _: str) -> str:
        page_binding = page_data.get("pageBinding", {})
        binding_type = page_binding.get("type")

        if (
            binding_type == page_type
            and page_data.get("visibility") != "HiddenInViewMode"
        ):
            return page_data.get("displayName", "Unnamed Page")
        return None

    results = process_json_files(
        os.path.join(report_path, "definition", "pages"), "page.json", _check_page
    )

    if not results:
        console.print_info(f"No {page_type} pages found that needed hiding.")
        return False

    for file_path, page_name in results:
        page_data = load_json(file_path)
        page_data["visibility"] = "HiddenInViewMode"
        if not dry_run:
            write_json(file_path, page_data)
        if not summary:
            if dry_run:
                console.print_dry_run(f"Would hide page: {page_name}")
            else:
                console.print_success(f"Hidden page: {page_name}")

    if summary:
        if dry_run:
            console.print_dry_run(f"Would hide {len(results)} {page_type} page(s).")
        else:
            console.print_success(f"Hidden {len(results)} {page_type} page(s).")

    return True


def set_first_page_as_active(
    report_path: str, dry_run: bool = False, summary: bool = False
) -> bool:
    """
    Set the first non-hidden page of the report as active.

    Args:
        report_path (str): The path to the report.
        dry_run (bool): Whether to perform a dry run.
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading("Setting the first non-hidden page as active", dry_run)
    pages_dir = os.path.join(report_path, "definition", "pages")
    pages_json_path = os.path.join(pages_dir, "pages.json")
    pages_data = load_json(pages_json_path)

    page_order = pages_data["pageOrder"]
    current_active_page = pages_data.get("activePageName")

    # Map Page ID to (Folder Path, Page Data)
    page_map = {}
    for page_id, folder_path, page_data in iter_pages(report_path):
        page_map[page_id] = (folder_path, page_data)

    # Find the first non-hidden page
    first_non_hidden_page = None
    first_non_hidden_page_display_name = None

    for page_id in page_order:
        if page_id in page_map:
            _, page_data = page_map[page_id]
            if page_data.get("visibility") != "HiddenInViewMode":
                first_non_hidden_page = page_id
                first_non_hidden_page_display_name = page_data.get(
                    "displayName", page_id
                )
                break

    # If all pages are hidden or no page.json exists, default to first page
    if first_non_hidden_page is None:
        first_non_hidden_page = page_order[0]
        if first_non_hidden_page in page_map:
            _, fallback_page_data = page_map[first_non_hidden_page]
            first_non_hidden_page_display_name = fallback_page_data.get(
                "displayName", first_non_hidden_page
            )
        else:
            first_non_hidden_page_display_name = first_non_hidden_page
        console.print_warning(
            f"Warning: All pages are hidden or no page.json found. Defaulting to first page: '{first_non_hidden_page_display_name}' ({first_non_hidden_page})"
        )

    if first_non_hidden_page != current_active_page:
        pages_data["activePageName"] = first_non_hidden_page
        if not dry_run:
            write_json(pages_json_path, pages_data)
        if dry_run:
            console.print_dry_run(
                f"Would set '{first_non_hidden_page_display_name}' ({first_non_hidden_page}) as the active page."
            )
        else:
            console.print_success(
                f"Set '{first_non_hidden_page_display_name}' ({first_non_hidden_page}) as the active page."
            )
        return True
    else:
        console.print_info(
            f"No changes needed. '{first_non_hidden_page_display_name}' ({first_non_hidden_page}) is already set as active."
        )
        return False


def remove_empty_pages(
    report_path: str, dry_run: bool = False, summary: bool = False
) -> bool:
    """
    Remove empty pages and clean up rogue folders in the report.

    Args:
        report_path (str): The path to the report.
        dry_run (bool): Whether to perform a dry run.
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading(
        "Removing empty pages and cleaning up rogue folders", dry_run
    )
    pages_dir = os.path.join(report_path, "definition", "pages")
    pages_json_path = os.path.join(pages_dir, "pages.json")
    pages_data = load_json(pages_json_path)

    page_order = pages_data.get("pageOrder", [])
    active_page_name = pages_data.get("activePageName")

    # Map Page ID to Folder Path
    page_id_to_folder = {}
    folder_to_page_id = {}

    for page_id, folder_path, page_data in iter_pages(report_path):
        page_id_to_folder[page_id] = folder_path
        folder_name = os.path.basename(folder_path)
        folder_to_page_id[folder_name] = page_id

    non_empty_pages = []
    for page_id in page_order:
        if page_id in page_id_to_folder:
            folder_path = page_id_to_folder[page_id]
            visuals_dir = os.path.join(folder_path, "visuals")

            has_visuals = False
            if os.path.exists(visuals_dir) and os.listdir(visuals_dir):
                has_visuals = True

            if has_visuals:
                non_empty_pages.append(page_id)

    if non_empty_pages:
        pages_data["pageOrder"] = non_empty_pages
        if active_page_name not in non_empty_pages:
            pages_data["activePageName"] = non_empty_pages[0]
    else:
        first_page_id = page_order[0]
        pages_data["pageOrder"] = [first_page_id]
        pages_data["activePageName"] = first_page_id
        non_empty_pages.append(first_page_id)
        console.print_warning(
            "All pages were empty. Keeping the first page as a placeholder."
        )

    if not dry_run:
        write_json(pages_json_path, pages_data)

    folders_to_remove = []
    existing_folders = [
        f for f in os.listdir(pages_dir) if os.path.isdir(os.path.join(pages_dir, f))
    ]

    for folder_name in existing_folders:
        page_id = folder_to_page_id.get(folder_name)

        if not page_id:
            folders_to_remove.append(folder_name)
        elif page_id not in non_empty_pages:
            folders_to_remove.append(folder_name)

    if folders_to_remove:
        if not summary:
            console.print_info(
                f"Removing empty and rogue page folders: {', '.join(folders_to_remove)}"
            )
        for folder in folders_to_remove:
            folder_path = os.path.join(pages_dir, folder)
            if not dry_run:
                shutil.rmtree(folder_path)
            if not summary:
                if dry_run:
                    console.print_dry_run(f"Would remove folder: {folder}")
                else:
                    console.print_success(f"Removed folder: {folder}")
        if summary:
            if dry_run:
                console.print_dry_run(
                    f"Would remove {len(folders_to_remove)} empty/rogue page folders"
                )
            else:
                console.print_success(
                    f"Removed {len(folders_to_remove)} empty/rogue page folders"
                )
        return True
    else:
        console.print_info("No empty or rogue page folders found.")
        return False


def set_page_size(
    report_path: str,
    width: int = 1280,
    height: int = 720,
    exclude_tooltip: bool = True,
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Set the page size for pages in the report.

    Args:
        report_path (str): The path to the report.
        width (int): Target page width (default: 1280).
        height (int): Target page height (default: 720).
        exclude_tooltip (bool): Skip tooltip pages (default: True).
        dry_run (bool): Perform a dry run without making changes.
        summary (bool): Show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading(f"Setting page size to {width}x{height}", dry_run)

    pages_dir = os.path.join(report_path, "definition", "pages")
    modified_count = 0

    if not os.path.exists(pages_dir):
        console.print_warning("No pages directory found.")
        return False

    for page_id, folder_path, page_data in iter_pages(report_path):
        page_json_path = os.path.join(folder_path, "page.json")
        folder_name = os.path.basename(folder_path)

        # Skip tooltip pages if configured
        if exclude_tooltip and page_data.get("type") == "Tooltip":
            if not summary:
                console.print_info(
                    f"Skipping tooltip page: {page_data.get('displayName', folder_name)}"
                )
            continue

        current_width = page_data.get("width")
        current_height = page_data.get("height")

        # Check if modification is needed
        if current_width != width or current_height != height:
            page_data["width"] = width
            page_data["height"] = height

            if not dry_run:
                write_json(page_json_path, page_data)

            modified_count += 1
            if not summary:
                page_name = page_data.get("displayName", folder_name)
                if dry_run:
                    console.print_dry_run(
                        f"Would set page '{page_name}' size from {current_width}x{current_height} to {width}x{height}"
                    )
                else:
                    console.print_success(
                        f"Set page '{page_name}' size from {current_width}x{current_height} to {width}x{height}"
                    )

    if modified_count > 0:
        if dry_run:
            console.print_dry_run(
                f"Would modify {modified_count} page(s) to {width}x{height}."
            )
        else:
            console.print_success(
                f"Modified {modified_count} page(s) to {width}x{height}."
            )
        return True
    else:
        console.print_info(
            f"All pages already have the target size ({width}x{height})."
        )
        return False


# Valid display options for pages
VALID_DISPLAY_OPTIONS = {"ActualSize", "FitToPage", "FitToWidth"}


def set_page_display_option(
    report_path: str,
    display_option: str,
    page: str = None,
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Set the display option for pages in the report.

    Args:
        report_path (str): The path to the report.
        display_option (str): Display option to set ("ActualSize", "FitToPage", "FitToWidth").
        page (str): Page name or displayName to filter. None applies to all pages.
        dry_run (bool): Perform a dry run without making changes.
        summary (bool): Show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    # Validate display option
    if display_option not in VALID_DISPLAY_OPTIONS:
        console.print_error(
            f"Invalid display option '{display_option}'. "
            f"Must be one of: {', '.join(sorted(VALID_DISPLAY_OPTIONS))}"
        )
        return False

    page_filter_msg = f" for page '{page}'" if page else " for all pages"
    console.print_action_heading(
        f"Setting display option to {display_option}{page_filter_msg}", dry_run
    )

    pages_dir = os.path.join(report_path, "definition", "pages")
    modified_count = 0

    if not os.path.exists(pages_dir):
        console.print_warning("No pages directory found.")
        return False

    for page_id, folder_path, page_data in iter_pages(report_path):
        page_json_path = os.path.join(folder_path, "page.json")
        folder_name = os.path.basename(folder_path)

        # Check if this page matches the filter (by name or displayName)
        if page is not None:
            page_name = page_data.get("name", "")
            page_display_name = page_data.get("displayName", "")
            if page != page_name and page != page_display_name:
                continue

        current_option = page_data.get("displayOption")

        # Check if modification is needed
        if current_option != display_option:
            page_data["displayOption"] = display_option

            if not dry_run:
                write_json(page_json_path, page_data)

            modified_count += 1
            if not summary:
                page_display_name = page_data.get("displayName", folder_name)
                old_option = current_option if current_option else "(default)"
                if dry_run:
                    console.print_dry_run(
                        f"Would set page '{page_display_name}' display option "
                        f"from {old_option} to {display_option}"
                    )
                else:
                    console.print_success(
                        f"Set page '{page_display_name}' display option "
                        f"from {old_option} to {display_option}"
                    )

    if modified_count > 0:
        if summary:
            if dry_run:
                console.print_dry_run(
                    f"Would modify {modified_count} page(s) to {display_option}."
                )
            else:
                console.print_success(
                    f"Modified {modified_count} page(s) to {display_option}."
                )
        return True
    else:
        if page:
            console.print_info(
                f"No matching page found or page already has display option '{display_option}'."
            )
        else:
            console.print_info(
                f"All pages already have the display option '{display_option}'."
            )
        return False
