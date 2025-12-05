### Added
- **Sanitize Rearchitecture**
  - Added YAML configuration support with `defaults/sanitize.yaml` - define default actions and parameters
  - Added auto-discovery for action functions - any exported function with `(report_path, dry_run, summary)` signature is usable
  - Added `configure_filter_pane` action with `--visible` and `--expanded` parameters
  - Added `hide_tooltip_pages` action (hides only tooltip pages)
  - Added `hide_drillthrough_pages` action (hides only drillthrough pages)
  - Added `set_page_size` action with configurable `--width` and `--height`

- **New CLI Commands**
  - `configure-filter-pane` - Configure filter pane visibility and expanded state
  - `hide-tooltip-pages` - Hide tooltip pages only
  - `hide-drillthrough-pages` - Hide drillthrough pages only

- **Code Reorganization**
  - Split `pbir_report_sanitizer.py` into focused modules:
    - `bookmark_utils.py` - Bookmark-related actions
    - `page_utils.py` - Page-related actions
    - `visual_utils.py` - Visual-related actions
    - `sanitize_config.py` - Configuration loading/merging

### Changed
- `sanitize` command now loads default actions from YAML config when no `--actions` flag specified
- `--actions all` now runs only actions defined in config file (not all available actions)
- Replaced static `AVAILABLE_ACTIONS` dict with `get_available_actions()` auto-discovery