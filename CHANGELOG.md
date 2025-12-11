### Added
- **Clear Filters Command**: New `clear-filters` CLI command and `clear_filters()` Python API to inspect and clear filter conditions from Power BI reports.
  - Supports report, page, and visual level filters (including slicers)
  - Filter targeting with `--page`, `--visual` options
  - Field filtering with `--table`, `--column`, `--field` (supports wildcards like `Date*`, `*Amount`)
  - Dry-run mode (`--dry-run`) for inspecting filters without modifying files
  - Configurable via `pbir-sanitizer.yaml` for use in sanitization pipelines
