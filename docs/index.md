---
hide:
  - navigation
---

# PBIR Utils

**pbir-utils** is a Python library designed to streamline the tasks that Power BI developers typically handle manually in Power BI Desktop. This module offers a range of utility functions to efficiently manage and manipulate PBIR (Power BI Enhanced Report Format) metadata.

## ✨ Features

### Core Utilities

- **🌐 Web UI**: Interactive browser-based interface for reports, wireframes, and actions
- **📄 Extract Metadata**: Export metadata from PBIR files to CSV
- **🖼️ Wireframe Visualizer**: Visual report layout with zoom, search, and field tracking
- **✅ Validate Report**: Rule-based validation with custom expression support
- **🧹 Sanitize Report**: Clean up and optimize reports with YAML configuration

### Report Management

- **⛔ Disable Interactions**: Bulk disable interactions between visuals
- **🧼 Remove Measures**: Remove unused report-level measures
- **🔗 Measure Dependencies**: Extract measure dependency trees
- **🔖 Remove Unused Bookmarks**: Clean up orphaned bookmarks
- **🎨 Remove Unused Visuals**: Remove unused custom visual registrations

### Filters & Pages

- **🔍 Update Filters**: Modify report-level filter conditions
- **🔢 Sort Filters**: Reorder filter pane items
- **⚙️ Configure Filter Pane**: Control pane visibility and state
- **📏 Set Page Size**: Set page dimensions for all pages
- **🙈 Hide Tooltip Pages**: Auto-hide tooltip and drillthrough pages

## 📦 Installation

```bash
# Using uv (Recommended)
uv add pbir-utils

# Using pip
pip install pbir-utils
```

For the web UI, install with optional dependencies:

```bash
# Using uv
uv add "pbir-utils[ui]"

# Using pip
pip install "pbir-utils[ui]"
```

## 🚀 Quick Start

After installation, the `pbir-utils` CLI is available:

```bash
# Launch interactive web UI
pbir-utils ui

# Sanitize a report with default actions (dry-run to preview)
pbir-utils sanitize "C:\Reports\MyReport.Report" --dry-run

# Validate against best practices
pbir-utils validate "C:\Reports\MyReport.Report"

# Extract metadata to CSV
pbir-utils extract-metadata "C:\Reports\MyReport.Report"

# Visualize report wireframes
pbir-utils visualize "C:\Reports\MyReport.Report"
```

Or use the Python API:

```python
import pbir_utils as pbir

# Validate a report
result = pbir.validate_report(r"C:\Reports\MyReport.Report", strict=False)
print(result)  # "5 passed, 0 errors, 2 warnings"

# Sanitize a report
pbir.sanitize_powerbi_report(r"C:\Reports\MyReport.Report", dry_run=True)
```

## 📚 Next Steps

- [CLI Reference](cli.md) - Detailed command-line usage
- [Python API](api.md) - Python library documentation
- [CI/CD Integration](ci_cd.md) - Pipeline integration and validation
