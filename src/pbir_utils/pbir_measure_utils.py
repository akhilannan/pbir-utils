import os

from .common import load_json, write_json, iter_pages, iter_visuals
from .metadata_extractor import _extract_metadata_from_file
from .console_utils import console


def _get_dependent_measures(
    measure_name: str,
    measures_dict: dict,
    visited: set = None,
    include_all_dependents: bool = False,
) -> set:
    """
    Recursively find measures that depend on the given measure.

    Args:
        measure_name (str): The name of the measure whose dependents are to be found.
        measures_dict (dict): A dictionary of all measures with their names as keys and expressions as values.
        visited (set, optional): A set to track visited measures during recursion to prevent infinite loops.
                                 Defaults to None.
        include_all_dependents (bool, optional): Whether to include indirect dependents as well.
                                                 Defaults to False.

    Returns:
        set: A set of dependent measures, either direct dependents or both direct and indirect dependents.
    """
    visited = visited or set()

    if measure_name in visited:
        return set()

    visited.add(measure_name)

    direct_dependents = {
        other_measure
        for other_measure, exp in measures_dict.items()
        if f"[{measure_name}]" in exp
    }

    if not include_all_dependents:
        return direct_dependents

    return direct_dependents.union(
        *(
            _get_dependent_measures(dependent, measures_dict, visited, True)
            for dependent in direct_dependents
        )
    )


def _get_all_measures_used_in_visuals(report_path: str) -> set:
    """
    Pre-compute all measures/columns used across all visuals in one pass.

    This function walks the report structure once and collects all measure/column
    references, enabling O(1) lookups instead of repeated file system walks.

    Args:
        report_path (str): The file system path to the report folder.

    Returns:
        set: A set of measure/column names used in visuals.
    """
    used_measures = set()
    for _, page_folder, _ in iter_pages(report_path):
        for _, visual_folder, _ in iter_visuals(page_folder):
            visual_file_path = os.path.join(visual_folder, "visual.json")
            for row in _extract_metadata_from_file(visual_file_path):
                col_or_measure = row.get("Column or Measure")
                if col_or_measure:
                    used_measures.add(col_or_measure)
                    # Handle Table.Measure format
                    if "." in col_or_measure:
                        used_measures.add(col_or_measure.split(".")[-1])
    return used_measures


def _build_dependency_graph(measures_dict: dict) -> dict:
    """
    Build a graph of measure -> set of measures that depend on it.

    This pre-computes all dependency relationships once, enabling O(1) lookups
    instead of re-scanning expressions for each measure check.

    Args:
        measures_dict (dict): A dictionary of all measures with names as keys
                              and expressions as values.

    Returns:
        dict: A dictionary mapping each measure to a set of measures that depend on it.
    """
    dependents = {m: set() for m in measures_dict}
    for measure, expression in measures_dict.items():
        for other in measures_dict:
            if f"[{other}]" in expression:
                dependents[other].add(measure)
    return dependents


def _get_all_dependents_from_graph(
    measure: str, dep_graph: dict, visited: set = None
) -> set:
    """
    Get all direct and indirect dependents using pre-built dependency graph.

    Args:
        measure (str): The measure to find dependents for.
        dep_graph (dict): Pre-built dependency graph from _build_dependency_graph.
        visited (set, optional): Set to track visited measures during recursion.

    Returns:
        set: All measures (direct and indirect) that depend on this measure.
    """
    visited = visited or set()
    if measure in visited:
        return set()
    visited.add(measure)

    direct = dep_graph.get(measure, set())
    return direct.union(
        *(_get_all_dependents_from_graph(d, dep_graph, visited) for d in direct)
    )


def _get_all_used_measures(
    measures_dict: dict, used_in_visuals: set, dep_graph: dict
) -> set:
    """
    Get all measures that are used directly or indirectly in a single pass.

    This function computes the transitive closure of measure usage:
    a measure is "used" if it's directly used in visuals, OR if any of its
    dependents are used in visuals.

    Args:
        measures_dict (dict): A dictionary of all measures with names as keys.
        used_in_visuals (set): Pre-computed set of measures used in visuals.
        dep_graph (dict): Pre-built dependency graph from _build_dependency_graph.

    Returns:
        set: All measures that are used directly or indirectly.
    """
    all_used = set()
    for measure in measures_dict:
        if measure in used_in_visuals:
            all_used.add(measure)
            continue
        # Check if any dependent is used
        all_dependents = _get_all_dependents_from_graph(measure, dep_graph)
        if any(dep in used_in_visuals for dep in all_dependents):
            all_used.add(measure)
    return all_used


def _get_visual_ids_for_measure(report_path: str, measure_name: str) -> list:
    """
    Get a list of visual IDs that use the specified measure.

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
            visual_data = load_json(visual_file_path)
            if any(
                row["Column or Measure"] == measure_name
                or (
                    row["Column or Measure"]
                    and row["Column or Measure"].endswith(f".{measure_name}")
                )
                for row in _extract_metadata_from_file(visual_file_path)
            ):
                visual_ids.append(visual_data.get("name"))
    return visual_ids


def _is_measure_used_in_visuals(report_path: str, measure_name: str) -> bool:
    """
    Check if the specified measure is used in any visual.

    Args:
        report_path (str): The file system path to the report folder.
        measure_name (str): The name of the measure to check for usage.

    Returns:
        bool: True if the measure is used in any visual within the report, False otherwise.
    """
    return bool(_get_visual_ids_for_measure(report_path, measure_name))


def _is_measure_in_cache(measure_name: str, used_measures_cache: set) -> bool:
    """
    Check if a measure is in the pre-computed cache.

    Args:
        measure_name (str): The name of the measure to check.
        used_measures_cache (set): Pre-computed set of used measures.

    Returns:
        bool: True if the measure is in the cache.
    """
    return measure_name in used_measures_cache


def _is_measure_or_dependents_used_in_visuals(
    report_path: str,
    measure_name: str,
    measures_dict: dict,
    used_measures_cache: set = None,
    dep_graph: dict = None,
) -> bool:
    """
    Check if a measure or any of its dependents are used in visuals.

    Args:
        report_path (str): The file system path to the report folder.
        measure_name (str): The name of the measure to check.
        measures_dict (dict): A dictionary of all measures with their names as keys and expressions as values.
        used_measures_cache (set, optional): Pre-computed set of measures used in visuals.
                                              If provided, uses O(1) lookups instead of file walks.
        dep_graph (dict, optional): Pre-built dependency graph from _build_dependency_graph.
                                    If provided, uses O(1) dependent lookups.

    Returns:
        bool: True if the measure or any of its dependents are used in visuals; False otherwise.
    """
    if used_measures_cache is not None:
        if _is_measure_in_cache(measure_name, used_measures_cache):
            return True
        if dep_graph is not None:
            all_dependents = _get_all_dependents_from_graph(measure_name, dep_graph)
        else:
            all_dependents = _get_dependent_measures(
                measure_name, measures_dict, include_all_dependents=True
            )
        return any(
            _is_measure_in_cache(dep, used_measures_cache) for dep in all_dependents
        )

    if _is_measure_used_in_visuals(report_path, measure_name):
        return True

    all_dependents = _get_dependent_measures(
        measure_name, measures_dict, include_all_dependents=True
    )

    return any(
        _is_measure_used_in_visuals(report_path, dependent)
        for dependent in all_dependents
    )


def _trace_dependency_path(
    measures_dict: dict, measure: str, current_path: list, dependency_paths: list
) -> None:
    """
    Recursively trace the dependency path of a measure.

    Args:
        measures_dict (dict): A dictionary of all measures with their names as keys and expressions as values.
        measure (str): The name of the measure to trace dependencies for.
        current_path (list): The current dependency path being built.
        dependency_paths (list): A list to store all discovered dependency paths.

    Returns:
        None
    """
    direct_dependents = _get_dependent_measures(measure, measures_dict)

    if not direct_dependents:
        dependency_paths.append(current_path)
        return

    for dependent in direct_dependents:
        if dependent in current_path:
            continue
        _trace_dependency_path(
            measures_dict, dependent, current_path + [dependent], dependency_paths
        )


def _format_measure_with_visual_ids(
    report_path: str, measure: str, include_visual_ids: bool
) -> str:
    """
    Format a measure name with its visual IDs.

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
    return measure


def _load_report_extension_data(report_path: str) -> tuple:
    """
    Helper function to load the Power BI report extension data.

    Args:
        report_path (str): The file system path to the report folder.

    Returns:
        tuple: A tuple containing the report file path and the loaded report extension data as a dictionary.
    """
    report_file = os.path.join(report_path, "definition", "reportExtensions.json")
    if not os.path.exists(report_file):
        return report_file, {}
    return report_file, load_json(report_file)


def generate_measure_dependencies_report(
    report_path: str, measure_names: list = None, include_visual_ids: bool = False
) -> str:
    """
    Generate a dependency report for given measures or all measures in a Power BI report,
    optionally including visual IDs.

    Args:
        report_path (str): The file system path to the report folder.
        measure_names (list, optional): A list of measure names to analyze. If None (default) or an empty list [],
                                        analyzes all measures in the report.
        include_visual_ids (bool, optional): If True, include a list of visual IDs where each measure is used.
                                             Default is False.

    Returns:
        str: A string representing the dependency report, with each measure's dependencies listed.
             If include_visual_ids is True, visual IDs are added in parentheses after each measure.
             If measure_names is None or an empty list, it returns a report with dependencies for all measures.
             Returns an empty string if no measures are found or have no dependencies.
    """
    console.print_heading("Action: Generating measure dependencies report")
    _, report_data = _load_report_extension_data(report_path)
    measures_dict = {
        measure["name"]: measure.get("expression", "")
        for entity in report_data.get("entities", [])
        for measure in entity.get("measures", [])
    }

    if not measures_dict:
        return ""

    measures_to_analyze = measure_names or measures_dict.keys()
    dependency_report = ""

    for measure_name in measures_to_analyze:
        dependency_paths = []
        direct_dependents = _get_dependent_measures(measure_name, measures_dict)

        if direct_dependents:
            dependency_report += f"--- Dependencies for {measure_name} ---\n"

            for dependent in direct_dependents:
                _trace_dependency_path(
                    measures_dict, dependent, [dependent], dependency_paths
                )

            formatted_paths = [
                " > ".join(
                    _format_measure_with_visual_ids(report_path, m, include_visual_ids)
                    for m in path
                )
                for path in dependency_paths
            ]
            dependency_report += "\n".join(formatted_paths) + "\n\n"

    if not dependency_report:
        console.print_info("No measure dependencies found in the report.")

    return dependency_report


def remove_measures(
    report_path: str,
    measure_names: list = None,
    check_visual_usage: bool = True,
    dry_run: bool = False,
    print_heading: bool = True,
    summary: bool = False,
) -> bool:
    """
    Remove specified measures or all measures from a Power BI PBIX report,
    with an optional check for their usage in visuals.

    Args:
        report_path (str): The file system path to the report folder.
        measure_names (list, optional): A list of measure names to be removed. If None or an empty list,
                                        all measures will be considered for removal. Default is None.
        check_visual_usage (bool, optional): If True, only remove a measure if neither the measure itself nor any
                                             of its dependents are used in any visuals. Default is True.
        summary (bool, optional): If True, show summary instead of detailed messages. Default is False.

    Returns:
        bool: True if changes were made (or would be made in dry run), False otherwise.
    """
    if print_heading:
        console.print_action_heading("Removing measures", dry_run)

    report_file, report_data = _load_report_extension_data(report_path)

    if not report_data:
        console.print_info("No measures found in the report.")
        return False

    removed_measures = []
    entities_to_keep = []

    used_measures_cache = None
    if check_visual_usage:
        used_measures_cache = _get_all_measures_used_in_visuals(report_path)

    for entity in report_data.get("entities", []):
        measures = entity.get("measures", [])
        measures_dict = {
            measure["name"]: measure.get("expression", "") for measure in measures
        }

        all_used_measures = None
        if check_visual_usage and used_measures_cache is not None:
            dep_graph = _build_dependency_graph(measures_dict)
            all_used_measures = _get_all_used_measures(
                measures_dict, used_measures_cache, dep_graph
            )

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
                    or (
                        all_used_measures is not None
                        and measure["name"] not in all_used_measures
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
        if not dry_run:
            write_json(report_file, report_data)
        if removed_measures:
            if dry_run:
                if summary:
                    msg = f"Would remove {len(removed_measures)} measures"
                else:
                    msg = f"Would remove measures: {', '.join(removed_measures)}"
                console.print_dry_run(msg)
            else:
                if summary:
                    msg = f"Removed {len(removed_measures)} measures"
                else:
                    msg = f"Measures removed: {', '.join(removed_measures)}"
                console.print_success(msg)
            return True
        else:
            console.print_info("No measures were removed.")
            return False
    else:
        if not dry_run:
            os.remove(report_file)
            console.print_success(
                "All measures removed. The reportExtensions.json file has been deleted."
            )
        else:
            console.print_dry_run(
                "Would remove all measures. The reportExtensions.json file would be deleted."
            )
        return True
