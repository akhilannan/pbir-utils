## Fixed
- **Filters/Sanitizer**: Fixed a bug where `clear_filters` (used by the `clear_all_report_filters` sanitizer action or CLI command) would exit silently without outputting an info message when no filters matched the specified criteria.
