# PBIR Utilities

[![PyPI version](https://badge.fury.io/py/pbir-utils.svg)](https://badge.fury.io/py/pbir-utils)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**pbir-utils** is a Python library designed to streamline the tasks that Power BI developers typically handle manually in Power BI Desktop. This module offers a range of utility functions to efficiently manage and manipulate PBIR (Power BI Enhanced Report Format) metadata.

## 📚 Documentation

**[View Full Documentation →](https://akhilannan.github.io/pbir-utils/)**

- [CLI Reference](https://akhilannan.github.io/pbir-utils/cli/) - Command-line usage and examples
- [Python API](https://akhilannan.github.io/pbir-utils/api/) - Library documentation and code examples

## Installation

```bash
pip install pbir-utils
```

## Quick Start

### CLI

```bash
# Sanitize a report (dry-run to preview changes)
pbir-utils sanitize "C:\Reports\MyReport.Report" --dry-run

# Extract metadata to CSV
pbir-utils extract-metadata "C:\Reports\MyReport.Report" "C:\Output\metadata.csv"

# Visualize report wireframes
pbir-utils visualize "C:\Reports\MyReport.Report"
```

### Python API

```python
import pbir_utils as pbir

# Sanitize a report
pbir.sanitize_powerbi_report("C:\\Reports\\MyReport.Report", actions=["remove_unused_measures"])
```

For more detailed examples, see the [example_usage.ipynb](examples/example_usage.ipynb) notebook.

## Features

- **CLI Support**: Access all utilities directly from the command line
- **Extract Metadata**: Retrieve key metadata from PBIR files
- **Report Wireframe Visualizer**: Visualize PBIR report layout
- **Sanitize Reports**: Clean up and optimize reports with YAML configuration
- **Disable Visual Interactions**: Bulk disable interactions
- **Manage Measures**: Remove unused measures, analyze dependencies
- **Filter Management**: Update and sort report-level filters
- **Standardize Folder Names**: Organize page and visual folders

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.