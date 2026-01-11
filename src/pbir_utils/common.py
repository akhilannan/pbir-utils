import json
from pathlib import Path
import re
import sys
from typing import Callable, Generator, Any

from .console_utils import console

__all__ = [
    "load_json",
    "write_json",
    "resolve_report_path",
    "get_report_paths",
    "find_report_folders",
    "iter_pages",
    "iter_visuals",
    "extract_visual_info",
    "walk_json_files",
    "process_json_files",
    "traverse_pbir_json",
    "iter_merged_fields",
    "FLOAT_PRESERVE_PREFIX",
]

# Magic prefix for preserving float precision during JSON round-trips.
# Floats are loaded as strings with this prefix, then the prefix (and quotes)
# are removed during write_json to restore the original numeric representation.
FLOAT_PRESERVE_PREFIX = "@@__PRESERVE_FLOAT__@@"
_FLOAT_RESTORE_PATTERN = re.compile(
    r'"'
    + re.escape(FLOAT_PRESERVE_PREFIX)
    + r'(-?[0-9]+\.?[0-9]*(?:[eE][+-]?[0-9]+)?)"'
)

# Keys to skip during traverse_pbir_json - contain redundant or unresolvable data
_SKIP_KEYS = frozenset({"queryRef", "nativeQueryRef", "metadata", "Subquery"})

# Keys that update usage_detail (describe where in a visual the field is used)
_USAGE_DETAIL_KEYS = frozenset(
    {
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
    }
)

# Keys that indicate filter context
_FILTER_KEYS = frozenset({"filters", "filter", "parameters"})


def _preserve_float(s: str) -> str:
    """Hook for json.load to preserve float precision as a prefixed string."""
    return FLOAT_PRESERVE_PREFIX + s


def load_json(file_path: str | Path) -> dict:
    """
    Loads and returns the content of a JSON file.

    Args:
        file_path (str | Path): Path to the JSON file.

    Returns:
        dict: Parsed JSON data.

    Raises:
        json.JSONDecodeError: If the JSON cannot be parsed.
        IOError: If the file cannot be read.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file, parse_float=_preserve_float)
    except json.JSONDecodeError:
        console.print_error(f"Unable to parse JSON in file: {file_path}")
    except IOError as e:
        console.print_error(f"Unable to read or write file: {file_path}. {str(e)}")
    return {}


def write_json(file_path: str | Path, data: dict) -> None:
    """
    Write JSON data to a file with indentation.

    Args:
        file_path (str | Path): The path to the file where JSON data will be written.
        data (dict): The JSON data to be written to the file.

    Returns:
        None
    """
    json_str = json.dumps(data, indent=2)
    # Restore preserved floats: remove quotes and magic prefix
    json_str = _FLOAT_RESTORE_PATTERN.sub(r"\1", json_str)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(json_str)


def validate_report_path(path_arg: str | Path | None) -> Path:
    """
    Validate that a path is a valid PBIR report folder.

    Args:
        path_arg: The path to check.

    Returns:
        Path: The resolved absolute path to the report folder.

    Raises:
        ValueError: If path_arg is None/empty.
        FileNotFoundError: If path does not exist or is not a valid report folder.
    """
    if not path_arg:
        # Check if CWD is a .Report folder
        cwd = Path.cwd()
        if cwd.name.lower().endswith(".report"):
            return cwd
        raise ValueError(
            "Report path not provided and current directory is not a .Report folder."
        )

    path = Path(path_arg).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    if not path.is_dir():
        raise FileNotFoundError(f"Path is not a directory: {path}")

    # Strict validation: require definition/report.json to exist
    report_json = path / "definition" / "report.json"
    if not report_json.exists():
        raise FileNotFoundError(
            f"Path does not appear to be a valid PBIR report (missing definition/report.json): {path}"
        )

    return path


def resolve_report_path(path_arg: str | None) -> str:
    """
    Resolves the report path.
    If path_arg is provided, returns it.
    If not, checks if CWD is a report folder (ends with .Report).
    If yes, returns CWD.
    Otherwise, exits with error.
    """
    try:
        return str(validate_report_path(path_arg))
    except (ValueError, FileNotFoundError) as e:
        console.print_error(str(e))
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
    dir_path = Path(directory_path)
    report_json = dir_path / "definition" / "report.json"

    if dir_path.name.endswith(".Report") and report_json.exists():
        return [str(report_json)]

    reports = reports or [
        d.name for d in dir_path.iterdir() if d.is_dir() and d.name.endswith(".Report")
    ]
    reports = [f"{r}.Report" if not r.endswith(".Report") else r for r in reports]

    report_paths = []
    for report in reports:
        report_file = dir_path / report / "definition" / "report.json"
        if report_file.exists():
            report_paths.append(str(report_file))
        else:
            console.print_warning(f"Report file not found: {report_file}")

    return report_paths


def find_report_folders(directory_path: str) -> list[str]:
    """
    Recursively find all .Report directories in the given path.

    Args:
        directory_path (str): The root directory to search.

    Returns:
        list: A list of absolute paths to .Report directories.
    """
    dir_path = Path(directory_path)
    report_paths: list[str] = []

    # Check if the directory_path itself is a report folder
    if dir_path.name.endswith(".Report") and (dir_path / "definition").exists():
        report_paths.append(str(dir_path))
    else:
        # Search recursively for .Report folders
        for item in dir_path.rglob("*.Report"):
            if item.is_dir():
                report_paths.append(str(item))
    return report_paths


def iter_pages(report_path: str | Path) -> Generator[tuple[str, str, dict], None, None]:
    """
    Iterate over pages in a Power BI report.

    Args:
        report_path: Path to the report root folder (e.g., MyReport.Report).

    Yields:
        tuple: (page_id, page_folder_path, page_data) for each valid page.
            - page_id: The unique identifier of the page (from page.json "name" field)
            - page_folder_path: Full path to the page folder
            - page_data: Parsed contents of page.json
    """
    pages_dir = Path(report_path) / "definition" / "pages"
    if not pages_dir.is_dir():
        return

    for folder_path in pages_dir.iterdir():
        if not folder_path.is_dir():
            continue

        page_json_path = folder_path / "page.json"
        if not page_json_path.exists():
            continue

        page_data = load_json(page_json_path)
        page_id = page_data.get("name", folder_path.name)  # Fallback to folder name
        yield page_id, str(folder_path), page_data


def iter_visuals(
    page_folder: str | Path,
) -> Generator[tuple[str, str, dict], None, None]:
    """
    Iterate over visuals in a page folder.

    Args:
        page_folder: Path to the page folder containing a 'visuals' subdirectory.

    Yields:
        tuple: (visual_id, visual_folder_path, visual_data) for each valid visual.
            - visual_id: The unique identifier of the visual (from visual.json "name" field)
            - visual_folder_path: Full path to the visual folder
            - visual_data: Parsed contents of visual.json
    """
    visuals_dir = Path(page_folder) / "visuals"
    if not visuals_dir.is_dir():
        return

    for folder_path in visuals_dir.iterdir():
        if not folder_path.is_dir():
            continue

        visual_json_path = folder_path / "visual.json"
        if not visual_json_path.exists():
            continue

        visual_data = load_json(visual_json_path)
        visual_id = visual_data.get("name", folder_path.name)  # Fallback to folder name
        yield visual_id, str(folder_path), visual_data


def extract_visual_info(page_folder: str | Path, include_fields: bool = False) -> dict:
    """
    Extract visual information from all visuals in a page folder.

    Args:
        page_folder: Path to the page folder containing a 'visuals' subdirectory.
        include_fields: If True, extract field usage for each visual.

    Returns:
        dict: A dictionary with visual IDs as keys and dicts of visual info as values.
              Each dict contains: x, y, width, height, visualType, parentGroupName, isHidden.
              If include_fields is True, also contains "fields" dict.
    """
    visuals = {}
    for visual_id, _, visual_data in iter_visuals(page_folder):
        position = visual_data.get("position", {})
        info = {
            "x": position.get("x"),
            "y": position.get("y"),
            "z": position.get("z", 0),
            "width": position.get("width"),
            "height": position.get("height"),
            "visualType": visual_data.get("visual", {}).get("visualType", "Group"),
            "parentGroupName": visual_data.get("parentGroupName"),
            "isHidden": visual_data.get("isHidden", False),
        }

        if include_fields:
            fields = {}

            for table, field, _, expression, _, attr_type in iter_merged_fields(
                visual_data, info["visualType"]
            ):
                if table not in fields:
                    fields[table] = {"columns": set(), "measures": set()}
                if attr_type == "Measure" or expression:
                    fields[table]["measures"].add(field)
                else:
                    fields[table]["columns"].add(field)

            # Convert sets to sorted lists
            for table in fields:
                fields[table]["columns"] = sorted(fields[table]["columns"])
                fields[table]["measures"] = sorted(fields[table]["measures"])

            info["fields"] = fields

        visuals[visual_id] = info
    return visuals


def walk_json_files(
    directory: str | Path, file_pattern: str
) -> Generator[str, None, None]:
    """
    Walk through JSON files in a directory matching a specific pattern.

    Args:
        directory (str | Path): The directory to search in.
        file_pattern (str): The file pattern to match (e.g., ".json").

    Yields:
        str: The full path of each matching file.
    """
    # Validate directory path to prevent traversal
    dir_path = Path(directory).resolve()
    if not dir_path.is_dir():
        return

    # Convert file_pattern to glob pattern (e.g., ".json" -> "*.json")
    glob_pattern = (
        f"*{file_pattern}" if not file_pattern.startswith("*") else file_pattern
    )

    for file_path in dir_path.rglob(glob_pattern):
        if file_path.is_file():
            # Ensure the file path is within the intended directory
            try:
                file_path.relative_to(dir_path)
                yield str(file_path)
            except ValueError:
                # File is outside the directory (shouldn't happen with rglob, but safety check)
                continue


def process_json_files(
    directory: str | Path,
    file_pattern: str,
    func: Callable,
    process: bool = False,
    dry_run: bool = False,
) -> list | int:
    """
    Process or check JSON files in a directory.

    Args:
        directory (str | Path): The directory to search in.
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
    data: dict | list,
    usage_context: str = None,
    usage_detail: str = None,
    attribute_type: str = None,
) -> Generator[tuple[Any, Any, Any, Any, Any, Any], None, None]:
    """
    Recursively traverses Power BI Enhanced Report Format (PBIR) JSON to extract metadata.

    Navigates through the PBIR JSON structure, extracting entities, properties,
    visuals, filters, bookmarks, and measures.

    Args:
        data: The PBIR JSON data to traverse (dict or list).
        usage_context: Current context (e.g., visual type, filter, bookmark).
        usage_detail: Detailed context (e.g., tooltip, legend, Category).
        attribute_type: Field type - "Column" or "Measure".

    Yields:
        tuple: (table, column, used_in, expression, used_in_detail, attribute_type)
    """
    # Handle list: recurse into each item
    if isinstance(data, list):
        for item in data:
            yield from traverse_pbir_json(
                item, usage_context, usage_detail, attribute_type
            )
        return

    # Only process dicts
    if not isinstance(data, dict):
        return

    for key, value in data.items():
        new_usage_detail = usage_detail or usage_context

        # Skip keys that contain redundant or unresolvable data
        if key in _SKIP_KEYS:
            continue

        # Yield Entity/Property directly
        if key == "Entity":
            yield (
                value,
                None,
                usage_context,
                None,
                usage_detail,
                attribute_type or "Column",
            )

        elif key == "Property":
            yield (
                None,
                value,
                usage_context,
                None,
                usage_detail,
                attribute_type or "Column",
            )

        # Measure wrapper: recurse with attribute_type="Measure"
        elif key == "Measure":
            yield from traverse_pbir_json(value, usage_context, usage_detail, "Measure")

        # Keys that update usage_detail
        elif key in _USAGE_DETAIL_KEYS:
            yield from traverse_pbir_json(value, usage_context, key, attribute_type)

        # Filter-related keys
        elif key in _FILTER_KEYS:
            yield from traverse_pbir_json(
                value, usage_context, "filter", attribute_type
            )

        # Visual key: extract visualType as context
        elif key == "visual":
            visual_type = (
                value.get("visualType", "visual")
                if isinstance(value, dict)
                else "visual"
            )
            yield from traverse_pbir_json(
                value, visual_type, new_usage_detail, attribute_type
            )

        # Page binding (drillthrough)
        elif key == "pageBinding":
            binding_type = (
                value.get("type", "Drillthrough")
                if isinstance(value, dict)
                else "Drillthrough"
            )
            yield from traverse_pbir_json(
                value, binding_type, new_usage_detail, attribute_type
            )

        # Filter config: set context to "Filters"
        elif key == "filterConfig":
            yield from traverse_pbir_json(
                value, "Filters", new_usage_detail, attribute_type
            )

        # Bookmarks: set context to "Bookmarks"
        elif key == "explorationState":
            yield from traverse_pbir_json(
                value, "Bookmarks", new_usage_detail, attribute_type
            )

        # Entities with measures (model extensions)
        elif key == "entities":
            for entity in value:
                table_name = entity.get("name")
                for measure in entity.get("measures", []):
                    yield (
                        table_name,
                        measure.get("name"),
                        usage_context,
                        measure.get("expression"),
                        new_usage_detail,
                        "Measure",
                    )

        # Default: recurse into value
        else:
            yield from traverse_pbir_json(
                value, usage_context, new_usage_detail, attribute_type
            )


def iter_merged_fields(
    data: dict | list,
    usage_context: str = None,
) -> Generator[tuple[str, str, str, str | None, str, str], None, None]:
    """
    Iterate over merged Entity/Property pairs from PBIR JSON.

    Wraps traverse_pbir_json and handles the pending_table/pending_attr_type
    merge logic, yielding only complete (table, field) tuples.

    Args:
        data: The PBIR JSON data to traverse.
        usage_context: Current context (e.g., visual type, filter, bookmark).

    Yields:
        tuple: (table, field, used_in, expression, used_in_detail, attr_type)
               Only yields when both table AND field are resolved.
    """
    pending_table = None
    pending_attr_type = None

    for (
        table,
        field,
        used_in,
        expression,
        used_in_detail,
        attr_type,
    ) in traverse_pbir_json(data, usage_context):
        # Case 1: Complete pair (expression rows from entities)
        if table and field:
            yield (table, field, used_in, expression, used_in_detail, attr_type)
            pending_table = None

        # Case 2: Entity only - store for next Property
        elif table and not field:
            pending_table = table
            pending_attr_type = attr_type

        # Case 3: Property only - merge with pending Entity
        elif field and not table and pending_table:
            final_attr = attr_type or pending_attr_type
            yield (
                pending_table,
                field,
                used_in,
                expression,
                used_in_detail,
                final_attr,
            )
            pending_table = None
