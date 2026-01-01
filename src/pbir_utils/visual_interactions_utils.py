from pathlib import Path

from .common import load_json, write_json, iter_pages, iter_visuals
from .console_utils import console


def _get_visuals(page_folder: str) -> tuple[list[str], dict[str, str]]:
    """
    Retrieves visual IDs and their types from a page folder.

    Args:
        page_folder (str): Path to the page folder containing a 'visuals' subdirectory.

    Returns:
        Tuple[list, dict]: A tuple containing a list of visual IDs and a dictionary
                           mapping visual IDs to their types.
    """
    visual_ids = []
    visual_types = {}

    for visual_id, _, visual_data in iter_visuals(page_folder):
        # Skip visual groups
        if "visualGroup" in visual_data:
            continue

        visual_type = visual_data.get("visual", {}).get("visualType", "Unknown")
        visual_ids.append(visual_id)
        visual_types[visual_id] = visual_type

    return visual_ids, visual_types


def _update_interactions(
    existing_interactions: list[dict],
    source_ids: list[str],
    target_ids: list[str],
    update_type: str = "Upsert",
    interaction_type: str = "NoFilter",
) -> list[dict]:
    """
    Updates visual interactions based on the update type and interaction type.

    Args:
        existing_interactions (list[dict]): List of existing visual interactions.
        source_ids (list[str]): List of source visual IDs.
        target_ids (list[str]): List of target visual IDs.
        update_type (str): Determines how interactions are handled. Options are "Upsert", "Insert", "Overwrite".
        interaction_type (str): Type of interaction to apply. Default is "NoFilter".

    Returns:
        list[dict]: Updated list of visual interactions.
    """
    if update_type == "Overwrite":
        new_interactions = [
            {"source": source_id, "target": target_id, "type": interaction_type}
            for source_id in source_ids
            for target_id in target_ids
            if source_id != target_id
        ]
        return new_interactions

    interactions_dict = {
        (item["source"], item["target"]): item for item in existing_interactions
    }

    if update_type in ["Upsert", "Insert"]:
        for source_id in source_ids:
            for target_id in target_ids:
                if source_id != target_id:
                    if (
                        update_type == "Upsert"
                        or (source_id, target_id) not in interactions_dict
                    ):
                        interactions_dict[(source_id, target_id)] = {
                            "source": source_id,
                            "target": target_id,
                            "type": interaction_type,
                        }

    return list(interactions_dict.values())


def _filter_ids_by_type(
    ids: set[str], types: list[str] | None, visual_types: dict[str, str]
) -> set[str]:
    """
    Filters a set of visual IDs by their types.

    Args:
        ids (set[str]): Set of visual IDs to filter.
        types (list[str] or None): List of allowed visual types. If None, no filtering is done.
        visual_types (dict[str, str]): Dictionary mapping visual IDs to their types.

    Returns:
        set[str]: Filtered set of visual IDs.
    """
    return {vid for vid in ids if not types or visual_types.get(vid) in types}


def _process_page(
    page_json_path: str | Path,
    page_folder: str,
    source_ids: list[str] | None,
    source_types: list[str] | None,
    target_ids: list[str] | None,
    target_types: list[str] | None,
    update_type: str,
    interaction_type: str,
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Processes and updates visual interactions for a specific page.

    Args:
        page_json_path (str | Path): Path to the page JSON file.
        page_folder (str): Path to the page folder containing a 'visuals' subdirectory.
        source_ids (list[str] or None): List of source visual IDs.
        source_types (list[str] or None): List of source visual types.
        target_ids (list[str] or None): List of target visual IDs.
        target_types (list[str] or None): List of target visual types.
        update_type (str): Determines how interactions are handled. Options are "Upsert", "Insert", "Overwrite".
        interaction_type (str): Type of interaction to apply. Default is "NoFilter".
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    page_json = load_json(page_json_path)
    visual_ids, visual_types = _get_visuals(page_folder)

    target_ids = _filter_ids_by_type(
        set(target_ids or visual_ids), target_types, visual_types
    )
    source_ids = _filter_ids_by_type(
        set(source_ids or visual_ids), source_types, visual_types
    )

    existing_interactions = page_json.get("visualInteractions", [])
    updated_interactions = _update_interactions(
        existing_interactions,
        list(source_ids),
        list(target_ids),
        update_type,
        interaction_type,
    )

    # Check if there were any changes
    has_changes = updated_interactions != existing_interactions

    page_json["visualInteractions"] = updated_interactions
    if not dry_run:
        write_json(page_json_path, page_json)
    elif not summary and has_changes:
        console.print_dry_run(f"Would update visual interactions in {page_json_path}")

    return has_changes


def _process_all_pages(
    report_path: str,
    pages: list[str] | None = None,
    source_ids: list[str] | None = None,
    source_types: list[str] | None = None,
    target_ids: list[str] | None = None,
    target_types: list[str] | None = None,
    update_type: str = "Upsert",
    interaction_type: str = "NoFilter",
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Processes all pages or specific pages based on provided parameters.

    Args:
        report_path (str): Path to the report folder.
        pages (list[str], optional): List of page names to process. If None, all pages are processed.
        source_ids (list[str], optional): List of source visual IDs.
        source_types (list[str], optional): List of source visual types.
        target_ids (list[str], optional): List of target visual IDs.
        target_types (list[str], optional): List of target visual types.
        update_type (str): Determines how interactions are handled. Options are "Upsert", "Insert", "Overwrite".
        interaction_type (str): Type of interaction to apply. Default is "NoFilter".
        summary (bool): Whether to show summary instead of detailed messages.

    Returns:
        bool: True if any changes were made (or would be made in dry run), False otherwise.
    """
    pages_updated = 0
    any_changes = False

    for page_id, page_folder, page_json in iter_pages(report_path):
        # Process the page if it's in the list or if all pages should be processed
        if not pages or page_json.get("displayName") in pages:
            page_folder_path = Path(page_folder)
            file_path = page_folder_path / "page.json"
            visuals_dir = page_folder_path / "visuals"
            if visuals_dir.is_dir():
                page_changed = _process_page(
                    file_path,
                    page_folder,
                    source_ids,
                    source_types,
                    target_ids,
                    target_types,
                    update_type,
                    interaction_type,
                    dry_run=dry_run,
                    summary=summary,
                )
                if page_changed:
                    any_changes = True
                pages_updated += 1

    if summary:
        if any_changes:
            if dry_run:
                msg = f"Would update visual interactions in {pages_updated} pages"
                console.print_dry_run(msg)
            else:
                msg = f"Updated visual interactions in {pages_updated} pages"
                console.print_success(msg)
        else:
            console.print_info("No visual interactions were modified.")
    elif not any_changes:
        console.print_info("No visual interactions were modified.")

    return any_changes


def disable_visual_interactions(
    report_path: str,
    pages: list[str] | None = None,
    source_visual_ids: list[str] | None = None,
    source_visual_types: list[str] | None = None,
    target_visual_ids: list[str] | None = None,
    target_visual_types: list[str] | None = None,
    update_type: str = "Upsert",
    dry_run: bool = False,
    summary: bool = False,
) -> bool:
    """
    Main function to disable visual interactions based on provided parameters.

    Args:
        report_path (str): Path to the report folder.
        pages (list, optional): List of page names to process. If None, all pages are processed.
        source_visual_ids (list, optional): List of specific source visual IDs. If None, all visuals are used as sources.
        source_visual_types (list, optional): List of source visual types. If None, all visuals are used as sources.
        target_visual_ids (list, optional): List of specific target visual IDs. If None, all visuals are used as targets.
        target_visual_types (list, optional): List of target visual types. If None, all visuals are used as targets.
        update_type (str, optional): Determines how interactions are handled. Options are "Upsert", "Insert", "Overwrite". Default is "Upsert".
        summary (bool, optional): If True, show summary instead of detailed messages. Default is False.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.

    Raises:
        ValueError: If any of the provided parameters are not lists when expected.
    """
    console.print_action_heading("Disabling visual interactions", dry_run)
    # Validate that parameters are lists if they are not None
    for param_name, param_value in {
        "pages": pages,
        "source_visual_ids": source_visual_ids,
        "source_visual_types": source_visual_types,
        "target_visual_ids": target_visual_ids,
        "target_visual_types": target_visual_types,
    }.items():
        if param_value is not None and not isinstance(param_value, list):
            raise ValueError(f"{param_name} must be a list")

    # Proceed with processing all pages
    return _process_all_pages(
        report_path,
        pages,
        source_visual_ids,
        source_visual_types,
        target_visual_ids,
        target_visual_types,
        update_type,
        interaction_type="NoFilter",
        dry_run=dry_run,
        summary=summary,
    )
