### Added
- **Visual Metadata Extraction**
    - Added `--visuals-only` flag to `extract-metadata` command for visual-level metadata export
    - Exports Visual Type, Visual ID, Parent Group ID, and Is Hidden status
    - Made output path optional - defaults to `metadata.csv` or `visuals.csv` in the report folder

### Documentation
- **CI/CD Guide**
    - Added GitHub Actions workflow example alongside Azure DevOps
    - Made validation script platform-agnostic (auto-detects CI environment)
- **Examples Cleanup**
    - Removed deprecated `examples/example_usage.ipynb` notebook as all examples are fully covered in the official documentation
    - Cleansed references to the notebook from `README.md` and documentation files
