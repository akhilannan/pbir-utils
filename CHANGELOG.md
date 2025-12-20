### Performance
- **High-Impact Optimizations**:
    - **Bookmark Usage Check**: Drastically improved speed of checking for unused bookmarks by scanning visuals in a single efficient pass.
    - **Invalid Bookmark Cleanup**: Significantly faster cleanup process by pre-loading valid visual data instead of repeated file checks.
    - **Hidden Visuals Removal**: Reduced file operations by 50% by merging duplicate scanning processes.
    - **Metadata Extraction**: Exponential speedup for large reports by optimizing how metadata expressions are matched and deduplicated.

### Changed
- **CLI**: All commands now consistently support auto-detection of report path when running from inside a `.Report` folder (`batch-update` and `update-filters` were updated)

### Documentation
- **CLI Reference**
    - Added comprehensive "Available Actions" table documenting all 22 sanitization actions with descriptions
    - Added "Default" column to action table showing which actions run by default vs. opt-in with `--include`
    - Added tips for config auto-discovery and report path auto-detection
