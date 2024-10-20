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
    Remove unused bookmarks from the report.

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

    Args:
        report_path (str): The path to the report.

    Returns:
        None
    """
    print("Action: Removing hidden visuals that are never shown using bookmarks")

    def _find_hidden_visuals(visual_data: dict, file_path: str) -> tuple:
        if visual_data.get("isHidden", False):  # check if visual is hidden
            visual_name = visual_data.get("name")
            if visual_name:
                return (
                    visual_name,
                    os.path.dirname(os.path.dirname(file_path)),
                )  # return visual name and page folder
        return None

    hidden_visuals_results = _process_or_check_json_files(
        os.path.join(report_path, "definition", "pages"),
        "visual.json",
        _find_hidden_visuals,
    )
    hidden_visuals = {result[1][0]: result[1][1] for result in hidden_visuals_results}

    def _check_bookmark(bookmark_data: dict, _: str) -> set:
        shown_visuals = set()
        sections = bookmark_data.get("explorationState", {}).get("sections", {})
        for section in sections.values():
            visual_containers = section.get("visualContainers", {})
            for visual_name, container in visual_containers.items():
                if visual_name in hidden_visuals:
                    if "display" not in container.get(
                        "singleVisual", {}
                    ):  # check if visual is set to display in bookmark
                        shown_visuals.add(visual_name)
        return shown_visuals

    bookmark_results = _process_or_check_json_files(
        os.path.join(report_path, "definition", "bookmarks"),
        ".bookmark.json",
        _check_bookmark,
    )
    shown_visuals = set().union(*[result[1] for result in bookmark_results])

    always_hidden_visuals = set(hidden_visuals.keys()) - shown_visuals

    for visual_name in always_hidden_visuals:
        visual_folder = hidden_visuals.get(visual_name)
        if visual_folder and os.path.exists(visual_folder):
            shutil.rmtree(visual_folder)
            print(f"Removed always hidden visual: {visual_name}")

    def _update_bookmark(bookmark_data: dict, _: str) -> bool:
        updated = False
        sections = bookmark_data.get("explorationState", {}).get("sections", {})
        for section in sections.values():
            visual_containers = section.get("visualContainers", {})
            for visual_name in always_hidden_visuals:
                if visual_name in visual_containers:
                    del visual_containers[visual_name]
                    updated = True
        return updated

    bookmarks_updated = _process_or_check_json_files(
        os.path.join(report_path, "definition", "bookmarks"),
        ".bookmark.json",
        _update_bookmark,
        process=True,
    )

    print(
        f"Removed {len(always_hidden_visuals)} hidden visuals that are never shown using bookmarks"
    )
    print(f"Updated {bookmarks_updated} bookmark files")


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
    }

    for action in actions:
        if action in action_map:
            action_map[action](report_path)
        else:
            print(f"Warning: Unknown action '{action}' skipped.")

    print("Power BI report sanitization completed.")
