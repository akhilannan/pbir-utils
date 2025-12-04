### Added
- New `--summary` flag for all CLI commands to show concise count-based output instead of detailed messages.
- New `--error-on-change` flag for CI/CD integration: exits with code 1 if changes would be made during dry run.
  - For `sanitize` command: accepts a list of specific actions to monitor (e.g., `--error-on-change set_first_page_as_active remove_empty_pages`).
  - For all other commands: acts as a boolean flag to error if any changes would occur.
  - Requires `--dry-run` to be specified.

### Changed
- Enhanced CLI output with colors and better formatting using ANSI escape codes.
- Improved dry run output with distinct `[DRY RUN]` labeling.
- Reduced noise in "Hidden Visuals" removal output.
- Introduced `console_utils` for centralized output management.
- All modification functions now return boolean values indicating if changes were made (or would be made in dry run).

