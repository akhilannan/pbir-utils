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
├── pbir-sanitize.yaml           # Shared sanitization configuration
└── requirements.txt             # Dependencies (including pbir-utils)
```

## 1. Define Sanitization Rules

First, define the rules you want to enforce in a `pbir-sanitize.yaml` file. This ensures all checks use the same standard.

You can customize the rules using `include` and `exclude` to modify the defaults, and even define custom rules.

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

## 2. Create the Validation Script

Create a Python script (e.g., `scripts/check_reports.py`) that validates each report. This script **automatically detects** whether it's running on GitHub Actions, Azure DevOps, or locally, and formats output accordingly.

The script will:

1. Iterate through all reports in your repository.
2. Run `sanitize_powerbi_report` in `dry_run` mode.
3. Log warnings or errors in the appropriate CI format.
4. Configure `BLOCKING_RULES` to specify which actions should **fail** the build. Actions not in this set will only produce warnings. Set it to `{}` (empty) if you want warnings only.

```python
"""CI/CD validation script for Power BI reports (GitHub Actions & Azure DevOps)."""
import os
import sys
from pathlib import Path
from pbir_utils import sanitize_powerbi_report

# Configuration
REPORT_PATTERN = "src/*.Report"
BLOCKING_RULES = {"remove_identifier_filters", "remove_unused_measures"}


def log_issue(message: str, is_error: bool = False) -> None:
    """Log an issue in the appropriate CI format."""
    level = "error" if is_error else "warning"
    if os.getenv("GITHUB_ACTIONS"):
        print(f"::{level}::{message}")
    elif os.getenv("TF_BUILD"):
        print(f"##vso[task.logissue type={level}]{message}")
    else:
        print(f"  [{level.upper()}] {message}")


def main() -> None:
    reports = list(Path.cwd().glob(REPORT_PATTERN))
    if not reports:
        print(f"No reports found matching '{REPORT_PATTERN}'")
        return

    print(f"Checking {len(reports)} report(s)...\n")
    has_blocking_errors = False

    for report_path in reports:
        name = report_path.name
        print(f"--- {name} ---")

        results = sanitize_powerbi_report(str(report_path), dry_run=True, summary=True)
        failed = [action for action, changed in results.items() if changed]

        if not failed:
            print("  OK")
            continue

        for action in failed:
            is_error = action in BLOCKING_RULES
            log_issue(f"[{name}] {action}", is_error=is_error)
            if is_error:
                has_blocking_errors = True

    if has_blocking_errors:
        print("\nBuild FAILED: Blocking errors found.")
        sys.exit(1)
    print("\nValidation complete.")


if __name__ == "__main__":
    main()
```

## 3. Configure Your CI Pipeline

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
2. **Validation**: The script scans all reports matching the pattern.
3. **Feedback**: Issues are logged in the native CI format (errors/warnings appear in the PR view).
4. **Result**: Build fails if any `BLOCKING_RULES` are triggered; otherwise, it passes with warnings.

## Why not auto-fix in CI?

You *could* run the sanitizer with `dry_run=False` and commit the changes back, but this is generally discouraged in CI because:

*   It modifies code without explicit developer review.
*   It can cause commit loops or merge conflicts.
*   Some sanitization actions (like removing measures) might need human judgment if defaults are too aggressive.

The recommended approach is to **warn in CI** or **fail the build in CI**, forcing the developer to run `pbir-utils sanitize` locally and commit the clean version.
