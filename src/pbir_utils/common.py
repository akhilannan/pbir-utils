import json
import os
import sys
from typing import Callable, Generator, Any


def load_json(file_path: str) -> dict:
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


def write_json(file_path: str, data: dict) -> None:
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


def resolve_report_path(path_arg: str | None) -> str:
    """
    Resolves the report path.
    If path_arg is provided, returns it.
    If not, checks if CWD is a report folder (ends with .Report).
    If yes, returns CWD.
    Otherwise, exits with error.
    """
    if path_arg:
        return path_arg

    cwd = os.getcwd()
    if cwd.lower().endswith(".report"):
        return cwd

    print(
        "Error: report_path not provided and current directory is not a .Report folder.",
        file=sys.stderr,
    )
    sys.exit(1)


def get_report_paths(directory_path: str, reports: list = None) -> list:
    """
    Retrieves the paths to the report JSON files in the specified root folder.

    Parameters:
    directory_path (str): Root folder containing reports.
    reports (list, optional): List of reports to update. Defaults to None.

    Returns:
    list: List of paths to report JSON files.
    """
    reports = reports or [
        d for d in os.listdir(directory_path) if d.endswith(".Report")
    ]
    reports = [f"{r}.Report" if not r.endswith(".Report") else r for r in reports]

    report_paths = []
    for report in reports:
        report_path = os.path.join(directory_path, report, "definition", "report.json")
        if os.path.exists(report_path):
            report_paths.append(report_path)
        else:
            print(f"Report file not found: {report_path}")

    return report_paths


def walk_json_files(directory: str, file_pattern: str) -> Generator[str, None, None]:
    """
    Walk through JSON files in a directory matching a specific pattern.

    Args:
        directory (str): The directory to search in.
        file_pattern (str): The file pattern to match.

    Yields:
        str: The full path of each matching file.
    """
    # Validate directory path to prevent traversal
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        return

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(file_pattern):
                file_path = os.path.join(root, file)
                # Ensure the file path is within the intended directory
                if (
                    os.path.commonpath([directory, os.path.abspath(file_path)])
                    == directory
                ):
                    yield file_path


def process_json_files(
    directory: str,
    file_pattern: str,
    func: Callable,
    process: bool = False,
    dry_run: bool = False,
) -> list | int:
    """
    Process or check JSON files in a directory.

    Args:
        directory (str): The directory to search in.
        file_pattern (str): The file pattern to match.
        func (callable): The function to apply to each file's data.
        process (bool): Whether to process the files or just check.

    Returns:
        list: A list of results or the count of modified files.
    """
    results = []
    modified_count = 0
    for file_path in walk_json_files(directory, file_pattern):
        data = load_json(file_path)
        result = func(data, file_path)
        if process and result:
            if not dry_run:
                write_json(file_path, data)
            modified_count += 1
        elif not process and result:
            results.append((file_path, result))
    return modified_count if process else results


def traverse_pbir_json(
    data: dict | list, usage_context: str = None, usage_detail: str = None
) -> Generator[tuple[Any, Any, Any, Any, Any], None, None]:
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
                yield from traverse_pbir_json(value, usage_context, key)
            elif key == "queryRef":
                yield (None, value, usage_context, None, usage_detail)
            elif key in ["filters", "filter", "parameters"]:
                yield from traverse_pbir_json(value, usage_context, "filter")
            elif key == "visual":
                visual_type = "visual"
                if isinstance(value, dict):
                    visual_type = value.get("visualType", "visual")
                yield from traverse_pbir_json(value, visual_type, new_usage_detail)
            elif key == "pageBinding":
                yield from traverse_pbir_json(
                    value, value.get("type", "Drillthrough"), new_usage_detail
                )
            elif key == "filterConfig":
                yield from traverse_pbir_json(value, "Filters", new_usage_detail)
            elif key == "explorationState":
                yield from traverse_pbir_json(value, "Bookmarks", new_usage_detail)
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
                yield from traverse_pbir_json(value, usage_context, new_usage_detail)
    elif isinstance(data, list):
        for item in data:
            yield from traverse_pbir_json(item, usage_context, usage_detail)
