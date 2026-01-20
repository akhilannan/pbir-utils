### Features
- **ui**: Added "Select All" checkbox for Expression Rules in validation panel
    - Consistent with Actions panel UX pattern
    - Supports indeterminate state when some rules are selected

### Improvements
- **cli**: Validation summary separator line now dynamically matches text width
- **api**: Refactored `/validate/run` and `/validate/run/stream` endpoints to use single `validate_report` call instead of two separate calls
    - Eliminates duplicate count calculation logic