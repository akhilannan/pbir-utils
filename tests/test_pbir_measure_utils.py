from unittest.mock import patch
import pytest

from pbir_utils.pbir_measure_utils import (
    _get_dependent_measures,
    _get_visual_ids_for_measure,
    _is_measure_used_in_visuals,
    _is_measure_or_dependents_used_in_visuals,
    _trace_dependency_path,
    generate_measure_dependencies_report,
    remove_measures,
)


@pytest.fixture
def measures_dict():
    return {
        "MeasureA": "SUM(Table[Col])",
        "MeasureB": "[MeasureA] * 2",
        "MeasureC": "[MeasureB] + 10",
        "MeasureD": "COUNT(Table[ID])",
    }


def test_get_dependent_measures(measures_dict):
    # MeasureA is used in MeasureB
    deps_A = _get_dependent_measures("MeasureA", measures_dict)
    assert "MeasureB" in deps_A
    assert "MeasureC" not in deps_A  # Direct only by default

    # MeasureB is used in MeasureC
    deps_B = _get_dependent_measures("MeasureB", measures_dict)
    assert "MeasureC" in deps_B

    # MeasureD has no dependents
    deps_D = _get_dependent_measures("MeasureD", measures_dict)
    assert len(deps_D) == 0

    # Recursive (all dependents)
    all_deps_A = _get_dependent_measures(
        "MeasureA", measures_dict, include_all_dependents=True
    )
    assert "MeasureB" in all_deps_A
    assert "MeasureC" in all_deps_A


@patch("pbir_utils.pbir_measure_utils.os.walk")
@patch("pbir_utils.pbir_measure_utils.load_json")
@patch("pbir_utils.pbir_measure_utils._extract_metadata_from_file")
def test_get_visual_ids_for_measure(mock_extract, mock_load, mock_walk):
    mock_walk.return_value = [("root", [], ["visual.json"])]
    mock_load.return_value = {"name": "Visual123"}

    # Case 1: Measure is used
    mock_extract.return_value = [{"Column or Measure": "MeasureA"}]
    ids = _get_visual_ids_for_measure("dummy_path", "MeasureA")
    assert ids == ["Visual123"]

    # Case 2: Measure is not used
    mock_extract.return_value = [{"Column or Measure": "OtherMeasure"}]
    ids = _get_visual_ids_for_measure("dummy_path", "MeasureA")
    assert ids == []

    # Case 3: Measure is used with qualified name (Table.Measure)
    mock_extract.return_value = [{"Column or Measure": "Table.MeasureA"}]
    ids = _get_visual_ids_for_measure("dummy_path", "MeasureA")
    assert ids == ["Visual123"]


@patch("pbir_utils.pbir_measure_utils._get_visual_ids_for_measure")
def test_is_measure_used_in_visuals(mock_get_ids):
    mock_get_ids.return_value = ["v1"]
    assert _is_measure_used_in_visuals("path", "m1")

    mock_get_ids.return_value = []
    assert not _is_measure_used_in_visuals("path", "m1")


@patch("pbir_utils.pbir_measure_utils._is_measure_used_in_visuals")
def test_is_measure_or_dependents_used_in_visuals(mock_is_used, measures_dict):
    # Case 1: Measure itself is used
    mock_is_used.side_effect = lambda p, m: m == "MeasureA"
    assert _is_measure_or_dependents_used_in_visuals("path", "MeasureA", measures_dict)

    # Case 2: Dependent is used (MeasureB uses MeasureA)
    mock_is_used.side_effect = lambda p, m: m == "MeasureB"
    assert _is_measure_or_dependents_used_in_visuals("path", "MeasureA", measures_dict)

    # Case 3: None used
    mock_is_used.side_effect = None
    mock_is_used.return_value = False
    assert not _is_measure_or_dependents_used_in_visuals(
        "path", "MeasureA", measures_dict
    )


def test_trace_dependency_path(measures_dict):
    paths = []
    _trace_dependency_path(measures_dict, "MeasureA", ["MeasureA"], paths)
    # Expected paths: A -> B -> C
    assert any(p == ["MeasureA", "MeasureB", "MeasureC"] for p in paths)


@patch("pbir_utils.pbir_measure_utils._load_report_extension_data")
@patch("pbir_utils.pbir_measure_utils._get_dependent_measures")
def test_generate_measure_dependencies_report(mock_get_deps, mock_load_data):
    mock_load_data.return_value = (
        "path",
        {"entities": [{"measures": [{"name": "M1", "expression": "exp"}]}]},
    )
    mock_get_deps.return_value = {"M2"}

    report = generate_measure_dependencies_report("path", measure_names=["M1"])
    assert "Dependencies for M1" in report


@patch("pbir_utils.pbir_measure_utils._load_report_extension_data")
@patch("pbir_utils.pbir_measure_utils.write_json")
@patch("pbir_utils.pbir_measure_utils._get_all_measures_used_in_visuals")
@patch("pbir_utils.pbir_measure_utils._build_dependency_graph")
@patch("pbir_utils.pbir_measure_utils._get_all_used_measures")
def test_remove_measures(
    mock_get_all_used, mock_build_graph, mock_get_all, mock_write, mock_load_data
):
    report_data = {
        "entities": [
            {
                "measures": [
                    {"name": "KeepMe", "expression": "exp1"},
                    {"name": "RemoveMe", "expression": "exp2"},
                ]
            }
        ]
    }
    mock_load_data.return_value = ("path/reportExtensions.json", report_data)
    mock_get_all.return_value = {
        "KeepMe"
    }  # Pre-computed cache of visually used measures
    mock_build_graph.return_value = {}  # Empty dependency graph for test
    # Phase 3: Mock batch computation - KeepMe is used, RemoveMe is not
    mock_get_all_used.return_value = {"KeepMe"}

    remove_measures("path", measure_names=None, check_visual_usage=True)

    # Check what was written back
    args, _ = mock_write.call_args
    written_data = args[1]
    measures = written_data["entities"][0]["measures"]
    assert len(measures) == 1
    assert measures[0]["name"] == "KeepMe"
