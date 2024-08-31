# PBIR Utilities

pbir-utils is a python project designed to streamline the tasks that Power BI developers typically handle manually in Power BI Desktop. This module offers a range of utility functions to efficiently manage and manipulate PBIR metadata.

## Features

- **Extract Metadata**: Retrieve key metadata informations from PBIR files.
- **Update Metadata**: Apply updates to metadata within PBIR files.
- **Report Wireframe Visualizer**: Visualize PBIR report wireframe.
- **Disable Visual Interactions**: Bulk disable interactions in PBIR report.
- **Remove Measures**: Bulk remove report-level measures.
- **Get Measure Dependencies**: Extract the dependency tree for report-level measures.

## Installation
```python
pip install pbir-utils
```

## Usage
Once installed, you can import the library as follows:
```python
import pbir_utils as pbir
```
To get started, refer to [example_usage.ipynb](examples/example_usage.ipynb) notebook, which contains detailed examples demonstrating how to use the various functions available in pbir_utils.