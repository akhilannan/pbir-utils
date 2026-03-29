"""
Page utilities for Power BI report sanitization.

Contains functions for managing pages in PBIR reports.
"""

from pathlib import Path
import shutil

from .common import (
    load_json,
    write_json,
    walk_json_files,
    process_json_files,
    iter_pages,
    iter_visuals,
)
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
        str(Path(report_path) / "definition" / "pages"), "page.json", _check_page
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


def set_active_page(
    report_path: str, page: str = None, dry_run: bool = False, summary: bool = False
) -> bool:
    """
    Set a specific page or the first non-hidden page as active.

    Args:
        report_path (str): The path to the report.
        page (str, optional): Page name or displayName to target. If None, sets the first non-hidden page.
        dry_run (bool): Whether to perform a dry run.
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    page_filter_msg = f" '{page}'" if page else " the first non-hidden page"
    console.print_action_heading(f"Setting{page_filter_msg} as active", dry_run)
    pages_dir = Path(report_path) / "definition" / "pages"
    pages_json_path = pages_dir / "pages.json"

    if not pages_json_path.exists():
        console.print_warning("No pages.json found.")
        return False

    pages_data = load_json(str(pages_json_path))

    page_order = pages_data.get("pageOrder", [])
    if not page_order:
        console.print_warning("No pages found in pageOrder. Cannot set active page.")
        return False
    current_active_page = pages_data.get("activePageName")

    page_map = {}
    for page_id, folder_path, page_data in iter_pages(report_path):
        page_map[page_id] = (folder_path, page_data)

    target_page_id = None
    target_page_display_name = None

    if page is not None:
        # Look for the specific page by name or displayName
        for page_id in page_order:
            if page_id in page_map:
                _, page_data = page_map[page_id]
                page_name = page_data.get("name", page_id)
                page_display_name = page_data.get("displayName", page_id)
                if page == page_name or page == page_display_name:
                    target_page_id = page_id
                    target_page_display_name = page_display_name
                    break

        # Also check pages not in pageOrder
        if target_page_id is None:
            for page_id, (_, page_data) in page_map.items():
                page_name = page_data.get("name", page_id)
                page_display_name = page_data.get("displayName", page_id)
                if page == page_name or page == page_display_name:
                    target_page_id = page_id
                    target_page_display_name = page_display_name
                    break

        if target_page_id is None:
            console.print_warning(
                f"Warning: Page '{page}' not found. Cannot set as active."
            )
            return False
    else:
        # Default behavior: find first non-hidden page in pageOrder
        for page_id in page_order:
            if page_id in page_map:
                _, page_data = page_map[page_id]
                if page_data.get("visibility") != "HiddenInViewMode":
                    target_page_id = page_id
                    target_page_display_name = page_data.get("displayName", page_id)
                    break

        # Fallback if all are hidden
        if target_page_id is None:
            target_page_id = page_order[0]
            if target_page_id in page_map:
                _, fallback_page_data = page_map[target_page_id]
                target_page_display_name = fallback_page_data.get(
                    "displayName", target_page_id
                )
            else:
                target_page_display_name = target_page_id
            console.print_warning(
                f"Warning: All pages are hidden. Defaulting to first page: '{target_page_display_name}' ({target_page_id})"
            )

    if target_page_id != current_active_page:
        pages_data["activePageName"] = target_page_id
        if not dry_run:
            write_json(str(pages_json_path), pages_data)
        if summary:
            if dry_run:
                console.print_dry_run(
                    f"Would set '{target_page_display_name}' as active."
                )
            else:
                console.print_success(f"Set '{target_page_display_name}' as active.")
        else:
            if dry_run:
                console.print_dry_run(
                    f"Would set '{target_page_display_name}' ({target_page_id}) as the active page."
                )
            else:
                console.print_success(
                    f"Set '{target_page_display_name}' ({target_page_id}) as the active page."
                )
        return True
    else:
        console.print_info(
            f"No changes needed. '{target_page_display_name}' ({target_page_id}) is already set as active."
        )
        return False


def set_first_page_as_active(
    report_path: str, dry_run: bool = False, summary: bool = False
) -> bool:
    """
    Set the first non-hidden page of the report as active. (Deprecated: use set_active_page instead)
    """
    return set_active_page(report_path, page=None, dry_run=dry_run, summary=summary)


def set_page_order(
    report_path: str,
    page_order: list[str],
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Set the specific order of pages in the report.

    Args:
        report_path (str): The path to the report.
        page_order (list[str]): List of page names or displayNames in the desired order.
        dry_run (bool): Whether to perform a dry run.
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading("Setting page order", dry_run)
    pages_dir = Path(report_path) / "definition" / "pages"
    pages_json_path = pages_dir / "pages.json"

    if not pages_json_path.exists():
        console.print_warning("No pages.json found.")
        return False

    pages_data = load_json(str(pages_json_path))
    current_order = pages_data.get("pageOrder", [])

    if not current_order:
        console.print_warning("Report has no pages in pageOrder.")
        return False

    page_map = {}
    for page_id, folder_path, page_data in iter_pages(report_path):
        page_name = page_data.get("name", page_id)
        page_display_name = page_data.get("displayName", page_id)
        # Store lowercase to make matching case-insensitive, but also store original
        page_map[page_name.lower()] = page_id
        page_map[page_display_name.lower()] = page_id
        page_map[page_id.lower()] = page_id

    resolved_order = []
    missing_pages = []

    for p in page_order:
        p_lower = p.lower()
        if p_lower in page_map:
            resolved_id = page_map[p_lower]
            if resolved_id not in resolved_order:
                resolved_order.append(resolved_id)
        else:
            missing_pages.append(p)

    if missing_pages:
        console.print_error(
            f"Could not resolve the following pages: {', '.join(missing_pages)}"
        )
        console.print_warning("Page order update aborted.")
        return False

    # Append any unspecified pages to the end to prevent orphaning them
    for current_id in current_order:
        if current_id not in resolved_order:
            resolved_order.append(current_id)

    if current_order == resolved_order:
        console.print_info("No changes needed. Page order is already matching.")
        return False

    pages_data["pageOrder"] = resolved_order
    if not dry_run:
        write_json(str(pages_json_path), pages_data)

    if summary:
        if dry_run:
            console.print_dry_run("Would reorder pages.")
        else:
            console.print_success("Reordered pages.")
    else:
        if dry_run:
            console.print_dry_run("Would update pageOrder.")
        else:
            console.print_success("Updated pageOrder.")

    return True


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
    pages_dir = Path(report_path) / "definition" / "pages"
    pages_json_path = pages_dir / "pages.json"
    pages_data = load_json(str(pages_json_path))

    page_order = pages_data.get("pageOrder", [])
    active_page_name = pages_data.get("activePageName")

    page_id_to_folder = {}
    folder_to_page_id = {}

    for page_id, folder_path, page_data in iter_pages(report_path):
        page_id_to_folder[page_id] = folder_path
        folder_name = Path(folder_path).name
        folder_to_page_id[folder_name] = page_id

    non_empty_pages = []
    for page_id in page_order:
        if page_id in page_id_to_folder:
            folder_path = page_id_to_folder[page_id]
            visuals_dir = Path(folder_path) / "visuals"

            has_visuals = False
            if visuals_dir.exists() and any(visuals_dir.iterdir()):
                has_visuals = True

            if has_visuals:
                non_empty_pages.append(page_id)

    if non_empty_pages:
        pages_data["pageOrder"] = non_empty_pages
        if active_page_name not in non_empty_pages:
            pages_data["activePageName"] = non_empty_pages[0]
    else:
        if not page_order:
            console.print_warning(
                "No pages found in the report. Attempting to preserve original state."
            )
            return False

        first_page_id = page_order[0]
        pages_data["pageOrder"] = [first_page_id]
        pages_data["activePageName"] = first_page_id
        non_empty_pages.append(first_page_id)
        console.print_warning(
            "All pages were empty. Keeping the first page as a placeholder."
        )

    if not dry_run:
        write_json(str(pages_json_path), pages_data)

    folders_to_remove = []
    existing_folders = [f.name for f in pages_dir.iterdir() if f.is_dir()]

    for folder_name in existing_folders:
        page_id = folder_to_page_id.get(folder_name)

        if not page_id:
            folders_to_remove.append(folder_name)
        elif page_id not in non_empty_pages:
            folders_to_remove.append(folder_name)

    if folders_to_remove:
        for folder in folders_to_remove:
            folder_path = pages_dir / folder
            if not dry_run:
                shutil.rmtree(str(folder_path))
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

    pages_dir = Path(report_path) / "definition" / "pages"
    modified_count = 0

    if not pages_dir.exists():
        console.print_warning("No pages directory found.")
        return False

    for page_id, folder_path, page_data in iter_pages(report_path):
        page_json_path = Path(folder_path) / "page.json"
        folder_name = Path(folder_path).name

        if exclude_tooltip and page_data.get("type") == "Tooltip":
            if not summary:
                console.print_info(
                    f"Skipping tooltip page: {page_data.get('displayName', folder_name)}"
                )
            continue

        current_width = page_data.get("width")
        current_height = page_data.get("height")

        if current_width != width or current_height != height:
            page_data["width"] = width
            page_data["height"] = height

            if not dry_run:
                write_json(str(page_json_path), page_data)

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
    exclude_types: list[str] = None,
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Set the display option for pages in the report.

    Args:
        report_path (str): The path to the report.
        display_option (str): Display option to set ("ActualSize", "FitToPage", "FitToWidth").
        page (str): Page name or displayName to filter. None applies to all pages.
        exclude_types (list[str]): List of page types to exclude (e.g., ["Tooltip"]).
        dry_run (bool): Perform a dry run without making changes.
        summary (bool): Show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
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

    pages_dir = Path(report_path) / "definition" / "pages"
    modified_count = 0

    if not pages_dir.exists():
        console.print_warning("No pages directory found.")
        return False

    for page_id, folder_path, page_data in iter_pages(report_path):
        page_json_path = Path(folder_path) / "page.json"
        folder_name = Path(folder_path).name

        # Check if this page matches the filter (by name or displayName)
        if page is not None:
            page_name = page_data.get("name", "")
            page_display_name = page_data.get("displayName", "")
            if page != page_name and page != page_display_name:
                continue

        # Check if page type is excluded
        if exclude_types:
            page_type = page_data.get("type")
            if page_type in exclude_types:
                if not summary:
                    console.print_info(
                        f"Skipping page '{page_data.get('displayName', folder_name)}' (Type: {page_type})"
                    )
                continue

        current_option = page_data.get("displayOption")

        if current_option != display_option:
            page_data["displayOption"] = display_option

            if not dry_run:
                write_json(str(page_json_path), page_data)

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


def remove_unused_hidden_pages(
    report_path: str,
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Remove hidden pages that are not used as tooltips, drillthroughs,
    page navigation targets, or referenced in active bookmarks.

    Args:
        report_path (str): Path to the report.
        dry_run (bool): Preview changes without modifying files.
        summary (bool): Show summary instead of detailed messages.

    Returns:
        bool: True if any pages were/would be removed.
    """
    console.print_action_heading("Removing unused hidden pages", dry_run)

    pages_dir = Path(report_path) / "definition" / "pages"
    pages_json_path = pages_dir / "pages.json"
    bookmarks_dir = Path(report_path) / "definition" / "bookmarks"
    bookmarks_json_path = bookmarks_dir / "bookmarks.json"

    if not pages_json_path.exists():
        console.print_info("No pages found.")
        return False

    pages_data = load_json(pages_json_path)
    page_order = pages_data.get("pageOrder", [])
    active_page = pages_data.get("activePageName", "")

    # 1. Collect hidden pages and build initial protected set
    hidden_pages = {}  # page_id -> displayName
    protected_pages = set()

    # Protect active page
    if active_page:
        protected_pages.add(active_page)

    for page_id, page_folder, page_data in iter_pages(report_path):
        if page_data.get("visibility") == "HiddenInViewMode":
            hidden_pages[page_id] = page_data.get("displayName", page_id)

        # Check page bindings/types (tooltips/drillthroughs)
        binding_type = page_data.get("pageBinding", {}).get("type", "")
        page_type = page_data.get("type", "")
        if page_type == "Tooltip" or binding_type in ("Tooltip", "Drillthrough"):
            protected_pages.add(page_id)

    if not hidden_pages:
        console.print_info("No hidden pages found.")
        return False

    # Scan visuals for page navigation and tooltip section references
    # Also collect used bookmark references
    used_bookmark_names = set()
    all_bookmarks_used = False

    for _, page_folder, _ in iter_pages(report_path):
        for _, _, visual_data in iter_visuals(page_folder):
            visual = visual_data.get("visual", {})
            visual_type = visual.get("visualType", "")

            # Check bookmark navigators
            if visual_type == "bookmarkNavigator":
                for bookmark in visual.get("objects", {}).get("bookmarks", []):
                    props = bookmark.get("properties", {})
                    if "bookmarkGroup" not in props:
                        all_bookmarks_used = True
                    else:
                        val = (
                            props.get("bookmarkGroup", {})
                            .get("expr", {})
                            .get("Literal", {})
                            .get("Value")
                        )
                        if val is not None and val.strip("'") == "":
                            all_bookmarks_used = True
                        elif val:
                            used_bookmark_names.add(val.strip("'"))

            # Check visual links (for page nav and bookmark actions)
            vco = visual.get("visualContainerObjects", {})
            for link in vco.get("visualLink", []):
                props = link.get("properties", {})

                # Bookmark links
                bm_val = (
                    props.get("bookmark", {})
                    .get("expr", {})
                    .get("Literal", {})
                    .get("Value")
                )
                if bm_val:
                    used_bookmark_names.add(bm_val.strip("'"))

                # Page navigation links
                nav_val = (
                    props.get("navigationSection", {})
                    .get("expr", {})
                    .get("Literal", {})
                    .get("Value")
                )
                if nav_val:
                    protected_pages.add(nav_val.strip("'"))

            # Check tooltip sections
            for tooltip in vco.get("visualTooltip", []):
                section_val = (
                    tooltip.get("properties", {})
                    .get("section", {})
                    .get("expr", {})
                    .get("Literal", {})
                    .get("Value")
                )
                if section_val:
                    target = section_val.strip("'")
                    if target != "___AUTO___":
                        protected_pages.add(target)

    # Scan bookmarks to find page references (only for "used" bookmarks)
    if bookmarks_dir.exists():
        for file_path_str in walk_json_files(bookmarks_dir, ".json"):
            file_path = Path(file_path_str)
            if file_path.name == "bookmarks.json" or not file_path.name.endswith(
                ".bookmark.json"
            ):
                continue

            bd = load_json(file_path)
            bookmark_name = bd.get("name")
            if all_bookmarks_used or bookmark_name in used_bookmark_names:
                state = bd.get("explorationState", {})
                active_sec = state.get("activeSection")
                if active_sec:
                    protected_pages.add(active_sec)

                sections_dict = state.get("sections", {})
                if sections_dict:
                    protected_pages.update(sections_dict.keys())

    # 3. Identify removable pages
    removable_pages = {
        pid: name for pid, name in hidden_pages.items() if pid not in protected_pages
    }

    if not removable_pages:
        console.print_info("No unused hidden pages found.")
        return False

    # 4. Process removals
    for page_id, display_name in removable_pages.items():
        if dry_run:
            if not summary:
                console.print_dry_run(
                    f"Would remove hidden page: {display_name} ({page_id})"
                )
        else:
            if not summary:
                console.print_success(
                    f"Removed hidden page: {display_name} ({page_id})"
                )

            # Remove from pageOrder
            if page_id in page_order:
                page_order.remove(page_id)

            # Delete folder
            page_folder = pages_dir / page_id
            if page_folder.exists() and page_folder.is_dir():
                shutil.rmtree(page_folder)

    # Save pages.json
    if not dry_run and removable_pages:
        pages_data["pageOrder"] = page_order
        write_json(pages_json_path, pages_data)

    # Clean up bookmarks referencing removed pages (even if they were unused)
    if not dry_run and bookmarks_dir.exists():
        bookmarks_index = (
            load_json(bookmarks_json_path) if bookmarks_json_path.exists() else None
        )

        for file_path_str in walk_json_files(bookmarks_dir, ".json"):
            file_path = Path(file_path_str)
            if file_path.name == "bookmarks.json" or not file_path.name.endswith(
                ".bookmark.json"
            ):
                continue

            bd = load_json(file_path)
            state = bd.get("explorationState", {})
            active_sec = state.get("activeSection")
            sections_dict = state.get("sections", {})

            needs_save = False
            file_deleted = False

            # If the active section is a removed page, this bookmark is totally invalid
            if active_sec in removable_pages:
                file_path.unlink()
                file_deleted = True
                if bookmarks_index and "items" in bookmarks_index:
                    bookmarks_index["items"] = [
                        item
                        for item in bookmarks_index["items"]
                        if item.get("name") != bd.get("name")
                    ]
            elif sections_dict:
                # Remove sections pointing to removed pages
                for pid in list(sections_dict.keys()):
                    if pid in removable_pages:
                        del sections_dict[pid]
                        needs_save = True

            if needs_save and not file_deleted:
                write_json(file_path, bd)

        if bookmarks_index:
            write_json(bookmarks_json_path, bookmarks_index)

        # If bookmarks dir has no remaining items, remove the whole dir
        if bookmarks_index is not None and not bookmarks_index.get("items"):
            if bookmarks_dir.exists():
                shutil.rmtree(bookmarks_dir)

    # Summary formatting
    if summary:
        msg = f"Removed {len(removable_pages)} unused hidden page(s)."
        if dry_run:
            console.print_dry_run("Would " + msg.lower())
        else:
            console.print_success(msg)

    return True
