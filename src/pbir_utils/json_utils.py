import json


def _load_json(file_path: str) -> dict:
    """
    Loads and returns the content of a JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        dict: Parsed JSON data.

    Raises:
        json.JSONDecodeError: If the JSON cannot be parsed.
        IOError: If the file cannot be read.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        print(f"Error: Unable to parse JSON in file: {file_path}")
    except IOError as e:
        print(f"Error: Unable to read or write file: {file_path}. {str(e)}")
    return {}


def _write_json(file_path: str, data: dict) -> None:
    """
    Write JSON data to a file with indentation.

    Args:
        file_path (str): The path to the file where JSON data will be written.
        data (dict): The JSON data to be written to the file.

    Returns:
        None
    """
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)