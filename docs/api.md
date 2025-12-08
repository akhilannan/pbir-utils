# Python API

The `pbir_utils` library provides a comprehensive Python API for programmatic access to all utilities.

```python
import pbir_utils as pbir
```

!!! tip "Runnable Examples"
    For complete, runnable examples, see the [example_usage.ipynb](https://github.com/akhilannan/pbir-utils/blob/main/examples/example_usage.ipynb) notebook.

---

## Batch Update Attributes

Performs a batch update on all components of a PBIR project by processing JSON files. Updates table and column references based on mappings provided in a CSV file.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `directory_path` | str | Path to the root directory of the PBIR project |
| `csv_path` | str | Path to the `Attribute_Mapping.csv` file |
| `dry_run` | bool | If `True`, simulate changes without modifying files. Default: `False` |

### CSV Format

The mapping CSV should have these columns:

| old_tbl | old_col | new_tbl | new_col |
|---------|---------|---------|---------|
| Sale | sale_id | Sales | Sale Id |
| Sale | order_date | Sales | OrderDate |
| Date | | Dates | |
| Product | product_name | | Product Name |

- If a table name is unchanged, `new_tbl` is optional
- If only the table name changes, `old_col` and `new_col` can be omitted

### Example

```python
pbir.batch_update_pbir_project(
    directory_path=r"C:\DEV\Power BI Report",
    csv_path=r"C:\DEV\Attribute_Mapping.csv",
    dry_run=True
)
```

---

## Export Metadata to CSV

Exports metadata from PBIR into a CSV file, including tables, columns, measures, DAX expressions, and usage contexts.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `directory_path` | str | Path to directory containing PBIR files |
| `csv_output_path` | str | Path for output CSV file |
| `filters` | dict | Dictionary to filter output data (keys are column names, values are sets of allowed values) |

### Example

```python
pbir.export_pbir_metadata_to_csv(
    directory_path=r"C:\DEV\Power BI Report",
    csv_output_path=r"C:\DEV\output.csv",
    filters={
        "Report": {},
        "Page Name": {},
        "Table": {},
        "Column or Measure": {},
    },
)
```

---

## Display Report Wireframes

Generates and displays interactive wireframes for a report using Dash and Plotly.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the PBIR report folder |
| `pages` | list | Page names to include (empty = all pages) |
| `visual_types` | list | Visual types to include (empty = all types) |
| `visual_ids` | list | Visual IDs to include (empty = all visuals) |
| `show_hidden` | bool | Show hidden visuals. Default: `True` |

!!! note "Filter Logic"
    The `pages`, `visual_types`, and `visual_ids` parameters use AND logic. Only visuals matching **all** specified criteria are shown.

### Example

```python
pbir.display_report_wireframes(
    report_path=r"C:\DEV\MyReport.Report",
    pages=["Overview"],
    visual_types=["slicer"],
    show_hidden=True
)
```

---

## Disable Visual Interactions

Disables interactions between visuals based on provided parameters.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the PBIR report folder |
| `pages` | list | Page names to process (empty = all pages) |
| `source_visual_ids` | list | Source visual IDs |
| `source_visual_types` | list | Source visual types |
| `target_visual_ids` | list | Target visual IDs |
| `target_visual_types` | list | Target visual types |
| `update_type` | str | `"Upsert"` (default), `"Insert"`, or `"Overwrite"` |
| `dry_run` | bool | Simulate changes without modifying files |

### Update Types

- **Upsert**: Disables matching interactions and inserts new combinations. Unmatched interactions remain unchanged.
- **Insert**: Adds new interactions without modifying existing ones.
- **Overwrite**: Replaces all existing interactions with the new configuration.

### Example

```python
pbir.disable_visual_interactions(
    report_path=r"C:\DEV\MyReport.Report",
    pages=["Overview"],
    source_visual_types=["slicer"],
    update_type="Upsert",
    dry_run=True
)
```

---

## Remove Measures

Removes report-level measures from a Power BI report.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the report folder |
| `measure_names` | list | Measures to remove (empty = all measures) |
| `check_visual_usage` | bool | Only remove unused measures. Default: `True` |
| `dry_run` | bool | Simulate changes without modifying files |

### Example

```python
pbir.remove_measures(
    report_path=r"C:\DEV\MyReport.Report",
    measure_names=["Unused Measure 1", "Unused Measure 2"],
    check_visual_usage=True,
    dry_run=True
)
```

---

## Generate Measure Dependencies

Generates a dependency tree for measures, focusing on measures with dependencies.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the report folder |
| `measure_names` | list | Measures to analyze (empty = all measures) |
| `include_visual_ids` | bool | Include visual IDs using the measures |

### Example

```python
result = pbir.generate_measure_dependencies_report(
    report_path=r"C:\DEV\MyReport.Report",
    measure_names=[],
    include_visual_ids=True
)
print(result)
```

---

## Update Report Filters

Updates filters in the Power BI report level filter pane.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `directory_path` | str | Root directory containing reports |
| `filters` | list | Filter configurations to apply |
| `reports` | list | Specific reports to update (optional) |
| `dry_run` | bool | Simulate changes without modifying files |

### Condition Types

| Type | Expected Values | Example |
|------|-----------------|---------|
| `GreaterThan`, `LessThan`, etc. | Single value | `{"Values": [50]}` |
| `Between`, `NotBetween` | Two values (range) | `{"Values": [10, 20]}` |
| `In`, `NotIn` | List of values | `{"Values": ["A", "B"]}` |
| `Contains`, `StartsWith`, `EndsWith` | Single string | `{"Values": ["keyword"]}` |
| `ContainsAnd`, `StartsWithOr` | Multiple strings | `{"Values": ["k1", "k2"]}` |

!!! note "Date Values"
    Date values should be formatted as `DD-MMM-YYYY`, e.g., `"15-Sep-2023"`.

!!! note "Clearing Filters"
    Set `Values` to `None` to clear an existing filter.

### Example

```python
pbir.update_report_filters(
    directory_path=r"C:\DEV\MyReport.Report",
    filters=[
        {"Table": "Sales", "Column": "Region", "Condition": "In", "Values": ["North", "South"]},
        {"Table": "Sales", "Column": "Date", "Condition": "Between", "Values": ["01-Jan-2023", "31-Dec-2023"]},
        {"Table": "Sales", "Column": "Amount", "Condition": "GreaterThan", "Values": [100]},
    ],
    dry_run=True
)
```

---

## Sort Report Filters

Reorders filters in the report filter pane based on a sorting strategy.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `directory_path` | str | Root directory containing reports |
| `reports` | list | Specific reports to update (optional) |
| `sort_order` | str | Sorting strategy (see below) |
| `custom_order` | list | Custom filter order (required for `Custom`) |
| `dry_run` | bool | Simulate changes without modifying files |

### Sorting Strategies

| Strategy | Description |
|----------|-------------|
| `Ascending` | Alphabetical order (A-Z) |
| `Descending` | Reverse alphabetical order (Z-A) |
| `SelectedFilterTop` | Selected filters first (both groups sorted ascending) |
| `Custom` | Order based on `custom_order` list |

### Example

```python
pbir.sort_report_filters(
    directory_path=r"C:\DEV\MyReport.Report",
    sort_order="SelectedFilterTop",
    dry_run=True
)
```

---

## Sanitize Power BI Report

A powerful utility to clean up and optimize Power BI reports.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the report folder |
| `actions` | list | Sanitization actions to perform |
| `dry_run` | bool | Simulate changes without modifying files |

### Available Actions

| Action | Description |
|--------|-------------|
| `remove_unused_measures` | Remove measures not used in any visuals |
| `remove_unused_bookmarks` | Remove bookmarks not activated through navigators/actions |
| `remove_unused_custom_visuals` | Remove unused custom visuals |
| `disable_show_items_with_no_data` | Disable "Show items with no data" for all visuals |
| `hide_tooltip_pages` | Hide tooltip and drillthrough pages |
| `set_first_page_as_active` | Set first page as default active page |
| `remove_empty_pages` | Remove pages without visuals |
| `remove_hidden_visuals_never_shown` | Remove permanently hidden visuals |
| `cleanup_invalid_bookmarks` | Remove bookmarks referencing non-existent pages/visuals |
| `standardize_pbir_folders` | Standardize folder names to be descriptive |

### Example

```python
pbir.sanitize_powerbi_report(
    r"C:\DEV\MyReport.Report",
    [
        "cleanup_invalid_bookmarks",
        "remove_unused_measures",
        "remove_unused_bookmarks",
        "remove_unused_custom_visuals",
        "disable_show_items_with_no_data",
        "hide_tooltip_pages",
        "set_first_page_as_active",
        "remove_empty_pages",
        "remove_hidden_visuals_never_shown",
        "standardize_pbir_folders",
    ],
    dry_run=True,
)
```

---

## Individual Sanitization Functions

You can also call specific sanitization actions independently:

```python
# Remove unused bookmarks
pbir.remove_unused_bookmarks(report_path, dry_run=True)

# Remove hidden visuals
pbir.remove_hidden_visuals_never_shown(report_path, dry_run=True)

# Set first page as active
pbir.set_first_page_as_active(report_path, dry_run=True)

# Remove empty pages
pbir.remove_empty_pages(report_path, dry_run=True)

# Cleanup invalid bookmarks
pbir.cleanup_invalid_bookmarks(report_path, dry_run=True)

# Standardize folder names
pbir.standardize_pbir_folders(report_path, dry_run=True)
```

!!! warning "Backup Your Reports"
    Always backup your report or use version control before running sanitization. Some actions are irreversible. Use `dry_run=True` to preview changes.
