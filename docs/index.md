---
hide:
  - navigation
---

# PBIR Utils

**pbir-utils** is a Python library designed to streamline the tasks that Power BI developers typically handle manually in Power BI Desktop. This module offers a range of utility functions to efficiently manage and manipulate PBIR (Power BI Enhanced Report Format) metadata.

## ✨ Features

- **💻 CLI Support**: Access all utilities directly from the command line.
- **📄 Extract Metadata**: Retrieve key metadata information from PBIR files.
- **✏️ Update Metadata**: Apply updates to metadata within PBIR files.
- **🖼️ Wireframe Visualizer**: Visualize PBIR report wireframe.
- **⛔ Disable Interactions**: Bulk disable interactions in PBIR report.
- **🧹 Remove Measures**: Bulk remove report-level measures.
- **🔗 Measure Dependencies**: Extract the dependency tree for report-level measures.
- **🔍 Update Filters**: Update the filters added to the Power BI report level filter pane.
- **🔢 Sort Filters**: Reorder filters in report filter pane on a specified sorting strategy.
- **📂 Standardize Folders**: Standardize page and visual folder names to be descriptive.
- **🔖 Remove Unused Bookmarks**: Remove bookmarks not used in the report.
- **🎨 Remove Unused Visuals**: Remove custom visuals not used in the report.
- **👁️‍🗨️ Disable "No Data"**: Disable "Show items with no data" property for visuals.
- **🙈 Hide Tooltip Pages**: Hide pages used as tooltips or drillthroughs.
- **⚙️ Configure Filter Pane**: Configure filter pane visibility and expanded state.
- **📏 Set Page Size**: Set page dimensions for all non-tooltip pages.
- **▶️ Set First Page Active**: Set the first page of the report as the active page.
- **🧼 Sanitize Report**: Clean up and optimize Power BI reports with YAML configuration support.

## 📦 Installation

```bash
pip install pbir-utils
```

## 🚀 Quick Start

After installation, the `pbir-utils` CLI is available:

```bash
# Sanitize a report with default actions (dry-run to preview changes)
pbir-utils sanitize "C:\Reports\MyReport.Report" --dry-run

# Extract metadata to CSV
pbir-utils extract-metadata "C:\Reports\MyReport.Report" "C:\Output\metadata.csv"

# Visualize report wireframes
pbir-utils visualize "C:\Reports\MyReport.Report"
```

Or use the Python API:

```python
import pbir_utils as pbir

# Sanitize a report
pbir.sanitize_powerbi_report("C:\\Reports\\MyReport.Report", actions=["remove_unused_measures"])
```


## 📚 Next Steps

- [CLI Reference](cli.md) - Detailed command-line usage
- [Python API](api.md) - Python library documentation
- [CI/CD Integration](ci_cd.md) - Pipeline integration and validation
