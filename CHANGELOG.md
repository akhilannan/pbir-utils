### Features
- **sanitize**: Added `exclude_types` parameter to page display option actions
    - Allows excluding specific page types (e.g., "Tooltip") when setting display options like "Fit to Page"
    - Default configuration now excludes Tooltip pages from display option changes

### Bug Fixes
- **api**: Fixed issue where sanitizer actions were running in validation stream even when excluded (e.g. via UI checkbox)