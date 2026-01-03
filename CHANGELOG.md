### Features
- **wireframe**: Major UX overhaul and enhancements
    - Added Fields Pane with comprehensive data model exploration (tables, columns, measures)
    - Added table tooltips showing field counts, visual usage, and page breakdown
    - Wireframe now opens on the active page instead of first page
    - Page changes tracked in undo stack; reset returns to original active page
    - Enhanced Field usage counts to include fields from Bookmarks, Page-level Filters, and Report-level Filters
    - Added filter toggles to show/hide visible or hidden visuals
    - Implemented universal Reset/Undo functionality
    - Visual improvements for toggle buttons and filter states
- **extract-metadata**: Added "Attribute Type" (Column/Measure) to the metadata CSV output

### Bug Fixes
- **sanitize**: Improved summary mode messaging
    - Fixed message grammar for single-report scenarios
    - Actions now show appropriate INFO messages when no changes are needed
- **extract-metadata**: Fixed duplicate rows and missing table names in metadata extraction
    - Skip redundant `queryRef`, `nativeQueryRef`, `metadata`, and `Subquery` keys
    - Prevents duplicate entries from qualified name references
    - Prevents orphan rows from filter subqueries with unresolved table aliases
