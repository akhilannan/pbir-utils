import os
import csv
import fnmatch

from .json_utils import _load_json

HEADER_FIELDS = [
    "Report",
    "Page",
    "Table",
    "Column or Measure",
    "Expression",
    "Used In",
    "Used In Detail",
    "ID",
]


def _extract_report_name(json_file_path: str) -> str:
    """
    Extracts the report name from the JSON file path.

    Args:
        json_file_path (str): The file path to the JSON file.

    Returns:
        str: The extracted report name if found, otherwise "NA".
    """
    return next(
        (
            component[:-7]
            for component in reversed(json_file_path.split(os.sep))
            if component.endswith(".Report")
        ),
        "NA",
    )


def _extract_active_section(bookmark_json_path: str) -> str:
    """
    Extracts the active section from the bookmarks JSON file.

    Args:
        bookmark_json_path (str): The file path to the bookmarks JSON file.

    Returns:
        str: The active section if found, otherwise an empty string.
    """
    # Check if the path is related to bookmarks
    if "bookmarks" in bookmark_json_path:
        return (
            _load_json(bookmark_json_path)
            .get("explorationState", {})
            .get("activeSection", "")
        )

    # Check if the path contains "pages" and extract the next part if it's a directory
    parts = os.path.normpath(bookmark_json_path).split(os.sep)
    try:
        pages_index = parts.index("pages") + 1
        if pages_index < len(parts) and not parts[pages_index].endswith(".json"):
            return parts[pages_index]
    except ValueError:
        pass

    return None


def _extract_page_name(json_path: str) -> str:
    """
    Extracts the page name from the JSON file path.

    Args:
        json_path (str): The file path to the JSON file.

    Returns:
        str: The extracted page name if found, otherwise "NA".
    """
    active_section = _extract_active_section(json_path)
    if not active_section:
        return "NA"

    base_path = json_path.split("definition")[0]
    page_json_path = os.path.join(
        base_path, "definition", "pages", active_section, "page.json"
    )

    return _load_json(page_json_path).get("displayName", "NA")


def _traverse_pbir_json_structure(data: dict | list, usage_context: str = None, usage_detail: str = None) -> object:
    """
    Recursively traverses the Power BI Enhanced Report Format (PBIR) JSON structure to extract specific metadata.

    This function navigates through the complex PBIR JSON structure, identifying and extracting
    key metadata elements such as entities, properties, visuals, filters, bookmarks, and measures.

    Args:
        data (dict or list): The PBIR JSON data to traverse.
        usage_context (str, optional): The current context within the PBIR structure (e.g., visual type, filter, bookmark, etc)
        usage_detail (str, optional): The detailed context inside a usage_context (e.g., tooltip, legend, Category, etc.)

    Yields:
        tuple: Extracted metadata in the form of (table, column, used_in, expression, used_in_detail).
               - table: The name of the table (if applicable)
               - column: The name of the column or measure
               - used_in: The broader context in which the element is used (e.g., visual type, filter, bookmark)
               - expression: The DAX expression for measures (if applicable)
               - used_in_detail: The specific setting where "Entity" and "Property" appear within the context
    """
    if isinstance(data, dict):
        for key, value in data.items():
            new_usage_detail = usage_detail or usage_context
            if key == "Entity":
                yield (value, None, usage_context, None, usage_detail)
            elif key == "Property":
                yield (None, value, usage_context, None, usage_detail)
            elif key in [
                "backColor",
                "Category",
                "categoryAxis",
                "Data",
                "dataPoint",
                "error",
                "fontColor",
                "icon",
                "labels",
                "legend",
                "Series",
                "singleVisual",
                "Size",
                "sort",
                "Tooltips",
                "valueAxis",
                "Values",
                "webURL",
                "X",
                "Y",
                "Y2",
            ]:
                yield from _traverse_pbir_json_structure(value, usage_context, key)
            elif key in ["filters", "filter", "parameters"]:
                yield from _traverse_pbir_json_structure(value, usage_context, "filter")
            elif key == "visual":
                yield from _traverse_pbir_json_structure(
                    value, value.get("visualType", "visual"), new_usage_detail
                )
            elif key == "pageBinding":
                yield from _traverse_pbir_json_structure(
                    value, value.get("type", "Drillthrough"), new_usage_detail
                )
            elif key == "filterConfig":
                yield from _traverse_pbir_json_structure(
                    value, "Filters", new_usage_detail
                )
            elif key == "explorationState":
                yield from _traverse_pbir_json_structure(
                    value, "Bookmarks", new_usage_detail
                )
            elif key == "entities":
                for entity in value:
                    table_name = entity.get("name")
                    for measure in entity.get("measures", []):
                        yield (
                            table_name,
                            measure.get("name"),
                            usage_context,
                            measure.get("expression", None),
                            new_usage_detail,
                        )
            else:
                yield from _traverse_pbir_json_structure(
                    value, usage_context, new_usage_detail
                )
    elif isinstance(data, list):
        for item in data:
            yield from _traverse_pbir_json_structure(item, usage_context, usage_detail)


def _apply_filters(row: dict, filters: dict) -> bool:
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


def _extract_metadata_from_file(json_file_path: str, filters: dict = None) -> list:
    """
    Extracts and formats attribute metadata from a single PBIR JSON file.

    Args:
        json_file_path (str): The file path to the PBIR JSON file.
        filters (dict, optional): A dictionary with column names as keys and sets of allowed values as values.

    Returns:
        list: A list of dictionaries representing the processed attribute metadata entries from the file.
    """
    report_name = _extract_report_name(json_file_path)

    page_filter = filters.get("Page") if filters else None
    page_name = _extract_page_name(json_file_path) or "NA"

    if page_filter and page_name not in page_filter:
        return []  # Skip this file if page doesn't match the filter

    # If we've passed the initial filter checks, proceed with loading and processing the JSON
    data = _load_json(json_file_path)
    id = data.get("name", None)
    all_rows = []

    def row_generator():
        temp_row = None
        for (
            table,
            column,
            used_in,
            expression,
            used_in_detail,
        ) in _traverse_pbir_json_structure(data):
            row = dict(
                zip(
                    HEADER_FIELDS,
                    [
                        report_name,
                        page_name,
                        table,
                        column,
                        expression,
                        used_in,
                        used_in_detail,
                        id,
                    ],
                )
            )

            if expression is None:
                if temp_row is None:
                    temp_row = row
                else:
                    temp_row["Column or Measure"] = column
                    yield temp_row
                    temp_row = None
            else:
                yield row

        if temp_row is not None:
            yield temp_row

    for row in row_generator():
        if _apply_filters(row, filters):
            all_rows.append(row)

    return all_rows


def _consolidate_metadata_from_directory(directory_path: str, filters: dict = None) -> list:
    """
    Extracts and consolidates attribute metadata from all PBIR JSON files in the specified directory.

    Args:
        directory_path (str): The root directory path containing PBIR component JSON files.
        filters (dict, optional): A dictionary with column names as keys and sets of allowed values as values.

    Returns:
        list: A list of dictionaries, each representing a unique metadata entry with fields:
            Report, Page, Table, Column or Measure, Expression, Used In, and ID.
    """
    all_rows_with_expression = []
    all_rows_without_expression = []
    report_filter = filters.get("Report") if filters else None
    report_pattern = (
        "|".join([f"*{report_name}.Report*" for report_name in report_filter])
        if report_filter
        else "*.Report*"
    )

    for root, _, files in os.walk(directory_path):
        if fnmatch.fnmatch(root, report_pattern):
            for file in files:
                if file.endswith(".json"):
                    json_file_path = os.path.join(root, file)

                    # Extract metadata from the JSON file
                    file_metadata = _extract_metadata_from_file(json_file_path, filters)

                    # Separate the extracted rows
                    rows_with_expression = [
                        row for row in file_metadata if row["Expression"] is not None
                    ]
                    rows_without_expression = [
                        row for row in file_metadata if row["Expression"] is None
                    ]

                    # Aggregate all rows with and without expressions
                    all_rows_with_expression.extend(rows_with_expression)
                    all_rows_without_expression.extend(rows_without_expression)

    # Add expressions from rows_with_expression to rows_without_expression if applicable
    for row_without in all_rows_without_expression:
        for row_with in all_rows_with_expression:
            if (
                row_without["Report"] == row_with["Report"]
                and row_without["Table"] == row_with["Table"]
                and row_without["Column or Measure"] == row_with["Column or Measure"]
            ):
                row_without["Expression"] = row_with["Expression"]
                break  # Stop looking once a match is found

    # Ensure rows_with_expression that were not used anywhere are added to rows_without_expression
    final_rows = all_rows_without_expression + [
        row
        for row in all_rows_with_expression
        if not any(
            row["Report"] == r["Report"]
            and row["Table"] == r["Table"]
            and row["Column or Measure"] == r["Column or Measure"]
            for r in all_rows_without_expression
        )
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
    directory_path: str, csv_output_path: str, filters: dict = None
):
    """
    Exports the extracted Power BI Enhanced Report Format (PBIR) metadata to a CSV file.

    This function processes JSON files representing Power BI reports, extracting information about
    tables, columns, measures, their expressions, and where they are used within the report. It
    handles multiple JSON files in the given directory, consolidating the extracted information
    into a single CSV output.

    Args:
        directory_path (str): The directory path containing PBIR JSON files.
        csv_output_path (str): The output path for the CSV file containing the extracted metadata.
        filters (dict, optional): A dictionary with column names as keys and sets of allowed values as values.
                                  If a filter key has an empty set/dict, it will be ignored.
                                  If filters is None or an empty dict, all data will be processed.

    Returns:
        None

    The resulting CSV file will contain the following columns:
    - Report: Name of the Power BI report
    - Page: Name of the page within the report (or "NA" if not applicable)
    - Table: Name of the table
    - Column or Measure: Name of the column or measure
    - Expression: DAX expression for measures (if applicable)
    - Used In: Context where the Column or Measure is used (e.g., visual, Drillthrough, Filters, Bookmarks)
    - Used In Detail: Additional context information (e.g., tooltip, legend, Category, etc.)
    - ID: The ID of the artifact where the Column or Measure is used
    """
    metadata = _consolidate_metadata_from_directory(directory_path, filters)

    with open(csv_output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=HEADER_FIELDS)
        writer.writeheader()
        writer.writerows(metadata)
