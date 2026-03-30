## Fixed
- **API**: Fixed a bug where `validate_report` (and the associated CLI validation rules) would fail to forward custom user configurations and parameters from `pbir-sanitize.yaml` (such as `theme_path` in `set_theme`), leading to `TypeError` during rule evaluation.

