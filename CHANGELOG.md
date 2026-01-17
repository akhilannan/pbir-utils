### Features
- **sanitize**: Added `exclude_types` parameter to page display option actions
    - Allows excluding specific page types (e.g., "Tooltip") when setting display options like "Fit to Page"
    - Default configuration now excludes Tooltip pages from display option changes
- **api**: Added `failed_rules` property to `ValidationResult` for easy access to unique failed rule names as `{rule_id: rule_name}`

### Bug Fixes
- **api**:
    - Fixed `ValidationResult` to count unique failed rules by severity, not violation instances. `str(result)` now shows accurate rule-level counts (e.g., "3 warnings" = 3 rules failed, not 38 violation instances)
    - Fixed issue where sanitizer actions were running in validation stream even when excluded (e.g. via UI checkbox)