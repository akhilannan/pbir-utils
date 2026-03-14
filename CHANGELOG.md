## Added
- **Sanitizer / CLI**: The `set_theme` action is now content-aware. It compares the JSON of the `--theme-file` with the report's existing custom theme, skipping application if the content is identical. This allows you to safely orchestrate theme enforcement across multiple reports. You can also specify a relative `theme_path` in `pbir-sanitize.yaml`, which resolves relative to the config file's directory.

## Fixed
- **Sanitizer**: Fixed a bug where `cleanup_invalid_bookmarks` would silently delete all bookmarks if you ran the folder standardization tool first. 
