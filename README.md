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
- **Sanitize Power BI Report**: Clean up and optimize Power BI reports.

## Installation
```bash
pip install pbir-utils
```

## CLI Usage

The `pbir-utils` command is available after installation.

### 1. Sanitize Report
Sanitize a Power BI report by removing unused or unwanted components.
```bash
pbir-utils sanitize "C:\Reports\MyReport.Report" --actions remove_unused_measures cleanup_invalid_bookmarks --dry-run
pbir-utils sanitize "C:\Reports\MyReport.Report" --actions all
```

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

## Python API Usage
You can also use the library in your Python scripts:
```python
import pbir_utils as pbir

# Example: Sanitize a report
pbir.sanitize_powerbi_report("C:\\Reports\\MyReport.Report", actions=["remove_unused_measures"])
```
To get started, refer to [example_usage.ipynb](examples/example_usage.ipynb) notebook, which contains detailed examples demonstrating how to use the various functions available in pbir_utils.