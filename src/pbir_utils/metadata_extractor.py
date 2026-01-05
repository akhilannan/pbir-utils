from pathlib import Path
import csv

from .common import (
    load_json,
    iter_merged_fields,
    iter_pages,
    extract_visual_info,
    find_report_folders,
)
from .console_utils import console

HEADER_FIELDS = [
    "Report",
    "Page Name",
    "Page ID",
    "Table",
    "Column or Measure",
    "Attribute Type",
    "Expression",
    "Used In",
    "Used In Detail",
    "ID",
]

VISUAL_HEADER_FIELDS = [
    "Report",
    "Page Name",
    "Page ID",
    "Visual Type",
    "Visual ID",
    "Parent Group ID",
    "Is Hidden",
]


def _extract_report_name(json_file_path: str | Path) -> str:
    """
    Extracts the report name from the JSON file path.

    Args:
        json_file_path (str | Path): The file path to the JSON file.

    Returns:
        str: The extracted report name if found, otherwise "NA".
    """
    path = Path(json_file_path)
    for part in reversed(path.parts):
        if part.endswith(".Report"):
            return part[:-7]
    return "NA"


def _extract_active_section(bookmark_json_path: str | Path) -> str:
    """
    Extracts the active section from the bookmarks JSON file.

    Args:
        bookmark_json_path (str | Path): The file path to the bookmarks JSON file.

    Returns:
        str: The active section if found, otherwise an empty string.
    """
    if "bookmarks" in str(bookmark_json_path):
        return (
            load_json(bookmark_json_path)
            .get("explorationState", {})
            .get("activeSection", "")
        )

    path = Path(bookmark_json_path)
    parts = path.parts
    try:
        pages_index = list(parts).index("pages") + 1
        if pages_index < len(parts) and not parts[pages_index].endswith(".json"):
            return parts[pages_index]
    except ValueError:
        pass

    return None


def _extract_page_info(json_path: str | Path) -> tuple:
    """
    Extracts the page name and ID from the JSON file path.

    Args:
        json_path (str | Path): The file path to the JSON file.

    Returns:
        tuple: The extracted page name and ID if found, otherwise ("NA", "NA").
    """
    active_section = _extract_active_section(json_path)
    if not active_section:
        return "NA", "NA"

    path_str = str(json_path)
    base_path = path_str.split("definition")[0]
    page_json_path = (
        Path(base_path) / "definition" / "pages" / active_section / "page.json"
    )

    page_data = load_json(page_json_path)

    return page_data.get("displayName", "NA"), page_data.get("name", "NA")


def _get_page_order(
    report_path: str | Path, include_active_page: bool = False
) -> list | tuple[list, str | None]:
    """
    Get the page order from the pages.json file.

    Args:
        report_path (str | Path): Path to the root folder of the report.
        include_active_page (bool): If True, also return the active page name.

    Returns:
        list: List of page IDs in the correct order (when include_active_page=False).
        tuple[list, str | None]: Page order and active page name (when include_active_page=True).
    """
    pages_json_path = Path(report_path) / "definition" / "pages" / "pages.json"
    pages_data = load_json(pages_json_path)
    page_order = pages_data.get("pageOrder", [])

    if include_active_page:
        active_page = pages_data.get("activePageName")
        return page_order, active_page

    return page_order


def _apply_row_filters(row: dict, filters: dict) -> bool:
    """
    Apply filters to a row with early exit.

    Args:
        row (dict): The row to filter.
        filters (dict): Filters dictionary with sets as values.

    Returns:
        bool: True if the row passes all filters, False otherwise.
    """
    if not filters:
        return True
    for column, allowed_values in filters.items():
        if allowed_values and row.get(column) not in allowed_values:
            return False
    return True


def _sort_by_page_order(metadata: list, report_paths: list[str]) -> None:
    """
    Sort metadata rows in-place by report name and page order.

    Args:
        metadata: List of row dicts with 'Report' and 'Page ID' keys.
        report_paths: List of report folder paths.
    """
    # Build page order map for sorting
    report_page_orders = {}
    for r_path in report_paths:
        r_name = _extract_report_name(Path(r_path) / "definition" / "report.json")
        report_page_orders[r_name] = _get_page_order(r_path)

    metadata.sort(
        key=lambda row: (
            row["Report"],
            (
                report_page_orders.get(row["Report"], []).index(row["Page ID"])
                if row["Page ID"] in report_page_orders.get(row["Report"], [])
                else len(report_page_orders.get(row["Report"], [])) + 1
            ),
        )
    )


def _extract_metadata_from_file(
    json_file_path: str | Path, filters: dict = None
) -> list:
    """
    Extracts and formats attribute metadata from a single PBIR JSON file.

    Args:
        json_file_path (str | Path): The file path to the PBIR JSON file.
        filters (dict, optional): A dictionary with column names as keys and sets of allowed values as values.

    Returns:
        list: A list of dictionaries representing the processed attribute metadata entries from the file.
    """
    report_name = _extract_report_name(json_file_path)

    page_filter = filters.get("Page Name") if filters else None
    page_name, page_id = _extract_page_info(json_file_path)

    if page_filter and page_name not in page_filter:
        return []  # Skip this file if page doesn't match the filter

    # If we've passed the initial filter checks, proceed with loading and processing the JSON
    data = load_json(json_file_path)
    id = data.get("name", None)
    all_rows = []

    # Use iter_merged_fields to get complete (table, field) pairs
    for (
        table,
        column,
        used_in,
        expression,
        used_in_detail,
        attr_type,
    ) in iter_merged_fields(data):
        row = dict(
            zip(
                HEADER_FIELDS,
                [
                    report_name,
                    page_name,
                    page_id,
                    table,
                    column,
                    attr_type,
                    expression,
                    used_in,
                    used_in_detail,
                    id,
                ],
            )
        )
        if _apply_row_filters(row, filters):
            all_rows.append(row)

    return all_rows


def _consolidate_metadata_from_directory(
    directory_path: str, filters: dict = None
) -> list:
    """
    Extracts and consolidates attribute metadata from all PBIR JSON files in the specified directory.

    Args:
        directory_path (str): The root directory path containing PBIR component JSON files.
        filters (dict, optional): A dictionary with column names as keys and sets of allowed values as values.

    Returns:
        list: A list of dictionaries, each representing a unique metadata entry with fields:
            Report, Page Name, Page ID, Table, Column or Measure, Expression, Used In, Used In Detail, and ID.
    """
    all_rows_with_expression = []
    all_rows_without_expression = []
    report_filter = filters.get("Report") if filters else None

    report_dirs = find_report_folders(directory_path)

    if not report_dirs:
        console.print_warning(f"No .Report folders found in {directory_path}")
        return []

    for report_dir in report_dirs:
        report_name = _extract_report_name(Path(report_dir) / "dummy")
        if report_filter and report_name not in report_filter:
            continue

        report_path = Path(report_dir)
        for json_file_path in report_path.rglob("*.json"):
            if json_file_path.is_file():
                file_metadata = _extract_metadata_from_file(json_file_path, filters)

                rows_with_expression = [
                    row for row in file_metadata if row["Expression"] is not None
                ]
                rows_without_expression = [
                    row for row in file_metadata if row["Expression"] is None
                ]

                # Aggregate all rows with and without expressions
                all_rows_with_expression.extend(rows_with_expression)
                all_rows_without_expression.extend(rows_without_expression)

    # Build index for expression lookups
    expression_index = {
        (row["Report"], row["Table"], row["Column or Measure"]): row["Expression"]
        for row in all_rows_with_expression
    }

    # Match expressions
    for row in all_rows_without_expression:
        key = (row["Report"], row["Table"], row["Column or Measure"])
        if key in expression_index:
            row["Expression"] = expression_index[key]

    # Build set of keys for lookup
    existing_keys = {
        (r["Report"], r["Table"], r["Column or Measure"])
        for r in all_rows_without_expression
    }

    # Add rows with expressions that weren't matched
    final_rows = all_rows_without_expression + [
        row
        for row in all_rows_with_expression
        if (row["Report"], row["Table"], row["Column or Measure"]) not in existing_keys
    ]

    # Extract distinct rows
    unique_rows = []
    seen = set()
    for row in final_rows:
        row_tuple = tuple(row[field] for field in HEADER_FIELDS)
        if row_tuple not in seen:
            unique_rows.append(row)
            seen.add(row_tuple)

    return unique_rows


def export_pbir_metadata_to_csv(
    directory_path: str,
    csv_output_path: str = None,
    filters: dict = None,
    *,
    pages: list[str] = None,
    reports: list[str] = None,
    tables: list[str] = None,
    visual_types: list[str] = None,
    visual_ids: list[str] = None,
    visuals_only: bool = False,
):
    """
    Exports the extracted Power BI Enhanced Report Format (PBIR) metadata to a CSV file.

    Args:
        directory_path (str): The directory path containing PBIR JSON files.
        csv_output_path (str, optional): The output path for the CSV file. If not provided,
                                         defaults to 'metadata.csv' or 'visuals.csv' (based on mode)
                                         in the same directory as directory_path.
        filters (dict, optional): A dictionary with column names as keys and sets of allowed values.
                                  Kept for backward compatibility. Prefer using explicit parameters.
        pages (list[str], optional): Filter by page displayName(s).
        reports (list[str], optional): Filter by report name(s) when processing a directory.
        tables (list[str], optional): Filter by table name(s).
        visual_types (list[str], optional): Filter by visual type(s) (for visuals_only mode).
        visual_ids (list[str], optional): Filter by visual ID(s) (for visuals_only mode).
        visuals_only (bool, optional): If True, exports visual-level metadata instead of attribute usage.
                                       Defaults to False.

    Returns:
        None
    """
    # Merge explicit parameters with legacy filters dict
    merged_filters = dict(filters) if filters else {}
    if pages:
        merged_filters["Page Name"] = set(pages)
    if reports:
        merged_filters["Report"] = set(reports)
    if tables:
        merged_filters["Table"] = set(tables)
    if visual_types:
        merged_filters["Visual Type"] = set(visual_types)
    if visual_ids:
        merged_filters["Visual ID"] = set(visual_ids)

    final_filters = merged_filters or None

    if csv_output_path is None:
        default_filename = "visuals.csv" if visuals_only else "metadata.csv"
        csv_output_path = str(Path(directory_path) / default_filename)

    if visuals_only:
        _export_visual_metadata(directory_path, csv_output_path, final_filters)
    else:
        _export_attribute_metadata(directory_path, csv_output_path, final_filters)


def _export_visual_metadata(
    directory_path: str, csv_output_path: str, filters: dict = None
):
    """Export visual-level metadata using iter_pages + extract_visual_info."""
    console.print_action_heading("Extracting visual metadata", False)

    metadata = []
    report_paths = find_report_folders(directory_path)

    if not report_paths:
        console.print_warning(f"No .Report folders found in {directory_path}")

    for report_path in report_paths:
        # Construct a dummy path to use the existing extractor
        dummy_file_path = Path(report_path) / "definition" / "report.json"
        report_name = _extract_report_name(dummy_file_path)

        # Apply report filter if specified
        report_filter = filters.get("Report") if filters else None
        if report_filter and report_name not in report_filter:
            continue

        for page_id, page_folder, page_data in iter_pages(report_path):
            page_name = page_data.get("displayName", "NA")

            # Apply page filter if specified
            if (
                filters
                and filters.get("Page Name")
                and page_name not in filters["Page Name"]
            ):
                continue

            visuals_info = extract_visual_info(page_folder)
            for visual_id, info in visuals_info.items():
                row = {
                    "Report": report_name,
                    "Page Name": page_name,
                    "Page ID": page_id,
                    "Visual Type": info["visualType"],
                    "Visual ID": visual_id,
                    "Parent Group ID": info["parentGroupName"],
                    "Is Hidden": info["isHidden"],
                }
                if _apply_row_filters(row, filters):
                    metadata.append(row)

    _sort_by_page_order(metadata, report_paths)

    try:
        with open(csv_output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=VISUAL_HEADER_FIELDS)
            writer.writeheader()
            writer.writerows(metadata)
        console.print_success(f"Visual metadata exported to {csv_output_path}")
    except Exception as e:
        console.print_error(f"Error exporting visual metadata: {e}")


def _export_attribute_metadata(
    directory_path: str, csv_output_path: str, filters: dict = None
):
    """Export attribute-level metadata (original behavior)."""
    console.print_action_heading("Extracting metadata", False)

    metadata = _consolidate_metadata_from_directory(directory_path, filters)

    all_report_paths = find_report_folders(directory_path)
    _sort_by_page_order(metadata, all_report_paths)

    try:
        with open(csv_output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=HEADER_FIELDS)
            writer.writeheader()
            writer.writerows(metadata)
        console.print_success(f"Metadata exported to {csv_output_path}")
    except Exception as e:
        console.print_error(f"Error exporting metadata: {e}")
