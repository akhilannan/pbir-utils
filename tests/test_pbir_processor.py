from unittest.mock import patch
import pytest

from conftest import create_dummy_file
from pbir_utils.pbir_processor import (
    _load_csv_mapping,
    _update_dax_expression,
    _update_entity,
    _update_property,
    batch_update_pbir_project,
)


def test_load_csv_mapping_invalid_columns(tmp_path):
    csv_content = "old_tbl,old_col,new_tbl\nTable,Col,NewTable"
    csv_path = create_dummy_file(tmp_path, "mapping.csv", csv_content)
    with pytest.raises(ValueError):
        _load_csv_mapping(csv_path)


def test_update_dax_expression_patterns():
    # Test quoted table
    expr = "'Old Table'[Column]"
    table_map = {"Old Table": "New Table"}
    assert _update_dax_expression(expr, table_map=table_map) == "'New Table'[Column]"

    # Test unquoted table
    expr = "OldTable[Column]"
    table_map = {"OldTable": "NewTable"}
    assert _update_dax_expression(expr, table_map=table_map) == "NewTable[Column]"

    # Test table with spaces becoming unquoted (if logic allowed, but here we test preservation/quoting)
    expr = "'Old Table'[Column]"
    table_map = {"Old Table": "NewTable"}
    assert (
        _update_dax_expression(expr, table_map=table_map) == "'NewTable'[Column]"
    )  # Code preserves quotes if present

    # Test column update
    expr = "'Table'[OldColumn]"
    column_map = {("Table", "OldColumn"): "NewColumn"}
    assert _update_dax_expression(expr, column_map=column_map) == "'Table'[NewColumn]"

    # Test column update with unquoted table
    expr = "Table[OldColumn]"
    column_map = {("Table", "OldColumn"): "NewColumn"}
    assert _update_dax_expression(expr, column_map=column_map) == "Table[NewColumn]"


def test_update_entity_nested():
    data = {
        "Entity": "OldTable",
        "nested": {"Entity": "OldTable", "entities": [{"name": "OldTable"}]},
    }
    table_map = {"OldTable": "NewTable"}
    updated = _update_entity(data, table_map)
    assert updated
    assert data["Entity"] == "NewTable"
    assert data["nested"]["Entity"] == "NewTable"
    assert data["nested"]["entities"][0]["name"] == "NewTable"


def test_update_property_nested():
    data = {
        "Column": {
            "Expression": {"SourceRef": {"Entity": "Table"}},
            "Property": "OldCol",
        },
        "nested": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": "Table"}},
                "Property": "OldCol",
            }
        },
    }
    column_map = {("Table", "OldCol"): "NewCol"}
    updated = _update_property(data, column_map)
    assert updated
    assert data["Column"]["Property"] == "NewCol"
    assert data["nested"]["Measure"]["Property"] == "NewCol"


def test_batch_update_pbir_project_exception(tmp_path):
    # Test with non-existent CSV to trigger exception handling
    with patch("builtins.print") as mock_print:
        batch_update_pbir_project(str(tmp_path), "non_existent.csv")
        mock_print.assert_called()
        assert "An error occurred" in mock_print.call_args[0][0]
