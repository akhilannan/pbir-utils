# PBIR Utilities

pbir-utils is a python project designed to streamline the tasks that Power BI developers typically handle manually in Power BI Desktop. This module offers a range of utility functions to efficiently manage and manipulate PBIR metadata.

## Features

- **CLI Support**: Access all utilities directly from the command line.
- **Extract Metadata**: Retrieve key metadata informations from PBIR files.
- **Update Metadata**: Apply updates to metadata within PBIR files.
- **Report Wireframe Visualizer**: Visualize PBIR report wireframe.
- **Disable Visual Interactions**: Bulk disable interactions in PBIR report.
- **Remove Measures**: Bulk remove report-level measures.
- **Get Measure Dependencies**: Extract the dependency tree for report-level measures.
- **Update Report Level Filters**: Update the filters added to the Power BI report level filter pane.
- **Sort Report Level Filters**: Reorder filters in report filter pane on a specified sorting strategy.
- **Standardize Folder Names**: Standardize page and visual folder names to be descriptive.
- **Remove Unused Bookmarks**: Remove bookmarks not used in the report.
- **Remove Unused Custom Visuals**: Remove custom visuals not used in the report.
- **Disable Show Items With No Data**: Disable "Show items with no data" property for visuals.
- **Hide Tooltip/Drillthrough Pages**: Hide pages used as tooltips or drillthroughs.
- **Configure Filter Pane**: Configure filter pane visibility and expanded state.
- **Set Page Size**: Set page dimensions for all non-tooltip pages.
- **Set First Page Active**: Set the first page of the report as the active page.
- **Sanitize Power BI Report**: Clean up and optimize Power BI reports with YAML configuration support.

## Installation
```bash
pip install pbir-utils
```

## CLI Usage

The `pbir-utils` command is available after installation.

> **Tip:** Use the `--summary` flag with any command to get concise count-based output instead of detailed messages.

### 1. Sanitize Report
Sanitize a Power BI report by removing unused or unwanted components. Runs default actions from config when no `--actions` specified.
```bash
# Run default actions from config (--actions all is optional)
pbir-utils sanitize "C:\Reports\MyReport.Report" --dry-run

# Run specific actions only
pbir-utils sanitize "C:\Reports\MyReport.Report" --actions remove_unused_measures --dry-run

# Exclude specific actions from defaults
pbir-utils sanitize "C:\Reports\MyReport.Report" --exclude set_first_page_as_active --dry-run

# Include additional actions beyond defaults
pbir-utils sanitize "C:\Reports\MyReport.Report" --include standardize_pbir_folders set_page_size --dry-run

# Concise output
pbir-utils sanitize "C:\Reports\MyReport.Report" --summary
```

#### YAML Configuration
Create a `pbir-sanitize.yaml` file to customize defaults. You only need to specify what you want to **change** - defaults are inherited:

```yaml
# pbir-sanitize.yaml - extends package defaults

# Define or override action implementations and parameters
definitions:
  set_page_size_hd:         # Custom action name
    description: Set page size to HD (1920x1080)  # Human-readable description for CLI output
    implementation: set_page_size
    params:
      width: 1920
      height: 1080
      exclude_tooltip: true

# Override default action list (replaces, does not merge)
actions:
  - cleanup_invalid_bookmarks
  - remove_unused_measures
  - set_page_size_hd          # Use our custom definition

# Or use include/exclude to modify defaults
include:
  - standardize_pbir_folders  # Add to defaults

exclude:
  - set_first_page_as_active  # Remove from defaults

options:
  summary: true               # Override default options
```

**Config Resolution Priority** (highest to lowest):
1. CLI flags (`--dry-run`, `--exclude`, etc.)
2. User config (`pbir-sanitize.yaml` in CWD or report folder)
3. Package defaults (`defaults/sanitize.yaml`)

### 2. Extract Metadata
Export attribute metadata from PBIR to CSV.
```bash
pbir-utils extract-metadata "C:\Reports\MyReport.Report" "C:\Output\metadata.csv"
```

### 3. Visualize Wireframes
Display report wireframes using Dash and Plotly.
```bash
pbir-utils visualize "C:\Reports\MyReport.Report"
pbir-utils visualize "C:\Reports\MyReport.Report" --pages "Overview" "Detail"
```

### 4. Batch Update
Batch update attributes in PBIR project using a mapping CSV.
```bash
pbir-utils batch-update "C:\PBIR\Project" "C:\Mapping.csv" --dry-run
```

### 5. Disable Interactions
Disable visual interactions between visuals.
```bash
pbir-utils disable-interactions "C:\Reports\MyReport.Report" --dry-run
pbir-utils disable-interactions "C:\Reports\MyReport.Report" --pages "Overview" --source-visual-types slicer
```

### 6. Remove Measures
Remove report-level measures.
```bash
pbir-utils remove-measures "C:\Reports\MyReport.Report" --dry-run
pbir-utils remove-measures "C:\Reports\MyReport.Report" --measure-names "Measure1" "Measure2"
```

### 7. Measure Dependencies
Generate a dependency tree for measures.
```bash
pbir-utils measure-dependencies "C:\Reports\MyReport.Report"
```

### 8. Update Filters
Update report-level filters.
```bash
pbir-utils update-filters "C:\Reports" '[{"Table": "Sales", "Column": "Region", "Condition": "In", "Values": ["North", "South"]}]' --dry-run
```

### 9. Sort Filters
Sort report-level filter pane items.
```bash
pbir-utils sort-filters "C:\Reports" --sort-order Ascending --dry-run
pbir-utils sort-filters "C:\Reports" --sort-order Custom --custom-order "Region" "Date"
```

### 10. Configure Filter Pane
Configure filter pane visibility and expanded state.
```bash
pbir-utils configure-filter-pane "C:\Reports\MyReport.Report" --dry-run
pbir-utils configure-filter-pane "C:\Reports\MyReport.Report" --visible false --dry-run
pbir-utils configure-filter-pane "C:\Reports\MyReport.Report" --expanded true --dry-run
```

> **Note:** Many individual commands have been consolidated into the `sanitize` command.
> Use `pbir-utils sanitize --actions <action_name>` for actions like:
> - `remove_unused_bookmarks`, `cleanup_invalid_bookmarks`
> - `remove_unused_custom_visuals`, `disable_show_items_with_no_data`
> - `hide_tooltip_pages`, `hide_drillthrough_pages`
> - `set_first_page_as_active`, `remove_empty_pages`
> - `standardize_pbir_folders`, `reset_filter_pane_width`

## CI/CD Integration

The `--error-on-change` flag enables automated validation in CI/CD pipelines. When used with `--dry-run`, the CLI exits with code 1 if any changes would be made, allowing builds to fail automatically when reports don't meet standards.

### Usage
```bash
# Fail if standardize_pbir_folders would make changes
pbir-utils sanitize "MyReport.Report" --actions standardize_pbir_folders --dry-run --error-on-change standardize_pbir_folders

# For sanitize: specify which actions should trigger failure
pbir-utils sanitize "MyReport.Report" --dry-run --error-on-change set_first_page_as_active remove_empty_pages
```

## Python API Usage
You can also use the library in your Python scripts:
```python
import pbir_utils as pbir

# Example: Sanitize a report
pbir.sanitize_powerbi_report("C:\\Reports\\MyReport.Report", actions=["remove_unused_measures"])
```
To get started, refer to [example_usage.ipynb](examples/example_usage.ipynb) notebook, which contains detailed examples demonstrating how to use the various functions available in pbir_utils.