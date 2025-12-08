### Fixed
- **Missing Log for Hide Pages Action**: `hide_pages_by_type` now prints an info message when no pages of the specified type are found.

### Changed
- **Refactor**: Removed redundant wrapper functions `hide_tooltip_pages`, `hide_drillthrough_pages`, and `hide_tooltip_drillthrough_pages`. Use `hide_pages_by_type` directly or via YAML configuration.
