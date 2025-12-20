"""
Bookmark utilities for Power BI report sanitization.

Contains functions for managing bookmarks in PBIR reports.
"""

import os
import shutil

from .common import load_json, write_json, process_json_files
from .console_utils import console


def remove_unused_bookmarks(
    report_path: str, dry_run: bool = False, summary: bool = False
) -> bool:
    """
    Remove bookmarks which are not activated in report using bookmark navigator or actions.

    Args:
        report_path (str): The path to the report.
        dry_run (bool): Whether to perform a dry run.
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading("Removing unused bookmarks", dry_run)

    bookmarks_dir = os.path.join(report_path, "definition", "bookmarks")
    bookmarks_json_path = os.path.join(bookmarks_dir, "bookmarks.json")

    if not os.path.exists(bookmarks_json_path):
        console.print_info("No bookmarks found.")
        return False

    bookmarks_data = load_json(bookmarks_json_path)

    def _is_bookmark_used(bookmark_name: str) -> bool:
        """Check if a bookmark is used in the report."""

        def _check_visual(visual_data: dict, _: str) -> str:
            visual = visual_data.get("visual", {})
            if visual.get("visualType") == "bookmarkNavigator":
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
            visual_link = visual.get("visualContainerObjects", {}).get("visualLink", [])
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
            for result in process_json_files(
                os.path.join(report_path, "definition", "pages"),
                "visual.json",
                _check_visual,
            )
        )

    used_bookmarks = set()
    new_items = []
    for item in bookmarks_data["items"]:
        if _is_bookmark_used(item["name"]):
            used_bookmarks.add(item["name"])
            new_items.append(item)
            if "children" in item:
                used_bookmarks.update(item["children"])
        elif "children" in item:
            used_children = [
                child for child in item["children"] if _is_bookmark_used(child)
            ]
            if used_children:
                item["children"] = used_children
                used_bookmarks.update(used_children)
                used_bookmarks.add(item["name"])
                new_items.append(item)

    bookmarks_data["items"] = new_items

    removed_bookmarks = 0
    removed_bookmark_names = []
    for filename in os.listdir(bookmarks_dir):
        if filename.endswith(".bookmark.json"):
            bookmark_file_data = load_json(os.path.join(bookmarks_dir, filename))
            if bookmark_file_data.get("name") not in used_bookmarks:
                if not dry_run:
                    os.remove(os.path.join(bookmarks_dir, filename))
                removed_bookmarks += 1
                removed_bookmark_names.append(filename)
                if not summary:
                    if dry_run:
                        console.print_dry_run(
                            f"Would remove unused bookmark file: {filename}"
                        )
                    else:
                        console.print_success(
                            f"Removed unused bookmark file: {filename}"
                        )

    if not dry_run:
        write_json(bookmarks_json_path, bookmarks_data)

    if not bookmarks_data["items"]:
        if not dry_run:
            shutil.rmtree(bookmarks_dir)
            console.print_success("Removed empty bookmarks folder")
        else:
            console.print_dry_run("Would remove empty bookmarks folder")

    if removed_bookmarks > 0:
        if dry_run:
            console.print_dry_run(f"Would remove {removed_bookmarks} unused bookmarks")
        else:
            console.print_success(f"Removed {removed_bookmarks} unused bookmarks")
    elif bookmarks_data["items"]:
        console.print_info("No unused bookmarks found.")

    return removed_bookmarks > 0 or not bookmarks_data["items"]


def cleanup_invalid_bookmarks(
    report_path: str, dry_run: bool = False, summary: bool = False
) -> bool:
    """
    Clean up invalid bookmarks that reference non-existent pages or visuals.

    Args:
        report_path (str): The path to the report.
        dry_run (bool): Whether to perform a dry run.
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading("Cleaning up invalid bookmarks", dry_run)

    bookmarks_dir = os.path.join(report_path, "definition", "bookmarks")
    if not os.path.exists(bookmarks_dir):
        console.print_info("No bookmarks directory found.")
        return False

    # Load pages.json to get valid page names
    pages_json_path = os.path.join(report_path, "definition", "pages", "pages.json")
    pages_data = load_json(pages_json_path)
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
            if not dry_run:
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
                for result in process_json_files(
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
    process_json_files(
        bookmarks_dir,
        ".bookmark.json",
        _process_bookmark,
        process=True,
        dry_run=dry_run,
    )

    # Update bookmarks.json
    bookmarks_json_path = os.path.join(bookmarks_dir, "bookmarks.json")
    bookmarks_data = load_json(bookmarks_json_path)

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
        if not dry_run:
            shutil.rmtree(bookmarks_dir)
            console.print_success("Removed empty bookmarks directory")
        else:
            console.print_dry_run("Would remove empty bookmarks directory")
    else:
        if stats["processed"] > 0:
            console.print_info(f"Processed {stats['processed']} bookmark files:")
            if stats["removed"] > 0:
                if not dry_run:
                    write_json(bookmarks_json_path, bookmarks_data)
                    console.print_success(
                        f"- Removed {stats['removed']} invalid bookmarks"
                    )
                else:
                    console.print_dry_run(
                        f"- Would remove {stats['removed']} invalid bookmarks"
                    )
            if stats["cleaned"] > 0:
                if dry_run:
                    console.print_dry_run(
                        f"- Would clean {stats['cleaned']} invalid visual references"
                    )
                else:
                    console.print_success(
                        f"- Cleaned {stats['cleaned']} invalid visual references"
                    )
            if stats["updated"] > 0:
                if dry_run:
                    console.print_dry_run(
                        f"- Would update {stats['updated']} bookmark files"
                    )
                else:
                    console.print_success(
                        f"- Updated {stats['updated']} bookmark files"
                    )
            return True
        else:
            console.print_info("No invalid bookmarks or references found.")
            return False
