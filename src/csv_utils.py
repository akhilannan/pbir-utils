import csv


def load_csv_mapping(csv_path):
    """
    Load a CSV file and return a list of dictionaries mapping from old (entity, column) pairs
    to new (entity, column) pairs, filtering out invalid rows based on specified conditions.
    
    Parameters:
    - csv_path: Path to the CSV file.
    
    Returns:
    - A list of dictionaries with keys as 'old_tbl', 'old_col', 'new_tbl', 'new_col'.
    """
    mappings = []
    with open(csv_path, 'r', newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        expected_columns = ['old_tbl', 'old_col', 'new_tbl', 'new_col']
        # Strip BOM from the column names if present
        fieldnames = [name.lstrip('\ufeff') for name in reader.fieldnames]
        if not all(col in fieldnames for col in expected_columns):
            raise ValueError(f"CSV file must contain the following columns: {', '.join(expected_columns)}")
        for row in reader:
            old_tbl, old_col, new_tbl, new_col = row['old_tbl'], row['old_col'], row['new_tbl'], row['new_col']
            if old_tbl and (new_tbl or (old_col and new_col)):
                mappings.append(row)
    return mappings