### Performance
- **Remove Measures**: Significantly improved performance for reports with many measures by pre-computing visual usage and dependency graphs in a single pass instead of walking the file system for each measure

### Fixed
- **Sanitize Command**: Now raises an error when `--config` path doesn't exist, instead of silently falling back to defaults
- **Visualize Command**: Fixed crash when a page has no visuals (empty legend labels) and prevented duplicate startup messages

### Removed
- **CLI**: Removed the redundant `--error-on-change` option from all commands (functionality can be achieved by checking `--dry-run` output)
