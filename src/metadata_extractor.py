import json
import os
import csv


def extract_report_name(json_file_path):
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


def extract_active_section(bookmark_json_path):
    """
    Extracts the active section from the bookmarks JSON file.

    Args:
        bookmark_json_path (str): The file path to the bookmarks JSON file.

    Returns:
        str: The active section if found, otherwise an empty string.
    """
    if "bookmarks" in bookmark_json_path:
        try:
            with open(bookmark_json_path, "r", encoding="utf-8") as file:
                return (
                    json.load(file).get("explorationState", {}).get("activeSection", "")
                )
        except (IOError, json.JSONDecodeError):
            return ""
    else:
        parts = bookmark_json_path.split(os.sep)
        return parts[parts.index("pages") + 1] if "pages" in parts else ""


def extract_page_name(json_path):
    """
    Extracts the page name from the JSON file path.

    Args:
        json_path (str): The file path to the JSON file.

    Returns:
        str: The extracted page name if found, otherwise "NA".
    """
    active_section = extract_active_section(json_path)
    if not active_section:
        return "NA"
    base_path = json_path.split("definition")[0]
    page_json_path = os.path.join(
        base_path, "definition", "pages", active_section, "page.json"
    )
    try:
        with open(page_json_path, "r", encoding="utf-8") as file:
            return json.load(file).get("displayName", "NA")
    except (IOError, json.JSONDecodeError):
        return "NA"


def traverse_pbir_json_structure(data, context=None):
    """
    Recursively traverses the Power BI Enhanced Report Format (PBIR) JSON structure to extract specific metadata.

    This function navigates through the complex PBIR JSON structure, identifying and extracting
    key metadata elements such as entities, properties, visuals, filters, bookmarks, and measures.
    It handles various PBIR-specific components and contexts, providing a comprehensive
    extraction of report structure and data model information.

    Args:
        data (dict or list): The PBIR JSON data to traverse.
        context (str, optional): The current context within the PBIR structure (e.g., visual type, filter, bookmark).

    Yields:
        tuple: Extracted metadata in the form of (table, column, context, expression).
               - table: The name of the table (if applicable)
               - column: The name of the column or measure
               - context: The context in which the element is used (e.g., visual type, filter, bookmark)
               - expression: The DAX expression for measures (if applicable)
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "Entity":
                yield (value, None, context, None)
            elif key == "Property":
                yield (None, value, context, None)
            elif key == "visual":
                yield from traverse_pbir_json_structure(
                    value, value.get("visualType", "visual")
                )
            elif key == "pageBinding":
                yield from traverse_pbir_json_structure(
                    value, value.get("type", "Drillthrough")
                )
            elif key == "filterConfig":
                yield from traverse_pbir_json_structure(value, "Filters")
            elif key == "explorationState":
                yield from traverse_pbir_json_structure(value, "Bookmarks")
            elif key == "entities":
                for entity in value:
                    table_name = entity.get("name")
                    for measure in entity.get("measures", []):
                        yield (
                            table_name,
                            measure.get("name"),
                            context,
                            measure.get("expression", None),
                        )
            else:
                yield from traverse_pbir_json_structure(value, context)
    elif isinstance(data, list):
        for item in data:
            yield from traverse_pbir_json_structure(item, context)


def extract_pbir_component_metadata(directory_path):
    """
    Extracts detailed metadata from all Power BI Enhanced Report Format (PBIR) component files in the specified directory.

    This function traverses through all JSON files in the PBIR project structure, extracting key metadata
    such as report name, page name, table names, column/measure details, DAX expressions, and usage information.
    It processes both visual components and data model elements, consolidating the information into a structured format.

    Args:
        directory_path (str): The root directory path containing PBIR component JSON files.

    Returns:
        list: A list of dictionaries, each representing a unique metadata entry with fields:
            Report, Page, Table, Column or Measure, Expression, and Used In.
    """

    # Extract data from all json files in a directory
    all_rows = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith(".json"):
                json_file_path = os.path.join(root, file)
                report_name = extract_report_name(json_file_path)
                page_name = extract_page_name(json_file_path) or "NA"
                try:
                    with open(json_file_path, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        for (
                            table,
                            column,
                            used_in,
                            expression,
                        ) in traverse_pbir_json_structure(data):
                            all_rows.append(
                                {
                                    "Report": report_name,
                                    "Page": page_name,
                                    "Table": table,
                                    "Column or Measure": column,
                                    "Expression": expression,
                                    "Used In": used_in,
                                }
                            )
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error: Unable to process file {json_file_path}: {str(e)}")

    # Separate rows based on whether they have an "expression" value
    rows_with_expression = [row for row in all_rows if row["Expression"] is not None]
    rows_without_expression = [row for row in all_rows if row["Expression"] is None]

    # This step is done to ensure we get table and respective column in single row
    reformatted_rows = [
        {
            "Report": rows_without_expression[i]["Report"],
            "Page": rows_without_expression[i]["Page"],
            "Table": rows_without_expression[i]["Table"],
            "Column or Measure": rows_without_expression[i + 1]["Column or Measure"],
            "Expression": None,
            "Used In": rows_without_expression[i]["Used In"],
        }
        for i in range(0, len(rows_without_expression), 2)
        if i + 1 < len(rows_without_expression)
    ]

    # This step ensures we add expression to the reformatted_rows based on a join to rows_with_expression
    for row_without in reformatted_rows:
        for row_with in rows_with_expression:
            if (
                row_without["Report"] == row_with["Report"]
                and row_without["Table"] == row_with["Table"]
                and row_without["Column or Measure"] == row_with["Column or Measure"]
            ):
                row_without["Expression"] = row_with["Expression"]
                break  # Stop looking once a match is found

    # Ensure rows_with_expression that were not used anywhere are added to reformatted_rows
    final_rows = reformatted_rows + [
        row
        for row in rows_with_expression
        if not any(
            row["Report"] == r["Report"]
            and row["Table"] == r["Table"]
            and row["Column or Measure"] == r["Column or Measure"]
            for r in reformatted_rows
        )
    ]

    # Extract distinct rows
    unique_rows = []
    seen = set()
    for row in final_rows:
        row_tuple = (
            row["Report"],
            row["Page"],
            row["Table"],
            row["Column or Measure"],
            row["Expression"],
            row["Used In"],
        )
        if row_tuple not in seen:
            unique_rows.append(row)
            seen.add(row_tuple)

    return unique_rows


def export_pbir_metadata_to_csv(directory_path, csv_output_path):
    """
    Exports the extracted Power BI Enhanced Report Format (PBIR) metadata to a CSV file.

    This function processes JSON files representing Power BI reports, extracting information about
    tables, columns, measures, their expressions, and where they are used within the report. It
    handles multiple JSON files in the given directory, consolidating the extracted information
    into a single CSV output.

    Args:
        directory_path (str): The directory path containing PBIR JSON files.
        csv_output_path (str): The output path for the CSV file containing the extracted metadata.

    Returns:
        None

    The resulting CSV file will contain the following columns:
    - Report: Name of the Power BI report
    - Page: Name of the page within the report (or "NA" if not applicable)
    - Table: Name of the table
    - Column or Measure: Name of the column or measure
    - Expression: DAX expression for measures (if applicable)
    - Used In: Context where the item is used (e.g., visual, Drillthrough, Filters, Bookmarks)
    """

    metadata = extract_pbir_component_metadata(directory_path)
    fieldnames = [
        "Report",
        "Page",
        "Table",
        "Column or Measure",
        "Expression",
        "Used In",
    ]
    with open(csv_output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metadata)