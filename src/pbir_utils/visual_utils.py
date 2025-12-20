"""
Visual utilities for Power BI report sanitization.

Contains functions for managing visuals in PBIR reports.
"""

import os
import shutil

from .common import load_json, write_json, process_json_files
from .console_utils import console


def remove_unused_custom_visuals(
    report_path: str, dry_run: bool = False, summary: bool = False
) -> bool:
    """
    Remove unused custom visuals from the report.

    Args:
        report_path (str): The path to the report.
        dry_run (bool): Whether to perform a dry run.
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading("Removing unused custom visuals", dry_run)

    report_json_path = os.path.join(report_path, "definition", "report.json")
    report_data = load_json(report_json_path)

    custom_visuals = set(report_data.get("publicCustomVisuals", []))
    if not custom_visuals:
        console.print_info("No custom visuals found in the report.")
        return False

    def _check_visual(visual_data: dict, _: str) -> str:
        visual_type = visual_data.get("visual", {}).get("visualType")
        return visual_type if visual_type in custom_visuals else None

    used_visuals = set(
        result[1]
        for result in process_json_files(
            directory=os.path.join(report_path, "definition", "pages"),
            file_pattern="visual.json",
            func=_check_visual,
        )
    )

    unused_visuals = custom_visuals - used_visuals
    if unused_visuals:
        if used_visuals:
            report_data["publicCustomVisuals"] = list(used_visuals)
        else:
            report_data.pop("publicCustomVisuals", None)
        if not dry_run:
            write_json(report_json_path, report_data)
        if dry_run:
            if summary:
                msg = f"Would remove {len(unused_visuals)} unused custom visuals"
            else:
                msg = f"Would remove unused custom visuals: {', '.join(unused_visuals)}"
            console.print_dry_run(msg)
        else:
            if summary:
                msg = f"Removed {len(unused_visuals)} unused custom visuals"
            else:
                msg = f"Removed unused custom visuals: {', '.join(unused_visuals)}"
            console.print_success(msg)
        return True
    else:
        console.print_info("No unused custom visuals found.")
        return False


def disable_show_items_with_no_data(
    report_path: str, dry_run: bool = False, summary: bool = False
) -> bool:
    """
    Disable the 'Show items with no data' option for visuals.

    Args:
        report_path (str): The path to the report.
        dry_run (bool): Whether to perform a dry run.
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading("Disabling 'Show items with no data'", dry_run)

    def _remove_show_all(data: dict, _: str) -> bool:
        if isinstance(data, dict):
            if "showAll" in data:
                del data["showAll"]
                return True
            return any(_remove_show_all(value, _) for value in data.values())
        elif isinstance(data, list):
            return any(_remove_show_all(item, _) for item in data)
        return False

    visuals_modified = process_json_files(
        os.path.join(report_path, "definition", "pages"),
        "visual.json",
        _remove_show_all,
        process=True,
        dry_run=dry_run,
    )

    if visuals_modified > 0:
        if dry_run:
            console.print_dry_run(
                f"Would disable 'Show items with no data' for {visuals_modified} visual(s)."
            )
        else:
            console.print_success(
                f"Disabled 'Show items with no data' for {visuals_modified} visual(s)."
            )
        return True
    else:
        console.print_info("No visuals found with 'Show items with no data' enabled.")
        return False


def _get_hidden_visuals_info(
    report_path: str,
) -> tuple[dict, dict, dict, list, dict, set]:
    """Helper to find hidden visuals, groups, and their children."""

    def _find_hidden_visuals(visual_data: dict, file_path: str) -> tuple:
        visual_name = visual_data.get("name")
        folder = os.path.dirname(file_path)
        visual_type = visual_data.get("visual", {}).get("visualType")

        # Check for default selection in visual.objects.general
        has_default_filters = False
        general_objects = (
            visual_data.get("visual", {}).get("objects", {}).get("general", [])
        )
        if isinstance(general_objects, list):
            for item in general_objects:
                if (
                    isinstance(item, dict)
                    and "properties" in item
                    and "filter" in item["properties"]
                ):
                    has_default_filters = True
                    break

        if visual_data.get("isHidden", False):
            if visual_data.get("visualGroup"):
                return (visual_name, folder, "group", visual_type, has_default_filters)
            return (visual_name, folder, "hidden", visual_type, has_default_filters)
        elif visual_data.get("parentGroupName"):
            return (
                visual_name,
                folder,
                ("child", visual_data["parentGroupName"]),
                visual_type,
                has_default_filters,
            )
        return None

    hidden_visuals_results = process_json_files(
        os.path.join(report_path, "definition", "pages"),
        "visual.json",
        _find_hidden_visuals,
    )

    hidden_groups = {}
    group_children = {}
    hidden_visuals = {}
    visual_types = {}
    visuals_with_default_filters = set()

    for result in hidden_visuals_results:
        if result[1]:
            visual_name, folder, info, visual_type, has_default_filters = result[1]
            visual_types[visual_name] = visual_type
            if has_default_filters:
                visuals_with_default_filters.add(visual_name)

            if info == "group":
                hidden_groups[visual_name] = folder
            elif isinstance(info, tuple) and info[0] == "child":
                parent_group = info[1]
                if parent_group not in group_children:
                    group_children[parent_group] = set()
                group_children[parent_group].add(visual_name)
            elif info == "hidden":
                hidden_visuals[visual_name] = folder

    return (
        hidden_groups,
        group_children,
        hidden_visuals,
        hidden_visuals_results,
        visual_types,
        visuals_with_default_filters,
    )


def _get_shown_visuals_from_bookmarks(report_path: str) -> tuple[set, set]:
    """Helper to identify visuals and groups shown by bookmarks."""

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

    shown_visuals = set()
    shown_groups = set()
    for _, result in process_json_files(
        os.path.join(report_path, "definition", "bookmarks"),
        ".bookmark.json",
        _check_bookmark,
    ):
        if result:
            vis, grp = result
            shown_visuals.update(vis)
            shown_groups.update(grp)

    return shown_visuals, shown_groups


def _get_visuals_filtered_by_bookmarks(report_path: str) -> set:
    """Helper to identify visuals that have filters applied in bookmarks."""

    def _check_bookmark_filters(bookmark_data: dict, _: str) -> set:
        filtered_visuals = set()
        for section in (
            bookmark_data.get("explorationState", {}).get("sections", {}).values()
        ):
            for visual_name, container in section.get("visualContainers", {}).items():
                # Check for filters in the container or singleVisual
                if "filters" in container:
                    filtered_visuals.add(visual_name)
                elif (
                    "singleVisual" in container
                    and "filters" in container["singleVisual"]
                ):
                    filtered_visuals.add(visual_name)
        return filtered_visuals

    filtered_visuals = set()
    for _, result in process_json_files(
        os.path.join(report_path, "definition", "bookmarks"),
        ".bookmark.json",
        _check_bookmark_filters,
    ):
        if result:
            filtered_visuals.update(result)

    return filtered_visuals


def remove_hidden_visuals_never_shown(
    report_path: str, dry_run: bool = False, summary: bool = False
) -> bool:
    """
    Remove hidden visuals that are never shown using bookmarks.
    Also removes hidden visual groups and their children.
    Preserves hidden slicers if they have default selections or are filtered by bookmarks.

    Args:
        report_path (str): The path to the report.
        dry_run (bool): Whether to perform a dry run.
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading(
        "Removing hidden visuals that are never shown using bookmarks", dry_run
    )

    (
        hidden_groups,
        group_children,
        hidden_visuals,
        hidden_visuals_results,
        visual_types,
        visuals_with_default_filters,
    ) = _get_hidden_visuals_info(report_path)
    shown_visuals, shown_groups = _get_shown_visuals_from_bookmarks(report_path)
    filtered_visuals = _get_visuals_filtered_by_bookmarks(report_path)

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
            visual_type = visual_types.get(visual)
            if visual_type and "slicer" in visual_type.lower():
                # Check if it has default filters or bookmark filters
                if visual in visuals_with_default_filters:
                    if not summary:
                        console.print_info(
                            f"Skipping removal of hidden slicer: {visual} (type: {visual_type}) (has default selection)"
                        )
                    continue
                if visual in filtered_visuals:
                    if not summary:
                        console.print_info(
                            f"Skipping removal of hidden slicer: {visual} (type: {visual_type}) (filtered by bookmark)"
                        )
                    continue

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
            page_json_path = os.path.join(
                os.path.dirname(os.path.dirname(folder)), "page.json"
            )
            if os.path.exists(page_json_path):
                page_data = load_json(page_json_path)
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
                    if not dry_run:
                        write_json(page_json_path, page_data)
                    if not summary:
                        if dry_run:
                            console.print_dry_run(
                                f"Would remove visual interactions for {visual_name} from {page_json_path}"
                            )
                        else:
                            console.print_success(
                                f"Removed visual interactions for {visual_name} from {page_json_path}"
                            )
            # Remove the visual folder
            if not dry_run:
                shutil.rmtree(folder)
            visual_type = visual_types.get(visual_name, "unknown")

            # Get page name
            page_name = "Unknown Page"
            if folder:
                page_dir = os.path.dirname(os.path.dirname(folder))
                page_json_path = os.path.join(page_dir, "page.json")
                if os.path.exists(page_json_path):
                    page_data = load_json(page_json_path)
                    page_name = page_data.get("displayName", "Unknown Page")

            if not summary:
                if dry_run:
                    console.print_dry_run(
                        f"Would remove '{visual_type}' visual in '{page_name}' page: {visual_name}"
                    )
                else:
                    console.print_success(
                        f"Removed '{visual_type}' visual in '{page_name}' page: {visual_name}"
                    )

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
    bookmarks_updated = process_json_files(
        os.path.join(report_path, "definition", "bookmarks"),
        ".bookmark.json",
        _update_bookmark,
        process=True,
        dry_run=dry_run,
    )

    if len(visuals_to_remove) > 0 or bookmarks_updated > 0:
        if dry_run:
            console.print_dry_run(
                f"Would remove {len(visuals_to_remove)} visuals (including groups and their children)"
            )
            if bookmarks_updated > 0:
                console.print_dry_run(
                    f"Would update {bookmarks_updated} bookmark files"
                )
        else:
            console.print_success(
                f"Removed {len(visuals_to_remove)} visuals (including groups and their children)"
            )
            if bookmarks_updated > 0:
                console.print_success(f"Updated {bookmarks_updated} bookmark files")
        return True
    else:
        console.print_info("No hidden visuals removed.")
        return False
