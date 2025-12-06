### Added
- **YAML-Driven Action Definitions**
  - New `definitions` section in `sanitize.yaml` for mapping action names to implementations
  - Implicit definitions: `action_name: {}` when function name matches
  - Explicit definitions: `action_name: { implementation: func_name, params: {...} }`
  - `set_page_size_16_9` preset action for 16:9 (1280x720) page sizing
  - `exclude_tooltip` parameter for `set_page_size` function

- **CLI Enhancements**
  - `--config PATH` flag to specify custom YAML config file
  - Help text dynamically generated from YAML definitions

### Changed
- `sanitize` command now uses `definitions` section to resolve action implementations
- Action parameters (like `check_visual_usage`, `page_type`) now configurable via YAML

### Removed (Breaking Changes)
The following standalone CLI commands have been consolidated into the `sanitize` command.
Use `pbir-utils sanitize --actions <action_name>` instead:

| Removed Command | Replacement |
|-----------------|-------------|
| `remove-unused-bookmarks` | `sanitize --actions remove_unused_bookmarks` |
| `cleanup-invalid-bookmarks` | `sanitize --actions cleanup_invalid_bookmarks` |
| `remove-unused-custom-visuals` | `sanitize --actions remove_unused_custom_visuals` |
| `disable-show-items-with-no-data` | `sanitize --actions disable_show_items_with_no_data` |
| `hide-tooltip-pages` | `sanitize --actions hide_tooltip_pages` |
| `hide-drillthrough-pages` | `sanitize --actions hide_drillthrough_pages` |
| `hide-tooltip-drillthrough-pages` | `sanitize --actions hide_tooltip_pages hide_drillthrough_pages` |
| `set-first-page-as-active` | `sanitize --actions set_first_page_as_active` |
| `remove-empty-pages` | `sanitize --actions remove_empty_pages` |
| `remove-hidden-visuals` | `sanitize --actions remove_hidden_visuals_never_shown` |
| `standardize-folder-names` | `sanitize --actions standardize_pbir_folders` |
| `set-page-size` | `sanitize --actions set_page_size_16_9` |
| `collapse-filter-pane` | `sanitize --actions collapse_filter_pane` |
| `reset-filter-pane-width` | `sanitize --actions reset_filter_pane_width` |

### Code Reorganization
- Deleted `commands/bookmarks.py`, `commands/visuals.py`, `commands/pages.py`, `commands/folders.py`
- Removed `collapse-filter-pane` and `reset-filter-pane-width` from `commands/filters.py`
- Updated `commands/__init__.py` to reflect module removals
