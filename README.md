<div align="center">
  <img src="https://raw.githubusercontent.com/akhilannan/pbir-utils/main/docs/assets/logo.svg" alt="pbir-utils logo" width="200"/>
</div>

[![PyPI version](https://img.shields.io/pypi/v/pbir-utils.svg)](https://pypi.org/project/pbir-utils/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/pbir-utils/)
[![CI](https://github.com/akhilannan/pbir-utils/actions/workflows/ci.yml/badge.svg)](https://github.com/akhilannan/pbir-utils/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**pbir-utils** is a Python library designed to streamline the tasks that Power BI developers typically handle manually in Power BI Desktop. This module offers a range of utility functions to efficiently manage and manipulate PBIR (Power BI Enhanced Report Format) metadata.

## 📚 Documentation

**[View Full Documentation →](https://akhilannan.github.io/pbir-utils/)**

- [CLI Reference](https://akhilannan.github.io/pbir-utils/cli/) - Command-line usage and examples
- [Python API](https://akhilannan.github.io/pbir-utils/api/) - Library documentation and code examples
- [CI/CD Integration](https://akhilannan.github.io/pbir-utils/ci_cd/) - Pipeline integration and validation

## 📦 Installation

```bash
# Using pip
pip install "pbir-utils[ui]"

# Using uv
uv add "pbir-utils[ui]"
```

## 🚀 Quick Start

### CLI

```bash
# Launch interactive web UI (alias: pbir-utils serve)
pbir-utils ui

# Sanitize a report (dry-run to preview changes)
pbir-utils sanitize "C:\Reports\MyReport.Report" --dry-run

# Validate a report against rules
pbir-utils validate "C:\Reports\MyReport.Report"

# Extract metadata to CSV
pbir-utils extract-metadata "C:\Reports\MyReport.Report"

# Visualize report wireframes
pbir-utils visualize "C:\Reports\MyReport.Report"
```

### Python API

```python
import pbir_utils as pbir

# Sanitize a report
pbir.sanitize_powerbi_report(r"C:\Reports\MyReport.Report", actions=["remove_unused_measures", "standardize_pbir_folders"])
```


## ✨ Features

- **💻 CLI Support**: Access all utilities directly from the command line
- **🌐 Web UI**: Interactive browser-based interface for reports and actions
- **⚙️ CI/CD Integration**: Validate reports in pipelines before deployment
- **✅ Validate Reports**: Rule-based validation with custom expressions
- **📄 Extract Metadata**: Retrieve key metadata from PBIR files
- **🖼️ Wireframe Visualizer**: Visualize PBIR report layout
- **🧼 Sanitize Reports**: Clean up and optimize reports with YAML configuration
- **⛔ Disable Interactions**: Bulk disable interactions
- **🧹 Manage Measures**: Remove unused measures, analyze dependencies
- **🔍 Filter Management**: Update and sort report-level filters
- **📂 Standardize Folder Names**: Organize page and visual folders

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.