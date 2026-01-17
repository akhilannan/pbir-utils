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
├── pbir-sanitize.yaml           # (Optional) Customize sanitizer actions/severity
├── pbir-rules.yaml              # (Optional) Customize expression rules
```

!!! tip "Optional Configuration"
    Both config files are **optional**. Without them, `validate_report()` uses the [default sanitize actions](cli.md#available-actions) and [default expression rules](cli.md#expression-rules). Config files are auto-discovered when placed in the repository root or report folder.

## 1. Define Sanitization Standards (Optional)

Customize which actions run or their severity levels:

```yaml
# pbir-sanitize.yaml
# By default, runs standard actions (remove_unused_measures, etc.)

definitions:
  # Override severity for specific actions
  remove_unused_measures:
    severity: error  # Make this a hard failure in CI

  cleanup_invalid_bookmarks:
    severity: warning  # Standard warning

  # Define custom actions
  remove_identifier_filters:
    implementation: clear_filters
    params:
      include_columns: ["*Id*", "* ID*"]
      clear_all: true
    description: "Remove filters on identifier columns"
    severity: warning

# Exclude specific default actions if needed
exclude:
  - set_first_page_as_active
  - remove_empty_pages

# Include additional actions
include:
  - standardize_pbir_folders 
  - remove_identifier_filters
```

## 2. Define Expression Rules (Optional)

Add custom expression rules or customize severity:

```yaml
# pbir-rules.yaml

options:
  # Fail build if ANY warning occurs? (Default strict=True fails on errors only)
  fail_on_warning: false

definitions:
  # Override default rule severity
  reduce_visuals_on_page:
    severity: warning
    params:
      max_visuals: 15  # Stricter than default 20

  # Add custom expression-based rules
  ensure_visual_title:
    description: "All visuals must have a title"
    severity: warning
    scope: visual
    expression: |
      len(visual.get("visual", {}).get("visualContainer", {}).get("title", {}).get("text", "")) > 0
  
  require_page_description:
    description: "All pages should have descriptions"
    severity: info
    scope: page
    expression: |
      len(page.get("displayOption", {}).get("description", "")) > 0

include:
  - ensure_visual_title
  - require_page_description
```

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
        # Run all checks (sanitizer + expression rules)
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

- Runs both **sanitizer checks** (from `pbir-sanitize.yaml`) and **expression rules** (from `pbir-rules.yaml`)
- Prints detailed results with `[Sanitizer Checks]` and `[Expression Rules]` sections
- Shows a summary line: "Validation complete: 5 passed, 9 warning(s), 3 info"
- Returns a `ValidationResult` with `.has_errors`, `.error_count`, `.warning_count`, etc.

### Advanced: Cherry-Pick Specific Checks

You can also run specific checks:

```python
# Run only sanitizer checks (e.g., for faster CI on draft PRs)
result = validate_report(str(report_path), source="sanitize", strict=False)

# Run specific actions only
result = validate_report(
    str(report_path), 
    actions=["remove_unused_measures", "cleanup_invalid_bookmarks"],
    strict=False
)

# Run only expression rules
result = validate_report(str(report_path), source="rules", strict=False)
```

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

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Validate Reports
        run: uv run --with pbir-utils python scripts/check_reports.py
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

  - script: pip install uv
    displayName: 'Install uv'

  - script: uv run --with pbir-utils python scripts/check_reports.py
    displayName: 'Validate Power BI Reports'
```

## How it Works

1. **Pull Request**: When a developer opens a PR, the pipeline runs.
2. **Validation**: The script scans all reports and runs `validate_report`.
3. **Configuration Loading**: 
   - Loads `pbir-sanitize.yaml` for sanitizer checks (with action severities).
   - Loads `pbir-rules.yaml` for expression rules.
   - Runs both by default (use `source` to filter).
4. **Result**: Build fails only if any `error` level violations are found.

## Auto-fixing (Local Only)

!!! warning "Do not run sanitize in CI/CD"
    Running sanitization as an automated fix in CI/CD is not recommended because:

    - It modifies code without explicit developer review
    - It can cause commit loops or merge conflicts
    - Some actions (like removing measures) may need human judgment if defaults are too aggressive

**Recommended approach:** Run sanitization locally to fix issues flagged by CI:

```bash
# Developer runs locally to fix sanitizer issues
pbir-utils sanitize "src/SalesReport.Report"
git add .
git commit -m "Fix validation errors"
```

Because validation uses the SAME `pbir-sanitize.yaml` for checks, running `sanitize` locally is guaranteed to fix all sanitizer-related issues. Expression rules (like `ensure_visual_title`) require manual fixing in Power BI Desktop.

!!! tip "Preview before applying"
    Use `--dry-run` first to preview what changes will be made:
    ```bash
    pbir-utils sanitize "src/SalesReport.Report" --dry-run
    ```
