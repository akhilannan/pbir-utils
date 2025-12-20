import csv
import os
import re

from .common import load_json, write_json
from .console_utils import console


def _load_csv_mapping(csv_path: str) -> list[dict]:
    """
    Load a CSV file and return a list of dictionaries mapping from old (entity, column) pairs
    to new (entity, column) pairs, filtering out invalid rows based on specified conditions.

    Parameters:
    - csv_path: Path to the CSV file.

    Returns:
    - A list of dictionaries with keys as 'old_tbl', 'old_col', 'new_tbl', 'new_col'.
    """
    mappings = []
    with open(csv_path, "r", newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        expected_columns = ["old_tbl", "old_col", "new_tbl", "new_col"]
        # Strip BOM from the column names if present
        fieldnames = [name.lstrip("\ufeff") for name in reader.fieldnames]
        if not all(col in fieldnames for col in expected_columns):
            raise ValueError(
                f"CSV file must contain the following columns: {', '.join(expected_columns)}"
            )
        for row in reader:
            old_tbl, old_col, new_tbl, new_col = (
                row["old_tbl"],
                row["old_col"],
                row["new_tbl"],
                row["new_col"],
            )
            if old_tbl and (new_tbl or (old_col and new_col)):
                mappings.append(row)
    return mappings


def _update_dax_expression(
    expression: str, table_map: dict = None, column_map: dict = None
) -> str:
    """
    Update DAX expressions based on table_map and/or column_map.

    Parameters:
    - expression: The DAX expression to update.
    - table_map: A dictionary mapping old table names to new table names.
    - column_map: A dictionary mapping old (table, column) pairs to new (table, column) pairs.

    Returns:
    - Updated DAX expression.
    """
    if table_map:

        def replace_table_name(match):
            full_match = match.group(0)
            quotes = match.group(1) or ""
            table_name = match.group(2) or match.group(
                3
            )  # Group 2 for quoted, Group 3 for unquoted

            if table_name in table_map:
                new_table = table_map[table_name]
                if " " in new_table and not quotes:
                    return f"'{new_table}'"
                return f"{quotes}{new_table}{quotes}"
            return full_match

        # Updated pattern to match both quoted and unquoted table names, avoiding those inside square brackets
        pattern = re.compile(r"(?<!\[)('+)?(\b[\w\s]+?\b)\1|\b([\w]+)\b(?!\])")
        expression = pattern.sub(replace_table_name, expression)

    if column_map:

        def replace_column_name(match):
            full_match = match.group(0)
            table_part = match.group(1)
            column_name = match.group(2)

            # Remove quotes from table name for lookup
            table_name = table_part.strip("'")

            if (table_name, column_name) in column_map:
                new_column = column_map[(table_name, column_name)]
                # Preserve original quoting style if no spaces in new table name
                if " " in table_name or table_part.startswith("'"):
                    table_part = f"'{table_name}'"
                else:
                    table_part = table_name
                return f"{table_part}[{new_column}]"
            return full_match

        # Pattern to match table[column], 'table'[column], or 'table name'[column]
        pattern = re.compile(r"('[A-Za-z0-9_ ]+'?|[A-Za-z0-9_]+)\[([A-Za-z0-9_]+)\]")
        expression = pattern.sub(replace_column_name, expression)

    return expression


def _update_entity(data: dict, table_map: dict) -> bool:
    """
    Update the "Entity" fields and DAX expressions in the JSON data based on the table_map.

    Parameters:
    - data: The JSON data to update.
    - table_map: A dictionary mapping old table names to new table names.

    Returns:
    - True if any updates were made, False otherwise.
    """
    updated = False

    def traverse_and_update(data):
        nonlocal updated
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "Entity" and value in table_map:
                    data[key] = table_map[value]
                    updated = True
                elif key == "entities":
                    for entity in value:
                        if "name" in entity and entity["name"] in table_map:
                            entity["name"] = table_map[entity["name"]]
                            updated = True
                        traverse_and_update(entity)
                elif key == "expression" and isinstance(value, str):
                    original_expression = value
                    data[key] = _update_dax_expression(
                        original_expression, table_map=table_map
                    )
                    if data[key] != original_expression:
                        updated = True
                else:
                    traverse_and_update(value)
        elif isinstance(data, list):
            for item in data:
                traverse_and_update(item)

    traverse_and_update(data)
    return updated


def _update_property(data: dict, column_map: dict) -> bool:
    """
    Update the "Property" fields in the JSON data based on the column_map and updated table names.

    Parameters:
    - data: The JSON data to update.
    - column_map: A dictionary mapping old (table, column) pairs to new (table, column) pairs.

    Returns:
    - True if any updates were made, False otherwise.
    """
    updated = False

    def traverse_and_update(data):
        nonlocal updated
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ["Column", "Measure"]:
                    entity = (
                        value.get("Expression", {}).get("SourceRef", {}).get("Entity")
                    )
                    property = value.get("Property")
                    if entity and property:
                        if (entity, property) in column_map:
                            new_property = column_map[(entity, property)]
                            value["Expression"]["SourceRef"]["Entity"] = entity
                            value["Property"] = new_property
                            updated = True
                elif key == "expression" and isinstance(value, str):
                    original_expression = value
                    value = _update_dax_expression(
                        original_expression, column_map=column_map
                    )
                    if value != original_expression:
                        data[key] = value
                        updated = True
                elif key == "filter" and isinstance(value, dict):
                    from_entity = None
                    if (
                        "From" in value
                        and "Where" in value
                        and value["From"]
                        and "Entity" in value["From"][0]
                    ):
                        from_entity = value["From"][0]["Entity"]

                    if "Where" in value and isinstance(value["Where"], list):
                        for condition in value["Where"]:
                            # Attempt to find Column property deep in the Condition structure
                            # This handles common categorical filter structures
                            try:
                                column = (
                                    condition.get("Condition", {})
                                    .get("Not", {})
                                    .get("Expression", {})
                                    .get("In", {})
                                    .get("Expressions", [{}])[0]
                                    .get("Column", {})
                                )
                                property = column.get("Property")
                                if property and from_entity:
                                    if (from_entity, property) in column_map:
                                        new_property = column_map[
                                            (from_entity, property)
                                        ]
                                        column["Property"] = new_property
                                        updated = True
                            except (AttributeError, KeyError, IndexError):
                                pass
                else:
                    traverse_and_update(value)
        elif isinstance(data, list):
            for item in data:
                traverse_and_update(item)

    traverse_and_update(data)
    return updated


def _update_pbir_component(
    file_path: str, table_map: dict, column_map: dict, dry_run: bool = False
) -> bool:
    """
    Update a single component within a Power BI Enhanced Report Format (PBIR) structure.

    This function processes a single JSON file representing a PBIR component (e.g., visual, page, bookmark)
    and updates table and column references based on the provided mappings.

    Parameters:
    - file_path: Path to the PBIR component JSON file.
    - table_map: A dictionary mapping old table names to new table names.
    - column_map: A dictionary mapping old (table, column) pairs to new column names.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    data = load_json(file_path)

    entity_updated = False
    property_updated = False

    if table_map:
        entity_updated = _update_entity(data, table_map)
        if entity_updated:
            console.print_success(f"Entity updated in file: {file_path}")

    if column_map:
        property_updated = _update_property(data, column_map)
        if property_updated:
            console.print_success(f"Property updated in file: {file_path}")

    if entity_updated or property_updated:
        if not dry_run:
            write_json(file_path, data)
        else:
            console.print_dry_run(f"Would update {file_path}")
        return True
    return False


def batch_update_pbir_project(
    directory_path: str, csv_path: str, dry_run: bool = False
) -> bool:
    """
    Perform a batch update on all components of a Power BI Enhanced Report Format (PBIR) project.

    This function processes all JSON files in a PBIR project directory, updating table and column
    references based on a CSV mapping file. It's designed to work with the PBIR folder structure,
    which separates report components into individual files.

    Parameters:
    - directory_path: Path to the root directory of the PBIR project (usually the 'definition' folder).
    - csv_path: Path to the CSV file with the mapping of old and new table/column names.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    console.print_action_heading("Batch updating PBIR project", dry_run)
    any_changes = False
    error_occurred = False
    try:
        mappings = _load_csv_mapping(csv_path)

        table_map = {}
        column_map = {}

        for row in mappings:
            old_tbl, old_col, new_tbl, new_col = (
                row["old_tbl"],
                row["old_col"],
                row["new_tbl"],
                row["new_col"],
            )
            if new_tbl and new_tbl != old_tbl:
                table_map[old_tbl] = new_tbl
            if old_col and new_col:
                effective_tbl = table_map.get(old_tbl, old_tbl)
                column_map[(effective_tbl, old_col)] = new_col

        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(root, file)
                    if _update_pbir_component(
                        file_path, table_map, column_map, dry_run=dry_run
                    ):
                        any_changes = True
    except Exception as e:
        error_occurred = True
        console.print_error(f"An error occurred: {str(e)}")

    if not any_changes and not error_occurred:
        console.print_info("No changes needed. All attributes are already up to date.")

    return any_changes
