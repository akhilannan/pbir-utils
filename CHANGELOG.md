### Features
- **wireframe**: Major UX overhaul and enhancements
    - Added Fields Pane with comprehensive data model exploration (tables, columns, measures)
    - Unified attribute extraction logic using `traverse_pbir_json` for consistent field detection
    - Enhanced Field usage counts to include fields from Bookmarks, Page-level Filters, and Report-level Filters
    - Improved support for identifying Measures within various PBIR JSON structures
    - Added filter toggles to show/hide visible or hidden visuals
    - Implemented universal Reset/Undo functionality
    - Visual improvements for toggle buttons and filter states

### Bug Fixes
- **sanitize**: Improved summary mode messaging
    - Fixed grammar for single-report scenarios
    - Actions now show appropriate INFO messages when no changes are needed
