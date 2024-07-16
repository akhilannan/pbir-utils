import json
import os
from .csv_utils import load_csv_mapping
from .json_utils import update_entity, update_property


def update_pbir_component(file_path, table_map, column_map):
    """
    Update a single component within a Power BI Enhanced Report Format (PBIR) structure.
    
    This function processes a single JSON file representing a PBIR component (e.g., visual, page, bookmark)
    and updates table and column references based on the provided mappings.
    
    Parameters:
    - file_path: Path to the PBIR component JSON file.
    - table_map: A dictionary mapping old table names to new table names.
    - column_map: A dictionary mapping old (table, column) pairs to new column names.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        
        entity_updated = False
        property_updated = False

        if table_map:
            entity_updated = update_entity(data, table_map)
            if entity_updated:
                print(f"Entity updated in file: {file_path}")

        if column_map:
            property_updated = update_property(data, column_map)
            if property_updated:
                print(f"Property updated in file: {file_path}")

        if entity_updated or property_updated:
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, indent=2)
    except json.JSONDecodeError:
        print(f"Error: Unable to parse JSON in file: {file_path}")
    except IOError as e:
        print(f"Error: Unable to read or write file: {file_path}. {str(e)}")


def batch_update_pbir_project(directory_path, csv_path):
    """
    Perform a batch update on all components of a Power BI Enhanced Report Format (PBIR) project.
    
    This function processes all JSON files in a PBIR project directory, updating table and column
    references based on a CSV mapping file. It's designed to work with the PBIR folder structure,
    which separates report components into individual files.
    
    Parameters:
    - directory_path: Path to the root directory of the PBIR project (usually the 'definition' folder).
    - csv_path: Path to the CSV file with the mapping of old and new table/column names.
    """
    try:
        mappings = load_csv_mapping(csv_path)
        
        table_map = {}
        column_map = {}
        
        for row in mappings:
            old_tbl, old_col, new_tbl, new_col = row['old_tbl'], row['old_col'], row['new_tbl'], row['new_col']
            if new_tbl and new_tbl != old_tbl:
                table_map[old_tbl] = new_tbl
            if old_col and new_col:
                effective_tbl = table_map.get(old_tbl, old_tbl)
                column_map[(effective_tbl, old_col)] = new_col
        
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    update_pbir_component(file_path, table_map, column_map)
    except Exception as e:
        print(f"An error occurred: {str(e)}")