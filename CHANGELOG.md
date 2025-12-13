### Added
- **Set Display Option Command**: New `set-display-option` CLI command and `set_page_display_option()` Python API to set page display options in Power BI reports.
  - Supports three display options: `ActualSize`, `FitToPage`, `FitToWidth`
  - Target specific pages by `displayName` or internal `name`
  - Apply to all pages when no filter specified
  - Sanitize actions: `set_display_option_fit_to_page`, `set_display_option_fit_to_width`, `set_display_option_actual_size`
- **Clear Filters Command**: New `clear-filters` CLI command and `clear_filters()` Python API to inspect and clear filter conditions from Power BI reports.
  - Supports report, page, and visual level filters (including slicers)
  - Filter targeting with `--page`, `--visual` options
  - Field filtering with `--table`, `--column`, `--field` (supports wildcards like `Date*`, `*Amount`)
  - Dry-run mode (`--dry-run`) for inspecting filters without modifying files
  - Configurable via `pbir-sanitizer.yaml` for use in sanitization pipelines

