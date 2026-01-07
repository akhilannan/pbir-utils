---
hide:
  - navigation
---

# CI/CD Integration

`pbir-utils` can be integrated into your CI/CD pipeline to validate Power BI reports before deployment. This ensures all reports adhere to your team's standards and best practices.

This guide demonstrates how to set up CI/CD checks for both **GitHub Actions** and **Azure DevOps** using a single, platform-agnostic validation script.

## Repository Structure

A typical repository structure for Power BI projects using `pbir-utils` might look like this:

```text
my-powerbi-repo/
├── src/
│   ├── SalesReport.Report/      # PBIR Source Folder
│   │   ├── definition/
│   │   └── ...
│   ├── HRReport.Report/
│   └── ...
├── scripts/
│   └── check_reports.py         # The validation script (works on any CI)
├── pbir-sanitize.yaml           # Defines WHAT to clean/sanitize (the standard)
├── pbir-rules.yaml              # Defines validation strictness & extra checks
└── requirements.txt             # Dependencies (including pbir-utils)
```

## 1. Define Sanitization Standards

First, define the "cleanup" standards in `pbir-sanitize.yaml`. This file controls which actions run and allows you to customize their behavior.

```yaml
# pbir-sanitize.yaml
# By default, runs standard actions (remove_unused_measures, etc.)

# 1. Define custom rules first
definitions:
  remove_identifier_filters:
    implementation: clear_filters # Using the clear_filters function
    params:
        include_columns: ["*Id*", "* ID*"] # Pattern to match ID columns
        clear_all: true # Required to actually perform the clear
    description: "Remove filters on identifier columns (e.g. OrderId, Customer ID)"

# 2. Exclude specific default actions if needed
exclude:
  - set_first_page_as_active
  - remove_empty_pages

# 3. Include additional actions (built-in or custom defined above)
include:
  - standardize_pbir_folders 
  - remove_identifier_filters
```

> **Note:** `pbir-sanitize.yaml` is automatically discovered when placed in the repository root. If using a different name or location, pass the `config` parameter explicitly: `sanitize_powerbi_report(path, config="path/to/config.yaml", ...)`

For more details on configuration and available actions, see the [CLI Reference](cli.md#yaml-configuration).

## 2. Define Validation Rules

Next, create a `pbir-rules.yaml` to configure validation behavior. This file tells the validation engine to:

1.  **Auto-include** all your sanitization standards as validation checks.
2.  **Customize severity** levels (make specific rules hard errors).
3.  **Add extra checks** (like naming conventions) that aren't sanitization tasks.

```yaml
# pbir-rules.yaml

options:
  # Crucial: Automatically uses your pbir-sanitize.yaml actions as rules!
  include_sanitizer_defaults: true
  
  # Fail build if ANY warning occurs? (Default strict=True fails on errors only)
  fail_on_warning: false

definitions:
  # 1. Customize severity of sanitizer rules
  # (Use the action names from pbir-sanitize.yaml)
  remove_unused_measures:
    severity: error  # Unused measures is a HARD failure
  
  remove_identifier_filters:
    severity: warning # ID filters are just a warning

  # 2. Add extra expression-based rules (not related to sanitization)
  ensure_visual_title:
    description: "All visuals must have a title"
    severity: warning
    scope: visual
    expression: |
      len(visual.get("visual", {}).get("visualContainer", {}).get("title", {}).get("text", "")) > 0
```

> **Note:** `pbir-rules.yaml` is automatically discovered when placed in the repository root (parent directory of your reports).

For complete documentation on all configuration options (merge order, severity overrides, expression rules, and integration with `pbir-sanitize.yaml`), see the [Rules Configuration Reference](cli.md#rules-configuration-reference).

## 3. Create the Validation Script

Create a Python script (e.g., `scripts/check_reports.py`) that validates each report:

```python
"""CI/CD validation script for Power BI reports."""
import sys
from pathlib import Path
from pbir_utils import validate_report

REPORT_PATTERN = "**/*.Report"

def main() -> None:
    reports = list(Path.cwd().glob(REPORT_PATTERN))
    if not reports:
        print(f"No reports found matching '{REPORT_PATTERN}'")
        return

    results = []
    for report_path in reports:
        result = validate_report(str(report_path), strict=False)
        results.append((report_path.name, result))

    # Print summary and check for errors
    print("\n=== SUMMARY ===")
    has_errors = False
    for name, r in results:
        print(f"'{name}': {r}")
        has_errors = has_errors or r.has_errors
    
    sys.exit(1 if has_errors else 0)

if __name__ == "__main__":
    main()
```

The script is simple because `validate_report()` already:
- Prints detailed rule results with colors
- Shows a summary line: "Validation complete: 5 passed, 13 warning(s), 2 info"
- Returns a `ValidationResult` with `.has_errors`, `.error_count`, `.warning_count`, etc.


## 4. Configure Your CI Pipeline

### GitHub Actions

Create `.github/workflows/validate-reports.yml`:

```yaml
name: Validate Power BI Reports

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install pbir-utils
        run: pip install pbir-utils

      - name: Validate Reports
        run: python scripts/check_reports.py
```

### Azure DevOps

Create `azure-pipelines.yaml`:

```yaml
trigger:
  - main

pr:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - checkout: self
    fetchDepth: 1

  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.12'
      addToPath: true

  - script: pip install pbir-utils
    displayName: 'Install pbir-utils'

  - script: python scripts/check_reports.py
    displayName: 'Validate Power BI Reports'
```

## How it Works

1. **Pull Request**: When a developer opens a PR, the pipeline runs.
2. **Validation**: The script scans all reports and runs `validate_report`.
3. **Configuration Loading**: 
   - `validate_report` loads `pbir-rules.yaml`.
   - Sees `include_sanitizer_defaults: true`.
   - Loads your `pbir-sanitize.yaml` (with all its `include`/`exclude` customizations).
   - Combines them with your explicit rules.
4. **Result**: Build fails only if any `error` level rules are violated.

## Auto-fixing

If validation fails, the developer can simply run:

```bash
# Developer runs locally to fix issues
pbir-utils sanitize "src/SalesReport.Report"
git add .
git commit -m "Fix validation errors"
```

Because validation uses the SAME `pbir-sanitize.yaml` as the standard, running `sanitize` locally is guaranteed to fix all sanitizer-related issues. Expression rules (like `ensure_visual_title`) require manual fixing in Power BI Desktop.
