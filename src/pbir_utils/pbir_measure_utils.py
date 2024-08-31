import os

from .json_utils import _load_json, _write_json
from .metadata_extractor import _extract_metadata_from_file


def _get_visual_ids_for_measure(report_path: str, measure_name: str) -> list:
    """
    Get a list of visual IDs that use the specified measure.

    Description:
        This function iterates through the visuals in a Power BI report and identifies the IDs
        of visuals that use the given measure.

    Args:
        report_path (str): The file system path to the report folder.
        measure_name (str): The name of the measure to check for usage.

    Returns:
        list: A list of visual IDs (strings) that use the measure.
    """
    visual_ids = []
    for root, _, files in os.walk(report_path):
        if "visual.json" in files:
            visual_file_path = os.path.join(root, "visual.json")
            visual_data = _load_json(visual_file_path)

            # Get visual ID ("name" in visual.json)
            visual_id = visual_data.get("name")

            all_rows = _extract_metadata_from_file(visual_file_path)
            for row in all_rows:
                if row["Column or Measure"] == measure_name:
                    visual_ids.append(visual_id)
    return visual_ids


def _is_measure_used_in_visuals(report_path: str, measure_name: str) -> bool:
    """
    Check if the specified measure is used in any visual.

    Description:
        This function determines whether a given measure is used in any of the visuals within
        a Power BI report.

    Args:
        report_path (str): The file system path to the report folder.
        measure_name (str): The name of the measure to check for usage.

    Returns:
        bool: True if the measure is used in any visual within the report, False otherwise.
    """
    return len(_get_visual_ids_for_measure(report_path, measure_name)) > 0


def _get_dependent_measures(measure_name, measures_dict, visited=None):
    """
    Recursively find all measures that depend on the given measure.

    Description:
        This function identifies all measures that directly or indirectly depend on the
        specified measure by analyzing the expressions of other measures in the report.

    Args:
        measure_name (str): The name of the measure whose dependents are to be found.
        measures_dict (dict): A dictionary of all measures with measure names as keys and
                              expressions as values.
        visited (set): A set to track visited measures during recursion to prevent infinite loops.

    Returns:
        set: A set of all dependent measure names.
    """
    visited = visited or set()

    if measure_name in visited:
        return set()

    visited.add(measure_name)

    dependents = set()

    for other_measure_name, expression in measures_dict.items():
        if f"[{measure_name}]" in expression:
            dependents.add(other_measure_name)
            dependents.update(
                _get_dependent_measures(other_measure_name, measures_dict, visited)
            )

    return dependents


def _is_measure_or_dependents_used_in_visuals(report_path, measure_name, measures_dict):
    """
    Check if a measure or any dependents are used in visuals.

    Description:
        This function checks if a given measure or any of its dependent measures are used
        in any visuals within the Power BI report.

    Args:
        report_path (str): The file system path to the report folder.
        measure_name (str): The name of the measure to check.
        measures_dict (dict): A dictionary of all measures with measure names as keys and
                              expressions as values.

    Returns:
        bool: True if the measure or any of its dependents are used in visuals, False otherwise.
    """
    if _is_measure_used_in_visuals(report_path, measure_name):
        return True

    return any(
        _is_measure_used_in_visuals(report_path, dependent)
        for dependent in _get_dependent_measures(measure_name, measures_dict)
    )


def _load_report_extension_data(report_path: str):
    """
    Helper function to load the Power BI report extension data.

    Description:
        This function loads the report's JSON data from the reportExtensions.json file.

    Args:
        report_path (str): The file system path to the report folder.

    Returns:
        dict: The loaded report extension data as a dictionary.
    """
    report_file = os.path.join(report_path, "definition", "reportExtensions.json")
    return report_file, _load_json(report_file)


def remove_measures(
    report_path: str, measure_names: list = None, check_visual_usage: bool = True
) -> None:
    """
    Removes specified measures or all measures from a PowerBI PBIR report,
    with an optional check for their usage in visuals.

    Description:
        This function allows you to remove specific measures or all measures from a Power BI report.
        It can optionally check if a measure is used in any visual before removing it to
        prevent accidental deletion of measures that are still in use.

    Args:
        report_path (str): The file system path to the report folder.
        measure_names (Optional[List[str]]): A list of measure names to be removed. If None or an empty list,
                                             all measures will be considered for removal. Default is None.
        check_visual_usage (bool): If True, only remove a measure if neither the measure itself nor any of its dependent measures
                                   are used in any visuals. Default is True.

    Returns:
        None
    """
    report_file, report_data = _load_report_extension_data(report_path)

    removed_measures = []
    entities_to_keep = []

    for entity in report_data.get("entities", []):
        measures = entity.get("measures", [])
        measures_dict = {
            measure["name"]: measure.get("expression", "") for measure in measures
        }

        entity["measures"] = [
            measure
            for measure in measures
            if not (
                (
                    measure_names is None
                    or not measure_names
                    or measure["name"] in measure_names
                )
                and (
                    not check_visual_usage
                    or not _is_measure_or_dependents_used_in_visuals(
                        report_path, measure["name"], measures_dict
                    )
                )
            )
        ]

        removed_measures.extend(
            [
                measure["name"]
                for measure in measures
                if measure not in entity["measures"]
            ]
        )

        if entity["measures"]:
            entities_to_keep.append(entity)

    report_data["entities"] = entities_to_keep

    if entities_to_keep:
        _write_json(report_file, report_data)
        print(
            f"Measures removed: {', '.join(removed_measures)}"
            if removed_measures
            else "No measures were removed."
        )
    else:
        os.remove(report_file)
        print("All measures removed. The reportExtensions.json file has been deleted.")


def _format_measure_with_visual_ids(report_path, measure, include_visual_ids):
    """
    Helper function to format a measure name with its visual IDs.

    Description:
        This function takes a measure name and optionally includes a list of visual IDs
        where the measure is used, formatting it as a string.

    Args:
        report_path (str): The file system path to the report folder.
        measure (str): The name of the measure.
        include_visual_ids (bool): Whether to include visual IDs in the formatted string.

    Returns:
        str: The formatted measure name, optionally with visual IDs in parentheses.
    """
    visual_ids = _get_visual_ids_for_measure(report_path, measure)
    if visual_ids and include_visual_ids:
        return f"{measure} ({', '.join(visual_ids)})"
    else:
        return measure


def _trace_dependency_path(measures_dict, measure, current_path, dependency_paths):
    """
    Helper function to recursively trace the dependency path of a measure.

    Description:
        This function recursively traces the dependencies of a measure, building a list of
        dependency paths that show how other measures depend on it.

    Args:
        measures_dict (dict): A dictionary of all measures with measure names as keys and
                              expressions as values.
        measure (str): The name of the measure to trace dependencies for.
        current_path (list): The current dependency path being built.
        dependency_paths (list): A list to store all discovered dependency paths.

    Returns:
        None
    """
    direct_dependents = [
        dep for dep, exp in measures_dict.items() if f"[{measure}]" in exp
    ]

    if not direct_dependents:
        dependency_paths.append(current_path)
        return

    for dependent in direct_dependents:
        _trace_dependency_path(
            measures_dict, dependent, current_path + [dependent], dependency_paths
        )


def get_measure_dependencies(report_path, measure_names=None, include_visual_ids=False):
    """
    Gets the dependency tree for given measures or all measures in a Power BI report,
    optionally including visual IDs.

    Description:
        This function analyzes the dependencies between measures in a Power BI report.
        It can either analyze a list of specified measures or generate a report for all measures.
        Optionally, it can include the IDs of visuals that use each measure.

    Args:
        report_path (str): The file system path to the report folder.
        measure_names (list, optional): A list of measure names to analyze. If None (default) or an empty list [],
                                     analyzes all measures in the report.
        include_visual_ids (bool): If True, include a list of visual IDs where each measure is used. Default is False.

    Returns:
        str: A string representing the dependency tree(s), with each level indented.
             If include_visual_ids is True, visual IDs are added in brackets after each measure.
             If measure_names is None or an empty list, it returns a string with dependencies for all measures,
             separated by section headers.
             Returns an empty string if no measures are found or have no dependencies.
    """
    _, report_data = _load_report_extension_data(report_path)

    measures_dict = {}
    for entity in report_data.get("entities", []):
        for measure in entity.get("measures", []):
            measures_dict[measure["name"]] = measure.get("expression", "")

    if not measures_dict:
        return ""

    if not measure_names:
        # Analyze all measures
        measures_to_analyze = measures_dict.keys()
    else:
        # Analyze specified measures
        measures_to_analyze = [m for m in measure_names if m in measures_dict]

    all_dependencies_str = ""
    for measure_name in measures_to_analyze:
        dependencies = _get_dependent_measures(measure_name, measures_dict)

        if dependencies:  # Only include measures with dependencies
            all_dependencies_str += f"--- Dependencies for {measure_name} ---\n"

            dependency_paths = []
            direct_dependents = [
                dep for dep, exp in measures_dict.items() if f"[{measure_name}]" in exp
            ]

            for dependent in direct_dependents:
                _trace_dependency_path(
                    measures_dict, dependent, [dependent], dependency_paths
                )

            formatted_paths = []
            for path in dependency_paths:
                formatted_path = " > ".join(
                    _format_measure_with_visual_ids(report_path, m, include_visual_ids)
                    for m in path
                )
                formatted_paths.append(formatted_path)

            all_dependencies_str += "\n".join(formatted_paths) + "\n\n"

    return all_dependencies_str