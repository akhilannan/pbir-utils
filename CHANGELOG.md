### Fixed
- **Float Precision Loss During Sanitization**
  - JSON round-trips now preserve high-precision floats (e.g., `268.57142857142861`) to prevent spurious git diffs
