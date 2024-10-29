from .pbir_measure_utils import remove_measures
from .json_utils import _load_json, _write_json
import os
import shutil


def _walk_json_files(directory: str, file_pattern: str):
    """
    Walk through JSON files in a directory matching a specific pattern.

    Args:
        directory (str): The directory to search in.
        file_pattern (str): The file pattern to match.

    Yields:
        str: The full path of each matching file.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(file_pattern):
                yield os.path.join(root, file)


def _process_or_check_json_files(
    directory: str, file_pattern: str, func: callable, process: bool = False
) -> list:
    """
    Process or check JSON files in a directory.

    Args:
        directory (str): The directory to search in.
        file_pattern (str): The file pattern to match.
        func (callable): The function to apply to each file's data.
        process (bool): Whether to process the files or just check.

    Returns:
        list: A list of results or the count of modified files.
    """
    results = []
    modified_count = 0
    for file_path in _walk_json_files(directory, file_pattern):
        data = _load_json(file_path)
        result = func(data, file_path)
        if process and result:
            _write_json(file_path, data)
            modified_count += 1
        elif not process and result:
            results.append((file_path, result))
    return modified_count if process else results


def remove_unused_measures(report_path: str) -> None:
    """
    Remove unused measures from the report.

    Args:
        report_path (str): The path to the report.

    Returns:
        None
    """
    print("Action: Removing unused measures")
    remove_measures(report_path, check_visual_usage=True)


def remove_unused_bookmarks(report_path: str) -> None:
    """
    Remove bookmarks which are not activated in report using bookmark navigator or actions

    Args:
        report_path (str): The path to the report.

    Returns:
        None
    """
    print("Action: Removing unused bookmarks")

    bookmarks_dir = os.path.join(report_path, "definition", "bookmarks")
    bookmarks_json_path = os.path.join(bookmarks_dir, "bookmarks.json")
    bookmarks_data = _load_json(bookmarks_json_path)

    def _is_bookmark_used(bookmark_name: str) -> bool:
        """
        Check if a bookmark is used in the report.

        Args:
            bookmark_name (str): The name of the bookmark.

        Returns:
            bool: True if the bookmark is used, False otherwise.
        """

        def _check_visual(visual_data: dict, _: str) -> str:
            visual = visual_data.get("visual", {})
            if (
                visual.get("visualType") == "bookmarkNavigator"
            ):  # check if bookmark is used in bookmark navigator
                bookmarks_obj = visual.get("objects", {}).get("bookmarks", [])
                return any(
                    bookmark.get("properties", {})
                    .get("bookmarkGroup", {})
                    .get("expr", {})
                    .get("Literal", {})
                    .get("Value")
                    == f"'{bookmark_name}'"
                    for bookmark in bookmarks_obj
                )
            visual_link = visual.get("visualContainerObjects", {}).get(
                "visualLink", []
            )  # check if bookmark is used in visual link
            return any(
                link.get("properties", {})
                .get("bookmark", {})
                .get("expr", {})
                .get("Literal", {})
                .get("Value")
                == f"'{bookmark_name}'"
                for link in visual_link
            )

        return any(
            result[1]
            for result in _process_or_check_json_files(
                os.path.join(report_path, "definition", "pages"),
                "visual.json",
                _check_visual,
            )
        )

    used_bookmarks = set()
    new_items = []
    for item in bookmarks_data["items"]:
        if _is_bookmark_used(
            item["name"]
        ):  # if bookmark is used, add it to used_bookmarks set
            used_bookmarks.add(item["name"])
            new_items.append(item)
            if "children" in item:
                used_bookmarks.update(item["children"])
        elif "children" in item:  # if bookmark has children
            used_children = [
                child for child in item["children"] if _is_bookmark_used(child)
            ]
            if used_children:
                item["children"] = used_children
                used_bookmarks.update(used_children)
                used_bookmarks.add(item["name"])
                new_items.append(item)

    removed_bookmarks = len(bookmarks_data["items"]) - len(new_items)
    bookmarks_data["items"] = new_items

    for filename in os.listdir(bookmarks_dir):
        if filename.endswith(".bookmark.json"):
            bookmark_file_data = _load_json(os.path.join(bookmarks_dir, filename))
            if (
                bookmark_file_data.get("name") not in used_bookmarks
            ):  # remove bookmark file if not used
                os.remove(os.path.join(bookmarks_dir, filename))
                print(f"Removed unused bookmark file: {filename}")

    _write_json(bookmarks_json_path, bookmarks_data)

    if not bookmarks_data["items"]:  # if no bookmarks left, remove the directory
        shutil.rmtree(bookmarks_dir)
        print("Removed empty bookmarks folder")
    else:
        print(f"Removed {removed_bookmarks} unused bookmarks")


def remove_unused_custom_visuals(report_path: str) -> None:
    """
    Remove unused custom visuals from the report.

    Args:
        report_path (str): The path to the report.

    Returns:
        None
    """
    print("Action: Removing unused custom visuals")

    report_json_path = os.path.join(report_path, "definition", "report.json")
    report_data = _load_json(report_json_path)

    custom_visuals = set(report_data.get("publicCustomVisuals", []))
    if not custom_visuals:
        print("No custom visuals found in the report.")
        return

    def _check_visual(visual_data: dict, _: str) -> str:
        visual_type = visual_data.get("visual", {}).get("visualType")
        return visual_type if visual_type in custom_visuals else None

    used_visuals = set(
        result[1]
        for result in _process_or_check_json_files(
            os.path.join(report_path, "definition", "pages"),
            "visual.json",
            _check_visual,
        )
    )

    unused_visuals = custom_visuals - used_visuals
    if unused_visuals:
        report_data["publicCustomVisuals"] = (
            list(used_visuals)
            if used_visuals
            else report_data.pop("publicCustomVisuals", None)
        )
        _write_json(report_json_path, report_data)
        print(f"Removed unused custom visuals: {', '.join(unused_visuals)}")
    else:
        print("No unused custom visuals found.")


def disable_show_items_with_no_data(report_path: str) -> None:
    """
    Disable the 'Show items with no data' option for visuals.

    Args:
        report_path (str): The path to the report.

    Returns:
        None
    """
    print("Action: Disabling 'Show items with no data'")

    def _remove_show_all(data: dict, _: str) -> bool:
        if isinstance(data, dict):
            if "showAll" in data:
                del data["showAll"]
                return True
            return any(_remove_show_all(value, _) for value in data.values())
        elif isinstance(data, list):
            return any(_remove_show_all(item, _) for item in data)
        return False

    visuals_modified = _process_or_check_json_files(
        os.path.join(report_path, "definition", "pages"),
        "visual.json",
        _remove_show_all,
        process=True,
    )

    if visuals_modified > 0:
        print(f"Disabled 'Show items with no data' for {visuals_modified} visual(s).")
    else:
        print("No visuals found with 'Show items with no data' enabled.")


def hide_tooltip_drillthrough_pages(report_path: str) -> None:
    """
    Hide tooltip and drillthrough pages in the report.

    Args:
        report_path (str): The path to the report.

    Returns:
        None
    """
    print("Action: Hiding tooltip drillthrough pages")

    def _check_page(page_data: dict, _: str) -> str:
        page_binding = page_data.get("pageBinding", {})
        binding_type = page_binding.get("type")

        if (
            binding_type in ["Tooltip", "Drillthrough"]
            and page_data.get("visibility") != "HiddenInViewMode"
        ):
            return page_data.get("displayName", "Unnamed Page")
        return None

    results = _process_or_check_json_files(
        os.path.join(report_path, "definition", "pages"), "page.json", _check_page
    )

    for file_path, page_name in results:
        page_data = _load_json(file_path)
        page_data["visibility"] = "HiddenInViewMode"
        _write_json(file_path, page_data)
        print(f"Hidden page: {page_name}")

    if results:
        print(f"Hidden {len(results)} tooltip/drillthrough page(s).")
    else:
        print("No tooltip/drillthrough pages found that needed hiding.")


def set_first_page_as_active(report_path: str) -> None:
    """
    Set the first page of the report as active.

    Args:
        report_path (str): The path to the report.

    Returns:
        None
    """
    print("Action: Setting the first page as active")
    pages_dir = os.path.join(report_path, "definition", "pages")
    pages_json_path = os.path.join(pages_dir, "pages.json")
    pages_data = _load_json(pages_json_path)

    page_order = pages_data["pageOrder"]
    current_active_page = pages_data.get("activePageName")

    if page_order[0] != current_active_page:
        pages_data["activePageName"] = page_order[0]
        _write_json(pages_json_path, pages_data)
        print(f"Set '{page_order[0]}' as the active page.")
    else:
        print("No changes needed. The first page is already set as active.")


def remove_empty_pages(report_path: str) -> None:
    """
    Remove empty pages and clean up rogue folders in the report.

    Args:
        report_path (str): The path to the report.

    Returns:
        None
    """
    print("Action: Removing empty pages and cleaning up rogue folders")
    pages_dir = os.path.join(report_path, "definition", "pages")
    pages_json_path = os.path.join(pages_dir, "pages.json")
    pages_data = _load_json(pages_json_path)

    page_order = pages_data.get("pageOrder", [])
    active_page_name = pages_data.get("activePageName")

    non_empty_pages = [
        page
        for page in page_order
        if os.path.exists(
            os.path.join(pages_dir, page, "visuals")
        )  # check if page has visuals folder
        and os.listdir(
            os.path.join(pages_dir, page, "visuals")
        )  # check if visuals folder is not empty
    ]

    if non_empty_pages:
        pages_data["pageOrder"] = non_empty_pages
        if active_page_name not in non_empty_pages:
            pages_data["activePageName"] = non_empty_pages[0]
    else:
        pages_data["pageOrder"] = [page_order[0]]
        pages_data["activePageName"] = page_order[0]
        print("All pages were empty. Keeping the first page as a placeholder.")

    _write_json(pages_json_path, pages_data)

    existing_folders = set(os.listdir(pages_dir)) - {"pages.json"}
    folders_to_keep = set(pages_data["pageOrder"])
    folders_to_remove = existing_folders - folders_to_keep

    if folders_to_remove:
        print(f"Removing empty and rogue page folders: {', '.join(folders_to_remove)}")
        for folder in folders_to_remove:
            folder_path = os.path.join(pages_dir, folder)
            if os.path.isdir(folder_path):
                shutil.rmtree(folder_path)
                print(f"Removed folder: {folder}")
    else:
        print("No empty or rogue page folders found.")


def remove_hidden_visuals_never_shown(report_path: str) -> None:
    """
    Remove hidden visuals that are never shown using bookmarks.
    Also removes hidden visual groups and their children.

    Args:
        report_path (str): The path to the report.

    Returns:
        None
    """
    print("Action: Removing hidden visuals that are never shown using bookmarks")

    def _find_hidden_visuals(visual_data: dict, file_path: str) -> tuple:
        visual_name = visual_data.get("name")
        folder = os.path.dirname(file_path)

        if visual_data.get("isHidden", False):
            if visual_data.get("visualGroup"):
                return (visual_name, folder, "group")
            return (visual_name, folder, "hidden")
        elif visual_data.get("parentGroupName"):
            return (visual_name, folder, ("child", visual_data["parentGroupName"]))
        return None

    hidden_visuals_results = _process_or_check_json_files(
        os.path.join(report_path, "definition", "pages"),
        "visual.json",
        _find_hidden_visuals,
    )

    # Initialize dictionaries to store our findings
    hidden_groups = {}  # group_name -> folder
    group_children = {}  # group_name -> set of child visual names
    hidden_visuals = {}  # visual_name -> folder

    # Process results
    for result in hidden_visuals_results:
        if result[1]:  # if we got a result
            visual_name, folder, info = result[1]
            if info == "group":
                hidden_groups[visual_name] = folder
            elif isinstance(info, tuple) and info[0] == "child":
                parent_group = info[1]
                if parent_group not in group_children:
                    group_children[parent_group] = set()
                group_children[parent_group].add(visual_name)
            elif info == "hidden":
                hidden_visuals[visual_name] = folder

    def _check_bookmark(bookmark_data: dict, _: str) -> tuple[set, set]:
        shown_visuals = set()
        shown_groups = set()

        for section in (
            bookmark_data.get("explorationState", {}).get("sections", {}).values()
        ):
            # Check groups
            for group_name, group_info in section.get(
                "visualContainerGroups", {}
            ).items():
                if not group_info.get("isHidden", False):
                    shown_groups.add(group_name)

            # Check visuals
            for visual_name, container in section.get("visualContainers", {}).items():
                if (
                    not container.get("singleVisual", {}).get("display", {}).get("mode")
                    == "hidden"
                ):
                    shown_visuals.add(visual_name)

        return shown_visuals, shown_groups

    # Get shown visuals from bookmarks
    shown_visuals = set()
    shown_groups = set()
    for _, result in _process_or_check_json_files(
        os.path.join(report_path, "definition", "bookmarks"),
        ".bookmark.json",
        _check_bookmark,
    ):
        if result:
            vis, grp = result
            shown_visuals.update(vis)
            shown_groups.update(grp)

    # Determine visuals to remove
    visuals_to_remove = set()

    # Add always-hidden groups and their children
    for group in set(hidden_groups) - shown_groups:
        visuals_to_remove.add(group)
        visuals_to_remove.update(group_children.get(group, set()))

    # Add hidden visuals never shown (excluding children of shown groups)
    for visual in hidden_visuals:
        if visual not in shown_visuals and not any(
            visual in group_children.get(group, set()) for group in shown_groups
        ):
            visuals_to_remove.add(visual)

    # Remove the visuals
    for visual_name in visuals_to_remove:
        # Get folder from hidden_groups or hidden_visuals_results
        folder = hidden_groups.get(visual_name)
        if not folder:
            folder = next(
                (
                    result[1][1]
                    for result in hidden_visuals_results
                    if result[1] and result[1][0] == visual_name
                ),
                None,
            )
        
        if folder and os.path.exists(folder):
            # Remove visual interactions for the visual
            page_json_path = os.path.join(os.path.dirname(folder), "page.json")
            if os.path.exists(page_json_path):
                page_data = _load_json(page_json_path)
                visual_interactions = page_data.get("visualInteractions", [])
                new_interactions = []
                for interaction in visual_interactions:
                    if (
                        interaction.get("source") != visual_name
                        and interaction.get("target") != visual_name
                    ):
                        new_interactions.append(interaction)
                if len(new_interactions) != len(visual_interactions):
                    page_data["visualInteractions"] = new_interactions
                    _write_json(page_json_path, page_data)
                    print(
                        f"Removed visual interactions for {visual_name} from {page_json_path}"
                    )
            # Remove the visual folder
            shutil.rmtree(folder)
            visual_type = "group" if visual_name in hidden_groups else "visual"
            print(f"Removed {visual_type}: {visual_name}")

    # Update bookmarks
    def _update_bookmark(bookmark_data: dict, _: str) -> bool:
        updated = False
        for section in (
            bookmark_data.get("explorationState", {}).get("sections", {}).values()
        ):
            for container_type in ["visualContainers", "visualContainerGroups"]:
                containers = section.get(container_type, {})
                for name in list(containers.keys()):
                    if name in visuals_to_remove:
                        del containers[name]
                        updated = True
        return updated

    # Update bookmarks to remove references to removed visuals
    bookmarks_updated = _process_or_check_json_files(
        os.path.join(report_path, "definition", "bookmarks"),
        ".bookmark.json",
        _update_bookmark,
        process=True,
    )

    print(
        f"Removed {len(visuals_to_remove)} visuals (including groups and their children)"
    )
    print(f"Updated {bookmarks_updated} bookmark files")


def cleanup_invalid_bookmarks(report_path: str) -> None:
    """
    Clean up invalid bookmarks that reference non-existent pages or visuals.

    Args:
        report_path (str): The path to the report.

    Returns:
        None
    """
    print("Action: Cleaning up invalid bookmarks")

    bookmarks_dir = os.path.join(report_path, "definition", "bookmarks")
    if not os.path.exists(bookmarks_dir):
        print("No bookmarks directory found.")
        return

    # Load pages.json to get valid page names
    pages_json_path = os.path.join(report_path, "definition", "pages", "pages.json")
    pages_data = _load_json(pages_json_path)
    valid_pages = set(pages_data.get("pageOrder", []))

    # Track bookmarks to remove globally
    bookmarks_to_remove = set()
    stats = {"processed": 0, "removed": 0, "cleaned": 0, "updated": 0}

    def _process_bookmark(bookmark_data: dict, file_path: str) -> bool:
        """Process a single bookmark file. Returns was_modified flag."""
        active_section = bookmark_data.get("explorationState", {}).get("activeSection")
        if active_section not in valid_pages:
            bookmarks_to_remove.add(bookmark_data.get("name"))
            stats["removed"] += 1
            stats["processed"] += 1
            os.remove(file_path)
            return False

        was_modified = False
        cleaned_visuals_count = 0
        sections = bookmark_data.get("explorationState", {}).get("sections", {})

        sections_to_remove = []
        for section_name, section_data in sections.items():
            if section_name not in valid_pages:
                sections_to_remove.append(section_name)
                was_modified = True
                continue

            # Get valid visuals for this page
            valid_visuals = {
                result[1]
                for result in _process_or_check_json_files(
                    os.path.join(
                        report_path, "definition", "pages", section_name, "visuals"
                    ),
                    "visual.json",
                    lambda data, _: data.get("name"),
                )
                if result[1]
            }

            # Clean up containers and groups
            for section_key in ["visualContainers", "visualContainerGroups"]:
                containers = section_data.get(section_key, {})
                invalid_items = [id for id in containers if id not in valid_visuals]
                if invalid_items:
                    was_modified = True
                    for id in invalid_items:
                        del containers[id]
                        cleaned_visuals_count += 1
                    if not containers and section_key in section_data:
                        del section_data[section_key]

            if not section_data:
                sections_to_remove.append(section_name)
                was_modified = True

        for section_name in sections_to_remove:
            del sections[section_name]

        if was_modified:
            stats["updated"] += 1
            stats["cleaned"] += cleaned_visuals_count
            stats["processed"] += 1

        return was_modified

    # Process all bookmark files
    _process_or_check_json_files(
        bookmarks_dir, ".bookmark.json", _process_bookmark, process=True
    )

    # Update bookmarks.json
    bookmarks_json_path = os.path.join(bookmarks_dir, "bookmarks.json")
    bookmarks_data = _load_json(bookmarks_json_path)

    def _cleanup_bookmark_items(items: list) -> list:
        """Recursively clean up bookmark items."""
        cleaned_items = []
        for item in items:
            if "children" in item:
                item["children"] = [
                    child
                    for child in item["children"]
                    if child not in bookmarks_to_remove
                ]
                if item["children"] or item["name"] not in bookmarks_to_remove:
                    cleaned_items.append(item)
            elif item["name"] not in bookmarks_to_remove:
                cleaned_items.append(item)
        return cleaned_items

    bookmarks_data["items"] = _cleanup_bookmark_items(bookmarks_data["items"])

    # Final cleanup and reporting
    if not bookmarks_data["items"]:
        shutil.rmtree(bookmarks_dir)
        print("Removed empty bookmarks directory")
    else:
        if stats["processed"] > 0:
            print(f"Processed {stats['processed']} bookmark files:")
            if stats["removed"] > 0:
                _write_json(bookmarks_json_path, bookmarks_data)
                print(f"- Removed {stats['removed']} invalid bookmarks")
            if stats["cleaned"] > 0:
                print(f"- Cleaned {stats['cleaned']} invalid visual references")
            if stats["updated"] > 0:
                print(f"- Updated {stats['updated']} bookmark files")
        else:
            print("No invalid bookmarks or references found.")


def sanitize_powerbi_report(report_path: str, actions: list[str]) -> None:
    """
    Sanitize a Power BI report by performing specified actions.

    Args:
        report_path (str): The file system path to the report folder.
        actions (list[str]): The sanitization actions to perform.

    Returns:
        None
    """
    action_map = {
        "remove_unused_measures": remove_unused_measures,
        "remove_unused_bookmarks": remove_unused_bookmarks,
        "remove_unused_custom_visuals": remove_unused_custom_visuals,
        "disable_show_items_with_no_data": disable_show_items_with_no_data,
        "hide_tooltip_drillthrough_pages": hide_tooltip_drillthrough_pages,
        "set_first_page_as_active": set_first_page_as_active,
        "remove_empty_pages": remove_empty_pages,
        "remove_hidden_visuals_never_shown": remove_hidden_visuals_never_shown,
        "cleanup_invalid_bookmarks": cleanup_invalid_bookmarks,
    }

    for action in actions:
        if action in action_map:
            action_map[action](report_path)
        else:
            print(f"Warning: Unknown action '{action}' skipped.")

    print("Power BI report sanitization completed.")
