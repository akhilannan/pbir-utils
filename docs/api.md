---
hide:
  - navigation
---

# Python API

The `pbir_utils` library provides a comprehensive Python API for programmatic access to all utilities.

```python
import pbir_utils as pbir
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
| `summary` | bool | Show summary instead of detailed messages. Default: `False` |

### Available Actions

Please refer to the [CLI Reference](cli.md#available-actions) for the complete list of available sanitization actions and their descriptions.

!!! tip "Additional Actions via YAML"
    More actions are available through YAML configuration, including `set_page_size_16_9`, `expand_filter_pane`, `collapse_filter_pane`, `hide_filter_pane`, `sort_filters_ascending`, `clear_all_report_filters`, and display option actions. See the [CLI Reference](cli.md#yaml-configuration) for configuration details.

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

# Set page display option
pbir.set_page_display_option(report_path, display_option="FitToPage", dry_run=True)
```

!!! warning "Backup Your Reports"
    Always backup your report or use version control before running sanitization. Some actions are irreversible. Use `dry_run=True` to preview changes.

---

## Validate Report

Validates a Power BI report against configurable checks. By default, runs both sanitizer checks and expression rules.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the report folder |
| `source` | str | Which checks to run: `"all"` (default), `"sanitize"`, or `"rules"` |
| `actions` | list | Specific sanitizer action IDs to check (from `pbir-sanitize.yaml`) |
| `rules` | list | Specific expression rule IDs to run (from `pbir-rules.yaml`) |
| `sanitize_config` | str/Path | Custom sanitize config path (default: auto-discovered) |
| `rules_config` | str/Path | Custom rules config path (default: auto-discovered) |
| `severity` | str | Minimum severity to check (`info`, `warning`, `error`) |
| `strict` | bool | Raise exception on error violations. Default: `True` |

### Returns

`ValidationResult` object with:

| Property | Type | Description |
|----------|------|-------------|
| `passed` | int | Number of checks that passed |
| `failed` | int | Number of checks that failed |
| `error_count` | int | Violations with `severity=error` |
| `warning_count` | int | Violations with `severity=warning` |
| `info_count` | int | Violations with `severity=info` |
| `has_errors` | bool | `True` if any errors exist |
| `has_warnings` | bool | `True` if any warnings exist |
| `results` | dict | Check ID → passed (bool) |
| `violations` | list | Full violation details |

### Raises

- `ValidationError`: If `strict=True` and any error violations found (or warnings if `fail_on_warning: true` in config).

### Example

```python
from pbir_utils import validate_report, ValidationError

# Run all checks (default)
result = validate_report(r"C:\Reports\MyReport.Report", strict=False)
print(result)  # "5 passed, 0 errors, 9 warnings, 3 info"

# Run only sanitizer checks
result = validate_report(
    r"C:\Reports\MyReport.Report",
    source="sanitize",
    strict=False
)

# Run only expression rules
result = validate_report(
    r"C:\Reports\MyReport.Report",
    source="rules",
    strict=False
)

# Run specific sanitizer actions only
result = validate_report(
    r"C:\Reports\MyReport.Report",
    actions=["remove_unused_measures", "cleanup_invalid_bookmarks"],
    strict=False
)

# Run specific expression rules only
result = validate_report(
    r"C:\Reports\MyReport.Report",
    rules=["reduce_pages", "reduce_visuals_on_page"],
    strict=False
)

# Filter by minimum severity
result = validate_report(
    r"C:\Reports\MyReport.Report",
    severity="warning",  # Only warning and error
    strict=False
)

# Use custom config files
result = validate_report(
    r"C:\Reports\MyReport.Report",
    sanitize_config="custom-sanitize.yaml",
    rules_config="custom-rules.yaml",
    strict=False
)

# Access counts directly
if result.has_errors:
    print("Build failed!")
print(f"Warnings: {result.warning_count}")
```

### Handling ValidationError

```python
from pbir_utils import validate_report, ValidationError

try:
    result = validate_report(r"C:\Reports\MyReport.Report", strict=True)
except ValidationError as e:
    print(f"Validation failed: {e}")
    for v in e.violations:
        print(f"  - {v['rule_id']}: {v['message']}")
```

For configuration details, see [Validate Report CLI Reference](cli.md#validate-report).


## Display Report Wireframes

Generates a static HTML wireframe of the report layout and opens it in the default web browser.

This function creates a temporary HTML file containing the wireframe visualization. The output includes rich interactive features: dark mode toggle, zoom controls (25%-200%), visual count badges, dimension tooltips, search/filter, copy ID, visual/page hiding with restoration pills, and global undo/reset.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the PBIR report folder |
| `pages` | list | Page names to include (empty = all pages) |
| `visual_types` | list | Visual types to include (empty = all types) |
| `visual_ids` | list | Visual IDs to include (empty = all visuals) |
| `show_hidden` | bool | Include hidden visuals in the output. Default: `True` |

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

## Export Metadata to CSV

Exports metadata from PBIR into a CSV file. Supports two modes: **attribute metadata** (default) and **visual metadata** (`visuals_only=True`).

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `directory_path` | str | Path to the PBIR report folder or a parent directory containing multiple reports |
| `csv_output_path` | str | Path for output CSV file. If not provided, defaults to `metadata.csv` or `visuals.csv` in the report folder |
| `filters` | dict | [Deprecated] Dictionary to filter output. Prefer using explicit parameters below. |
| `pages` | list[str] | Filter by page displayName(s) |
| `reports` | list[str] | Filter by report name(s) when processing a directory |
| `tables` | list[str] | Filter by table name(s) |
| `visual_types` | list[str] | Filter by visual type(s) (for `visuals_only=True`) |
| `visual_ids` | list[str] | Filter by visual ID(s) (for `visuals_only=True`) |
| `visuals_only` | bool | If `True`, exports visual-level metadata instead of attribute usage. Default: `False` |

### Example

```python
# Export attribute metadata with default output (metadata.csv in report folder)
pbir.export_pbir_metadata_to_csv(
    directory_path=r"C:\DEV\Power BI Report",
)

# Export with page filter
pbir.export_pbir_metadata_to_csv(
    directory_path=r"C:\DEV\Power BI Report",
    csv_output_path=r"C:\DEV\metadata.csv",
    pages=["Overview", "Detail"],
)

# Export from directory, filtering by report names
pbir.export_pbir_metadata_to_csv(
    directory_path=r"C:\DEV\Reports",
    reports=["Report1", "Report2"],
)

# Export visual metadata with visual type filter
pbir.export_pbir_metadata_to_csv(
    directory_path=r"C:\DEV\Power BI Report",
    visuals_only=True,
    visual_types=["slicer", "card"],
)
```

### Output Columns

**Attribute Metadata (default):** Report, Page Name, Page ID, Table, Column or Measure, Expression, Used In, Used In Detail, ID

**Visual Metadata (`visuals_only=True`):** Report, Page Name, Page ID, Visual Type, Visual ID, Parent Group ID, Is Hidden


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

Please refer to the [CLI Reference](cli.md#csv-format) for the required CSV format and column definitions.

### Example

```python
pbir.batch_update_pbir_project(
    directory_path=r"C:\DEV\Power BI Report",
    csv_path=r"C:\DEV\Attribute_Mapping.csv",
    dry_run=True
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
| `summary` | bool | Show summary instead of detailed messages. Default: `False` |

### Update Types

- **Upsert**: Disables matching interactions and inserts new combinations. Unmatched interactions remain unchanged.
- **Insert**: Adds new interactions without modifying existing ones.
- **Overwrite**: Replaces all existing interactions with the new configuration.

### Behavior

The function's scope depends on which parameters are provided:

1. **Only `report_path`**: Disables interactions between all visuals across all pages.

2. **`report_path` + `pages`**: Disables interactions between all visuals on the specified pages only.

3. **With `source_visual_ids` or `source_visual_types`**: Disables interactions **from** the specified source visuals to all other visuals (or specified targets) on the pages.

4. **With `target_visual_ids` or `target_visual_types`**: Disables interactions **to** the specified target visuals from all source visuals (or specified sources) on the pages.

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
| `summary` | bool | Show summary instead of detailed messages. Default: `False` |

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
| `report_path` | str | Path to .Report folder or root directory containing reports |
| `filters` | list | Filter configurations to apply |
| `reports` | list | Specific reports to update (optional) |
| `dry_run` | bool | Simulate changes without modifying files |
| `summary` | bool | Show summary instead of detailed messages. Default: `False` |

### Condition Types & Filter Values

Please refer to the [CLI Reference](cli.md#condition-types) for the full list of supported condition types and filter value formats.

### Example

```python
pbir.update_report_filters(
    report_path=r"C:\DEV\MyReport.Report",
    filters=[
        # Inclusion filter
        {"Table": "Sales", "Column": "Region", "Condition": "In", "Values": ["North", "South"]},
        # Date range filter
        {"Table": "Orders", "Column": "OrderDate", "Condition": "Between", "Values": ["01-Jan-2023", "31-Dec-2023"]},
        # Numeric comparison
        {"Table": "Sales", "Column": "Amount", "Condition": "GreaterThan", "Values": [100]},
        # Text matching
        {"Table": "Products", "Column": "Name", "Condition": "Contains", "Values": ["Pro"]},
        # Clear existing filter
        {"Table": "Sales", "Column": "Category", "Condition": "In", "Values": None},
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
| `report_path` | str | Path to .Report folder or root directory containing reports |
| `reports` | list | Specific reports to update (optional) |
| `sort_order` | str | Sorting strategy (see below) |
| `custom_order` | list | Custom filter order (required for `Custom`) |
| `dry_run` | bool | Simulate changes without modifying files |
| `summary` | bool | Show summary instead of detailed messages. Default: `False` |

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
    report_path=r"C:\DEV\MyReport.Report",
    sort_order="SelectedFilterTop",
    dry_run=True
)
```

---

## Clear Filters

Clears filter conditions from report, page, and visual levels. By default operates in dry-run mode (inspection only).

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the PBIR report folder |
| `show_page_filters` | bool | Include all page-level filters. Default: `False` |
| `show_visual_filters` | bool | Include all visual-level filters. Default: `False` |
| `target_page` | str | Target specific page by displayName or ID (optional) |
| `target_visual` | str | Target specific visual by name or type (optional) |
| `include_tables` | list | Table name patterns to match (supports wildcards) |
| `include_columns` | list | Column name patterns to match (supports wildcards) |
| `include_fields` | list | Full field references to match (e.g., `'Sales'[Amount]`) |
| `clear_all` | bool | Explicitly clear all matching filters. Default: `False` |
| `dry_run` | bool | Preview without modifying files. Default: `True` |
| `summary` | bool | Show concise count-based summary instead of detailed messages. Default: `False` |

!!! note "Slicer Support"
    The function automatically detects all slicer types including standard slicers (`slicer`), chiclet slicers (`chicletSlicer`), timeline slicers (`timelineSlicer`), and any custom slicer visuals containing "slicer" in the type name.

### Example

```python
# Inspect report-level filters (dry run)
pbir.clear_filters(
    report_path=r"C:\DEV\MyReport.Report",
    dry_run=True
)

# Clear filters on Date tables
pbir.clear_filters(
    report_path=r"C:\DEV\MyReport.Report",
    include_tables=["Date*"],
    clear_all=True,
    dry_run=False
)

# Clear page-level filters on a specific page
pbir.clear_filters(
    report_path=r"C:\DEV\MyReport.Report",
    target_page="Overview",
    clear_all=True,
    dry_run=False
)

# Clear all visual filters including slicers with summary output
pbir.clear_filters(
    report_path=r"C:\DEV\MyReport.Report",
    show_visual_filters=True,
    clear_all=True,
    dry_run=False,
    summary=True
)
```


---

## Configure Filter Pane

Configures the filter pane visibility and expanded/collapsed state at the report level.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the PBIR report folder |
| `visible` | bool | Show/hide the filter pane entirely. Default: `True` |
| `expanded` | bool | Expand/collapse the pane when visible. Default: `False` |
| `dry_run` | bool | Preview without modifying files. Default: `False` |
| `summary` | bool | Show summary instead of detailed messages. Default: `False` |

### Example

```python
# Hide the filter pane
pbir.configure_filter_pane(
    report_path=r"C:\DEV\MyReport.Report",
    visible=False,
    dry_run=True
)

# Show filter pane expanded
pbir.configure_filter_pane(
    report_path=r"C:\DEV\MyReport.Report",
    visible=True,
    expanded=True,
    dry_run=False
)

# Show filter pane collapsed (default)
pbir.configure_filter_pane(
    report_path=r"C:\DEV\MyReport.Report",
    visible=True,
    expanded=False
)
```

---

## Reset Filter Pane Width

Resets the filter pane width by removing any custom width settings from all pages, reverting to the default width.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the PBIR report folder |
| `dry_run` | bool | Preview without modifying files. Default: `False` |
| `summary` | bool | Show summary instead of detailed messages. Default: `False` |

### Example

```python
# Preview which pages have custom filter pane width
pbir.reset_filter_pane_width(
    report_path=r"C:\DEV\MyReport.Report",
    dry_run=True
)

# Reset filter pane width on all pages
pbir.reset_filter_pane_width(
    report_path=r"C:\DEV\MyReport.Report",
    dry_run=False
)
```

---

## Hide Pages by Type

Hides pages based on their type (Tooltip or Drillthrough).

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the PBIR report folder |
| `page_type` | str | Type of pages to hide (`Tooltip` or `Drillthrough`) |
| `dry_run` | bool | Preview without modifying files. Default: `False` |
| `summary` | bool | Show summary instead of detailed messages. Default: `False` |

### Example

```python
# Hide all tooltip pages
pbir.hide_pages_by_type(
    report_path=r"C:\DEV\MyReport.Report",
    page_type="Tooltip",
    dry_run=True
)

# Hide all drillthrough pages
pbir.hide_pages_by_type(
    report_path=r"C:\DEV\MyReport.Report",
    page_type="Drillthrough",
    dry_run=False
)
```

---

## Set Page Display Option

Sets the display option for pages, controlling how pages are rendered in the Power BI viewer.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the PBIR report folder |
| `display_option` | str | Display option to set (`ActualSize`, `FitToPage`, `FitToWidth`) |
| `page` | str | Page name or displayName to filter (optional, None = all pages) |
| `dry_run` | bool | Preview without modifying files. Default: `False` |
| `summary` | bool | Show summary instead of detailed messages. Default: `False` |

### Display Options

| Option | Description |
|--------|-------------|
| `ActualSize` | Pages display at their actual pixel dimensions |
| `FitToPage` | Pages scale to fit the entire page in the viewport |
| `FitToWidth` | Pages scale to fit the width of the viewport |

### Example

```python
# Set all pages to FitToPage
pbir.set_page_display_option(
    report_path=r"C:\DEV\MyReport.Report",
    display_option="FitToPage",
    dry_run=True
)

# Set a specific page by displayName
pbir.set_page_display_option(
    report_path=r"C:\DEV\MyReport.Report",
    display_option="ActualSize",
    page="Trends",
    dry_run=False
)

# Set a specific page by internal name/ID
pbir.set_page_display_option(
    report_path=r"C:\DEV\MyReport.Report",
    display_option="FitToWidth",
    page="bb40336091625ae0070a"
)
```

---

## Set Page Size

Sets the page dimensions (width and height) for pages in the report.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_path` | str | Path to the PBIR report folder |
| `width` | int | Target page width in pixels. Default: `1280` |
| `height` | int | Target page height in pixels. Default: `720` |
| `exclude_tooltip` | bool | Skip tooltip pages. Default: `True` |
| `dry_run` | bool | Preview without modifying files. Default: `False` |
| `summary` | bool | Show summary instead of detailed messages. Default: `False` |

### Example

```python
# Set all pages to 16:9 HD (1280x720)
pbir.set_page_size(
    report_path=r"C:\DEV\MyReport.Report",
    width=1280,
    height=720,
    dry_run=True
)

# Set pages to Full HD (1920x1080)
pbir.set_page_size(
    report_path=r"C:\DEV\MyReport.Report",
    width=1920,
    height=1080,
    exclude_tooltip=True,
    dry_run=False
)
```

---
