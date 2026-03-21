## Fixed
- **Themes/Sanitizer**: Fixed a bug where relative `theme_path` strings in `pbir-sanitize.yaml` resolved against the current working directory instead of the configuration file's directory when executed via the validation or Python API.
