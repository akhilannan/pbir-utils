### Fixed
- **Double Message Logging**
  - Fixed issue where action headings were printed twice when a description was configured in YAML
  - Added `suppress_heading` context manager to `ConsoleUtils` to control heading output
