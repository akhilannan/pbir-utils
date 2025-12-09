### Performance
- **CLI Startup Optimization**: Reduced `--help` command time from ~10 seconds to under 1 second (~15x faster) by implementing lazy imports for heavy dependencies and deferring module loading until commands are executed.

### Fixed
- **Wireframe Visualizer Coordinate Parsing**: Fixed `TypeError` and `ValueError` in `display_report_wireframes` caused by coordinates being stored as strings or with `@@__PRESERVE_FLOAT__@@` prefixes.
