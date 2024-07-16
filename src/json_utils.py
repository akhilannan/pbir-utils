import re


def update_dax_expression(expression, table_map=None, column_map=None):
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
            quotes = match.group(1) or ''
            table_name = match.group(2) or match.group(3)  # Group 2 for quoted, Group 3 for unquoted
            
            if table_name in table_map:
                new_table = table_map[table_name]
                if ' ' in new_table and not quotes:
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
                if ' ' in table_name or table_part.startswith("'"):
                    table_part = f"'{table_name}'"
                else:
                    table_part = table_name
                return f"{table_part}[{new_column}]"
            return full_match

        # Pattern to match table[column], 'table'[column], or 'table name'[column]
        pattern = re.compile(r"('[A-Za-z0-9_ ]+'?|[A-Za-z0-9_]+)\[([A-Za-z0-9_]+)\]")
        expression = pattern.sub(replace_column_name, expression)

    return expression


def update_entity(data, table_map):
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
                    data[key] = update_dax_expression(original_expression, table_map=table_map)
                    if data[key] != original_expression:
                        updated = True
                else:
                    traverse_and_update(value)
        elif isinstance(data, list):
            for item in data:
                traverse_and_update(item)

    traverse_and_update(data)
    return updated


def update_property(data, column_map):
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
                    entity = value.get("Expression", {}).get("SourceRef", {}).get("Entity")
                    property = value.get("Property")
                    if entity and property:
                        if (entity, property) in column_map:
                            new_property = column_map[(entity, property)]
                            value["Expression"]["SourceRef"]["Entity"] = entity
                            value["Property"] = new_property
                            updated = True
                elif key == "expression" and isinstance(value, str):
                    original_expression = value
                    value = update_dax_expression(original_expression, column_map=column_map)
                    if value != original_expression:
                        data[key] = value
                        updated = True
                elif key == "filter":
                    if "From" in value and "Where" in value:
                        from_entity = value["From"][0]["Entity"]
                        for condition in value["Where"]:
                            column = condition.get("Condition", {}).get("Not", {}).get("Expression", {}).get("In", {}).get("Expressions", [{}])[0].get("Column", {})
                            property = column.get("Property")
                            if property:
                                if (from_entity, property) in column_map:
                                    new_property = column_map[(from_entity, property)]
                                    column["Property"] = new_property
                                    updated = True
                else:
                    traverse_and_update(value)
        elif isinstance(data, list):
            for item in data:
                traverse_and_update(item)

    traverse_and_update(data)
    return updated