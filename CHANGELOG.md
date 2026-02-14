### Bug Fixes
- **sanitize**: Fixed `remove_unused_bookmarks` incorrectly removing bookmarks from Navigator visuals configured to show "All" bookmarks.
    - Now correctly identifies navigators with missing or empty `bookmarkGroup` properties as using all bookmarks.
