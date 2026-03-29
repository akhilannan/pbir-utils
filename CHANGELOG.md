## Added
- **Sanitizer**: Added `remove_unused_hidden_pages` action (opt-in) to safely delete hidden pages. Pages are kept if they are the active page, or referenced by tooltips, drillthroughs, used bookmarks, or page navigation.

## Changed
- **Dependencies**: Downgraded `pyyaml` requirement to `>=6.0.2` (from `6.0.3`) to resolve installation conflicts with `ms-fabric-cli`.
