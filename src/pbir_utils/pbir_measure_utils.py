import os

from .json_utils import load_json, write_json
from .metadata_extractor import extract_metadata_from_file


def is_measure_used_in_visuals(
    report_path: str, entity_name: str, measure_name: str
) -> bool:
    """
    Check if the specified measure from the given entity is used in any visual within the report.

    Args:
        report_path (str): The file system path to the report folder.
        entity_name (str): The name of the entity containing the measure.
        measure_name (str): The name of the measure to check for usage.

    Returns:
        bool: True if the measure from the specified entity is used in any visual within the report, False otherwise.
    """
    for root, _, files in os.walk(report_path):
        if "visual.json" in files:
            visual_file_path = os.path.join(root, "visual.json")
            all_rows = extract_metadata_from_file(visual_file_path)

            # Check if the measure is in any of the rows with the correct entity
            for row in all_rows:
                if (
                    row["Table"] == entity_name
                    and row["Column or Measure"] == measure_name
                ):
                    return True
    return False


def remove_measures(
    report_path: str, measure_names: list = None, check_visual_usage: bool = True
) -> None:
    """
    Removes specified measures or all measures from a PowerBI PBIR report, with an optional check for their usage in visuals.

    Args:
        report_path (str): The file system path to the report folder.
        measure_names (Optional[List[str]]): A list of measure names to be removed. If None or an empty list,
                                             all measures will be considered for removal. Default is None.
        check_visual_usage (bool): If True, only remove measures not used in visuals. Default is True.

    Returns:
        None
    """
    report_file = os.path.join(report_path, "definition", "reportExtensions.json")

    # Use the load_json function to read the report file
    report_data = load_json(report_file)

    removed_measures = []
    entities_to_keep = []

    for entity in report_data.get("entities", []):
        entity_name = entity.get("name")
        measures = entity.get("measures", [])

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
                    or not is_measure_used_in_visuals(
                        report_path, entity_name, measure["name"]
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
        # Use the write_json function to write the report data
        write_json(report_file, report_data)
        print(
            f"Measures removed: {', '.join(removed_measures)}"
            if removed_measures
            else "No measures were removed."
        )
    else:
        os.remove(report_file)
        print("All measures removed. The reportExtensions.json file has been deleted.")