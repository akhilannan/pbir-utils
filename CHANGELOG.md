## Fixed
- **API**: Fixed an issue in `pbir-utils ui` where uploading a custom sanitizer config caused relative paths (e.g., `theme_path`) to resolve against the system's temporary directory instead of the working directory. Configs now work identically across CLI, Web UI, and CI/CD.

