---
hide:
  - navigation
---

# CLI Reference

The `pbir-utils` command-line interface provides access to all utilities after installation.

!!! tip "Summary Mode"
    Use the `--summary` flag with any command to get concise count-based output instead of detailed messages.

## UI (Web Interface)

Launch a local web-based UI client for browsing reports, visualizing wireframes, and executing actions interactively.

!!! note "Optional Dependencies"
    UI requires additional dependencies. Install with:
    
    * **pip**: `pip install "pbir-utils[ui]"`
    * **uv**: `uv add "pbir-utils[ui]"`

```bash
# Launch UI (opens browser automatically)
# Alias: pbir-utils serve
pbir-utils ui

# Auto-open a specific report
pbir-utils ui "C:\Reports\MyReport.Report"

# From inside a .Report folder (auto-detected)
cd "C:\Reports\MyReport.Report"
pbir-utils ui

# Custom port
pbir-utils ui --port 9000

# Don't auto-open browser
pbir-utils ui --no-browser

# Custom host (for remote access)
pbir-utils ui --host 0.0.0.0 --port 8080
```

### UI Features

| Feature | Description |
|---------|-------------|
| **Report Browser** | Navigate filesystem to select `.Report` folders |
| **Wireframe Viewer** | Full wireframe visualization with zoom, filters, fields pane |
| **Action Execution** | Run sanitize actions with real-time progress streaming |
| **Validation Panel** | Run expression rules + sanitize action checks with popup summary |
| **CSV Export** | Download attribute and visual metadata as CSV (respects filters) |
| **HTML Export** | Download wireframe as standalone HTML file (respects filters) |
| **Auto-Reload** | Wireframe refreshes automatically after successful actions |

### CLI Options

| Option | Description |
|--------|-------------|
| `report_path` | Path to auto-open on launch (optional; auto-detects `.Report` from CWD) |
| `--port` | Port to bind to (default: 8765) |
| `--host` | Host to bind to (default: 127.0.0.1) |
| `--no-browser` | Don't automatically open the browser |

---
## Sanitize Report

Sanitize a Power BI report by applying best practices, standardizing configurations, and removing unused components. Runs default actions from config when no `--actions` specified.

```bash
# Run default actions from config (--actions all is optional)
pbir-utils sanitize "C:\Reports\MyReport.Report" --dry-run

# Run specific actions only
pbir-utils sanitize "C:\Reports\MyReport.Report" --actions remove_unused_measures --dry-run

# Exclude specific actions from defaults
pbir-utils sanitize "C:\Reports\MyReport.Report" --exclude set_first_page_as_active --dry-run

# Include additional actions beyond defaults
pbir-utils sanitize "C:\Reports\MyReport.Report" --include standardize_pbir_folders set_page_size --dry-run

# Concise output
pbir-utils sanitize "C:\Reports\MyReport.Report" --summary
```

### Available Actions

The following actions are available for use with `--actions`, `--include`, or `--exclude`:

!!! tip "**Default Actions**"
    Actions marked with ✓ run by default when no flags are specified. Use `--include` to add additional actions, or `--exclude` to skip default ones.

| Action | Description | Default |
|--------|-------------|:-------:|
| `cleanup_invalid_bookmarks` | Remove bookmarks referencing non-existent pages or visuals | ✓ |
| `remove_unused_bookmarks` | Remove bookmarks not used by bookmark navigators or visual link actions | ✓ |
| `remove_unused_measures` | Remove measures not used in visuals (preserves measures referenced by used measures) | ✓ |
| `remove_unused_custom_visuals` | Remove custom visual registrations not used by any visual | ✓ |
| `disable_show_items_with_no_data` | Turn off "Show items with no data" on visuals (improves performance by hiding rows/columns with blank values) | ✓ |
| `remove_hidden_visuals_never_shown` | Remove permanently hidden visuals not revealed by bookmarks (keeps hidden slicer visuals that have default values or are controlled by bookmarks) | ✓ |
| `remove_empty_pages` | Remove pages without visuals and clean up orphan folders | ✓ |
| `set_first_page_as_active` | Set the first non-hidden page as the default active page | ✓ |
| `reset_filter_pane_width` | Remove custom filter pane width from all pages | ✓ |
| `hide_tooltip_pages` | Set visibility to hidden for Tooltip pages | ✓ |
| `hide_drillthrough_pages` | Set visibility to hidden for Drillthrough pages | |
| `standardize_pbir_folders` | Rename folders to be descriptive (e.g., `Overview_abc123` for pages, `slicer_xyz789` for visuals) | |
| `set_page_size_16_9` | Set all non-tooltip pages to 1280×720 | |
| `expand_filter_pane` | Show and expand the filter pane | |
| `collapse_filter_pane` | Show but collapse the filter pane | |
| `hide_filter_pane` | Hide the filter pane entirely | |
| `sort_filters_selected_top` | Sort filters with applied conditions first, then alphabetically | |
| `sort_filters_ascending` | Sort all filters alphabetically (A-Z) | |
| `clear_all_report_filters` | Clear all report-level filter conditions | |
| `set_display_option_fit_to_page` | Set all pages to FitToPage display mode | |
| `set_display_option_fit_to_width` | Set all pages to FitToWidth display mode | |
| `set_display_option_actual_size` | Set all pages to ActualSize display mode | |

### YAML Configuration

Create a `pbir-sanitize.yaml` file to customize defaults. You only need to specify what you want to **change** - defaults are inherited.

```yaml
# pbir-sanitize.yaml - extends package defaults

# Define or override action implementations and parameters
definitions:
  # --- Custom Action Examples ---
  set_page_size_hd:         # Custom action name
    description: Set page size to HD (1920x1080)
    implementation: set_page_size
    params:
      width: 1920
      height: 1080
      exclude_tooltip: true

  clear_all_report_filters:
    description: Clear all report-level filter conditions
    implementation: clear_filters
    params:
      clear_all: true
      dry_run: false

  clear_date_filters:
    description: Clear filters on Date tables
    implementation: clear_filters
    params:
      include_tables:
        - "Date*"
      clear_all: true

  set_display_option_fit_to_page:
    description: Set all pages to FitToPage display
    implementation: set_page_display_option
    params:
      display_option: FitToPage

# Override default action list (replaces, does not merge)
# actions:
#   - cleanup_invalid_bookmarks
#   - remove_unused_measures
#   - set_page_size_hd          # Use our custom definition
#   - clear_all_report_filters  # usage of common action configuration

# Or use include/exclude to modify defaults
include:
  - standardize_pbir_folders    # part of additional actions
  - set_display_option_fit_to_page # Custom action
  - clear_date_filters        # Custom action
  - set_page_size_hd          # Custom action
  - clear_all_report_filters  # Custom action

exclude:
  - set_first_page_as_active

options:
  summary: true               # Override default options
```

!!! note "Custom Action Implementations"
    The `implementation` field can reference any function from the [Python API](api.md). This allows you to wrap any API function with custom parameters as a reusable sanitize action.

### Config Resolution Priority

Configuration is resolved in the following order (highest to lowest):

1. CLI flags (`--dry-run`, `--exclude`, etc.)
2. User config (`pbir-sanitize.yaml` in CWD or report folder)
3. Package defaults (`defaults/sanitize.yaml`)

!!! tip "Auto-Discovery"
    - **Config**: Place `pbir-sanitize.yaml` in your report folder or current directory and it will be used automatically. Use `--config path/to/config.yaml` to specify a different file.
    - **Report Path**: When running from inside a `.Report` folder, the report path argument is optional—it will be detected automatically.

> **See Also:** [YAML Configuration Basics](#yaml-configuration-basics) for common patterns like `definitions`, `include`/`exclude`, merge behavior, and config discovery.

---

## Validate Report

Validate a Power BI report against configurable checks. By default, runs **both**:

- **Sanitizer checks**: Verify that sanitize actions wouldn't make changes (from `pbir-sanitize.yaml`)
- **Expression rules**: Evaluate conditions on report structure (from `pbir-rules.yaml`)

```bash
# Validate with all checks (default)
pbir-utils validate "C:\Reports\MyReport.Report"

# Run only sanitizer checks
pbir-utils validate "C:\Reports\MyReport.Report" --source sanitize

# Run only expression rules
pbir-utils validate "C:\Reports\MyReport.Report" --source rules

# Run specific sanitizer actions only
pbir-utils validate "C:\Reports\MyReport.Report" --actions remove_unused_measures cleanup_invalid_bookmarks

# Run specific expression rules only
pbir-utils validate "C:\Reports\MyReport.Report" --rules reduce_pages reduce_visuals_on_page

# Filter by minimum severity
pbir-utils validate "C:\Reports\MyReport.Report" --severity warning

# Strict mode for CI/CD (exit code 1 on violations)
pbir-utils validate "C:\Reports\MyReport.Report" --strict

# JSON output for scripting
pbir-utils validate "C:\Reports\MyReport.Report" --format json

# Use custom config files
pbir-utils validate "C:\Reports\MyReport.Report" --sanitize-config custom-sanitize.yaml
pbir-utils validate "C:\Reports\MyReport.Report" --rules-config custom-rules.yaml
```

### Sample Output

```
Validating MyReport.Report
--------------------------

[Sanitizer Checks]
[WARNING] Remove unused measures
    └─ Would remove measures: Dummy, Dummy1
[PASS] Clean up invalid bookmarks
[WARNING] Remove unused bookmarks
    └─ Would remove bookmarks: Unused Bookmark
[INFO] Set the first non-hidden page as active
    └─ Would set 'Home' as the active page.

[Expression Rules]
[PASS] Reports with too many pages are harder to navigate
[INFO] Visuals with more data fields degrade performance
    └─ Page: Driver Info, Visual: 25956ecd7135217b00b2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Validation complete: 3 passed, 2 warning(s), 2 info
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed (or no `--strict` flag) |
| `1` | Violations found (with `--strict`) or errors when `fail_on_warning: true` |

### CLI Options

| Option | Description |
|--------|-------------|
| `--source` | Which checks to run: `all` (default), `sanitize`, or `rules` |
| `--actions` | Specific sanitizer action IDs to check (from `pbir-sanitize.yaml`) |
| `--rules` | Specific expression rule IDs to run (from `pbir-rules.yaml`) |
| `--sanitize-config` | Path to a custom sanitize config YAML file (default: auto-discovered) |
| `--rules-config` | Path to a custom rules config YAML file (default: auto-discovered) |
| `--severity` | Minimum severity to report (`info`, `warning`, `error`) |
| `--strict` | Exit with code 1 if any violations found |
| `--format` | Output format: `console` (default) or `json` |

### Sanitizer Checks

Sanitizer checks verify that sanitize actions from `pbir-sanitize.yaml` wouldn't make changes. Each action has its own severity level defined in the sanitize config.

**Default Severity Levels:**

| Actions | Default Severity |
|---------|------------------|
| `cleanup_invalid_bookmarks`, `remove_unused_bookmarks`, `remove_unused_measures`, `remove_unused_custom_visuals`, `remove_hidden_visuals_never_shown`, `remove_empty_pages` | `warning` |
| `set_first_page_as_active`, `disable_show_items_with_no_data`, `reset_filter_pane_width`, `hide_tooltip_pages`, cosmetic actions | `info` |

You can customize severity in `pbir-sanitize.yaml`:

```yaml
# pbir-sanitize.yaml
definitions:
  remove_unused_measures:
    severity: error  # Make this a hard error for CI/CD
  
  cleanup_invalid_bookmarks:
    severity: info   # Downgrade to info
```

### Expression Rules

Expression rules from `pbir-rules.yaml` evaluate conditions on report structure. Built-in rules:

| Rule | Severity | Description |
|------|----------|-------------|
| `reduce_pages` | info | Reports with more than 10 pages |
| `reduce_visuals_on_page` | info | Pages with more than 20 visuals |
| `reduce_objects_within_visuals` | info | Visuals with more than 6 data fields |
| `reduce_topn_filters` | info | Visuals with multiple TopN filters |
| `reduce_advanced_filters` | info | Visuals with multiple Advanced filters |
| `ensure_theme_colors` | info | Avoid hardcoded hex colors; use ThemeDataColor (disabled by default) |


### YAML Configuration

Create separate YAML files to customize each type of check:

**`pbir-sanitize.yaml`** - Customize sanitizer actions and severities:

```yaml
definitions:
  remove_unused_measures:
    severity: error
    
  # Custom action with custom severity
  my_filter_check:
    description: "Custom filter check"
    severity: warning
    implementation: clear_filters
    params:
      dry_run: true

# Include additional actions in validation
include:
  - standardize_pbir_folders

# Exclude actions from validation
exclude:
  - set_first_page_as_active
```

**`pbir-rules.yaml`** - Customize expression rules:

```yaml
options:
  fail_on_warning: false

definitions:
  # Override built-in rule severity
  reduce_visuals_on_page:
    severity: warning
    params:
      max_visuals: 15  # Stricter than default 20
  
  # Disable a noisy rule
  reduce_advanced_filters:
    disabled: true
  
  # Custom expression rule
  require_page_names:
    description: "All pages must have descriptive names"
    severity: warning
    scope: page
    expression: |
      not page.get("displayName", "").startswith("Page ")

include:
  - require_page_names

exclude:
  - reduce_topn_filters
```

> **See Also:** [YAML Configuration Basics](#yaml-configuration-basics) for common patterns like merge behavior, `disabled` flag, and config discovery.

### Expression Rules Reference

#### Available Scopes

| Scope | Context Variable | Description |
|-------|------------------|-------------|
| `report` | `report` | Full report context (pages, bookmarks, reportExtensions, etc.) |
| `page` | `page` | Current page object (with `visuals` array) |
| `visual` | `visual`, `page` | Current visual object and its parent page |
| `measure` | `measure`, `entity` | Current measure object and its parent entity |
| `bookmark` | `bookmark` | Current bookmark object |

#### Available Functions

**Built-in:** `len()`, `sum()`, `min()`, `max()`, `any()`, `all()`, `sorted()`, `reversed()`

**Regex:** `re_match(pattern, string)`, `re_search(pattern, string)`

**JSON Traversal Helpers:**

| Function | Description | Example |
|----------|-------------|---------|
| `get_path(obj, path, default)` | Safely navigate nested properties using dot notation | `get_path(visual, "visual.query.projections")` |
| `has_path(obj, path)` | Check if a nested path exists | `has_path(visual, "visual.objects.fill")` |
| `find_all(obj, key)` | Recursively find all values for a key (like JSONPath `$..key`) | `find_all(visual, "projections")` |

**Helper Examples:**

```yaml
definitions:
  # Use get_path to simplify deep property access
  check_visual_type:
    scope: visual
    expression: >
      get_path(visual, "visual.visualType") == "slicer"

  # Use find_all to search recursively (like JSONPath $..projections)
  count_all_projections:
    scope: visual
    params:
      max_fields: 6
    expression: >
      sum(len(p) for p in find_all(get_path(visual, "visual.query"), "projections")) <= max_fields

  # Use has_path for existence checks
  require_alt_text:
    scope: visual
    expression: >
      has_path(visual, "visual.visualContainerObjects.general")

  # Combine helpers with regex for powerful validation
  ensure_theme_colors:
    scope: visual
    expression: >
      get_path(visual, "visual.visualType") == "textbox" or 
      all(not re_search(r'#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})', str(c)) 
          for c in find_all(visual, "color"))
```

#### Writing Expression Rules

**Step 1: Explore the PBIR Structure**

Open your report's JSON files to see the exact structure and property names available:

```
MyReport.Report/
├── definition/
│   ├── report.json              # Report settings
│   ├── reportExtensions.json    # Measures
│   ├── pages/
│   │   └── {pageId}/
│   │       ├── page.json        # Page properties
│   │       └── visuals/
│   │           └── {visualId}/
│   │               └── visual.json  # Visual config
```

**Step 2: Write the Expression**

Expressions are Python code that returns `True` (pass) or `False` (violation):

```yaml
definitions:
  require_page_description:
    description: "All pages should have descriptions"
    severity: warning
    scope: page
    expression: |
      len(page.get("displayOption", {}).get("description", "")) > 0
```

**Step 3: Use Parameters for Flexibility**

```yaml
definitions:
  max_visuals_per_page:
    description: "Limit visuals per page"
    severity: warning
    scope: page
    params:
      max_visuals: 15
      excluded_types: ["shape", "textbox"]
    expression: |
      len([v for v in page.get("visuals", [])
           if get_path(v, "visual.visualType") not in excluded_types]) <= max_visuals
```

### Complete Example

```yaml
# pbir-rules.yaml
options:
  fail_on_warning: false

definitions:
  # Override severity
  reduce_visuals_on_page:
    severity: warning
    params:
      max_visuals: 10  # Stricter

  # Disable noisy rule
  reduce_advanced_filters:
    disabled: true

  # Custom rule
  require_page_names:
    description: "All pages must have descriptive names (not 'Page 1')"
    severity: warning
    scope: page
    expression: |
      not page.get("displayName", "").startswith("Page ")

include:
  - require_page_names

exclude:
  - reduce_topn_filters
```

---

## Visualize Wireframes

Generate a static HTML wireframe of the report layout. This tool creates a lightweight, portable HTML file that visualizes the position and size of visuals across pages.

The generated wireframe opens automatically in your default browser and includes rich interactive features:

**Navigation & View Controls:**

- **Fields Pane**: Sidebar to explore data model and filter visuals by data usage (Tables, Columns, Measures). Includes field usage from **Visuals**, **Bookmarks**, and **Filters** (Page-level and Report-level).
- **Page Tabs**: Switch between pages with visual count badges
- **Dark Mode**: Toggle with 🌙 button (preference saved automatically)
- **Zoom Controls**: Scale 25%-200% for large reports
- **Pro Layout**: Modern glassmorphic UI with Inter typography
- **Accurate Layering**: Visuals respect their Z-order from Power BI for correct overlapping

**Visual Interaction:**

- **Left-click**: Copy visual ID to clipboard
- **Right-click visual**: Temporarily hide visual (click `+X visuals` pill to restore)
- **Right-click tab**: Temporarily hide page (click `+X pages` pill to restore)
- **Fields Pane**: Expandable sidebar to browse and filter visuals by tables, columns, and measures. Tracks field usage across **Visuals**, **Bookmarks**, and **Filters**.
- **Universal Reset**: Clear all filters (Search, Fields, Visibility) with 🔄 button
- **Undo**: Revert last action (Filter, Selection, Hide) with ↩ button
- **Search**: Filter visuals by ID, Type, or Page Name (and Fields via the pane)

**Information Tooltips:**

- **Page Tooltip** (hover over tabs): Page size, visual count, and type breakdown
- **Visual Tooltip** (hover over visuals): Size (W×H), Position (X,Y), Parent group
- **Table Tooltip** (hover over table headers in Fields Pane): Column/measure counts, visual usage, page breakdown

!!! note "Active Page"
    The wireframe opens on the report's active page instead of the first page. Page changes are tracked for undo/reset.

```bash
# Generate wireframe for all pages
pbir-utils visualize "C:\Reports\MyReport.Report"

# Filter by specific pages
pbir-utils visualize "C:\Reports\MyReport.Report" --pages "Overview" "Detail"

# Filter by visual type
pbir-utils visualize "C:\Reports\MyReport.Report" --visual-types slicer card

# Exclude hidden visuals from generation
pbir-utils visualize "C:\Reports\MyReport.Report" --no-show-hidden
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--pages` | List of page names to include (uses AND logic with other filters) |
| `--visual-types` | List of visual types to include (e.g., `slicer`, `card`, `table`) |
| `--visual-ids` | List of specific visual IDs to include |
| `--no-show-hidden` | Exclude hidden visuals from the generated HTML (default: include them) |

!!! note "Filter Logic"
    The `--pages`, `--visual-types`, and `--visual-ids` options use AND logic—only visuals matching ALL specified criteria are shown.

---
## Extract Metadata

Extract metadata from PBIR reports to CSV. Supports two modes: **attribute metadata** (default) and **visual metadata** (`--visuals-only`).

You can specify a single `.Report` folder or a parent directory containing multiple reports. When a parent directory is provided, the tool recursively processes all reports found within it.

If no output path is specified, creates `metadata.csv` (or `visuals.csv` with `--visuals-only`) in the report folder.

### Attribute Metadata (Default)

Exports detailed information about tables, columns, measures, DAX expressions, and usage contexts.

```bash
# Creates metadata.csv in the report folder
pbir-utils extract-metadata "C:\Reports\MyReport.Report"

# With custom output path
pbir-utils extract-metadata "C:\Reports\MyReport.Report" "C:\Output\metadata.csv"

# Filter by page name(s)
pbir-utils extract-metadata "C:\Reports\MyReport.Report" --pages "Overview" "Detail"

# Filter by report name(s) when processing a directory
pbir-utils extract-metadata "C:\Reports" --reports "Report1" "Report2"
```

**Output columns:** Report, Page Name, Page ID, Table, Column or Measure, Expression, Used In, Used In Detail, ID

### Visual Metadata

Exports visual-level information including type, grouping, and hidden status.

```bash
# Creates visuals.csv in the report folder
pbir-utils extract-metadata "C:\Reports\MyReport.Report" --visuals-only

# Filter by visual type
pbir-utils extract-metadata "C:\Reports\MyReport.Report" --visuals-only --visual-types slicer card

# With custom output path
pbir-utils extract-metadata "C:\Reports\MyReport.Report" "C:\Output\visuals.csv" --visuals-only
```

**Output columns:** Report, Page Name, Page ID, Visual Type, Visual ID, Parent Group ID, Is Hidden

### CLI Options

| Option | Description |
|--------|-------------|
| `--pages` | Filter by page displayName(s) |
| `--reports` | Filter by report name(s) when processing a directory |
| `--tables` | Filter by table name(s) |
| `--visual-types` | Filter by visual type(s) (for `--visuals-only` mode) |
| `--visual-ids` | Filter by visual ID(s) (for `--visuals-only` mode) |
| `--visuals-only` | Extract visual-level metadata instead of attribute usage |
| `--filters` | [Deprecated] JSON string filter. Use explicit arguments instead. |

---
## Batch Update

Batch update attributes in PBIR project using a mapping CSV.

```bash
pbir-utils batch-update "C:\PBIR\Project" "C:\Mapping.csv" --dry-run
```

### CSV Format

The mapping CSV should have these columns:

| old_tbl | old_col | new_tbl | new_col |
|---------|---------|---------|---------|
| Sale | sale_id | Sales | Sale Id |
| Sale | order_date | Sales | OrderDate |
| Date | | Dates | |
| Product | product_name | | Product Name |

- If a table name is unchanged, `new_tbl` is optional
- If only the table name changes, `old_col` and `new_col` can be omitted

---
## Disable Interactions

Disable visual interactions between visuals. Useful for preventing slicers or other visuals from affecting specific targets.

```bash
# Disable all interactions on all pages
pbir-utils disable-interactions "C:\Reports\MyReport.Report" --dry-run

# Disable slicer interactions on specific pages
pbir-utils disable-interactions "C:\Reports\MyReport.Report" --pages "Overview" --source-visual-types slicer

# Disable interactions from specific source to target visuals
pbir-utils disable-interactions "C:\Reports\MyReport.Report" --source-visual-ids "abc123" --target-visual-types card

# Use Insert mode to add without modifying existing
pbir-utils disable-interactions "C:\Reports\MyReport.Report" --update-type Insert --dry-run
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--pages` | List of page names to process (default: all pages) |
| `--source-visual-ids` | List of source visual IDs |
| `--source-visual-types` | List of source visual types (e.g., `slicer`) |
| `--target-visual-ids` | List of target visual IDs |
| `--target-visual-types` | List of target visual types |
| `--update-type` | Update strategy: `Upsert` (default), `Insert`, or `Overwrite` |
| `--dry-run` | Preview changes without modifying files |
| `--summary` | Show count-based summary instead of detailed messages |

### Update Types

| Type | Behavior |
|------|----------|
| `Upsert` | Disables matching interactions and inserts new ones. Existing non-matching interactions remain unchanged. **(Default)** |
| `Insert` | Only inserts new interactions without modifying existing ones. |
| `Overwrite` | Replaces all existing interactions with the new configuration. |

### Behavior

The command's scope depends on which options are provided:

1. **Only report path**: Disables interactions between all visuals across all pages.
2. **With `--pages`**: Disables interactions between all visuals on the specified pages only.
3. **With `--source-visual-ids` or `--source-visual-types`**: Disables interactions **from** the specified sources to all targets.
4. **With `--target-visual-ids` or `--target-visual-types`**: Disables interactions **to** the specified targets from all sources.

---
## Remove Measures

Remove report-level measures. By default, only removes measures that are not used in any visuals (including their dependents).

```bash
# Remove all unused measures (checks visual usage)
pbir-utils remove-measures "C:\Reports\MyReport.Report" --dry-run

# Remove specific measures by name
pbir-utils remove-measures "C:\Reports\MyReport.Report" --measure-names "Measure1" "Measure2"

# Force remove without checking visual usage
pbir-utils remove-measures "C:\Reports\MyReport.Report" --measure-names "OldMeasure" --no-check-usage
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--measure-names` | List of specific measure names to remove (default: all measures) |
| `--no-check-usage` | Skip visual usage check before removing (default: checks usage) |
| `--dry-run` | Preview changes without modifying files |
| `--summary` | Show count-based summary instead of detailed messages |

---
## Measure Dependencies

Generate a dependency tree for measures, showing which measures depend on other measures.

```bash
# Show all measure dependencies
pbir-utils measure-dependencies "C:\Reports\MyReport.Report"

# Analyze specific measures
pbir-utils measure-dependencies "C:\Reports\MyReport.Report" --measure-names "Total Sales" "Profit Margin"

# Include visual IDs that use each measure
pbir-utils measure-dependencies "C:\Reports\MyReport.Report" --include-visual-ids
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--measure-names` | List of specific measure names to analyze (default: all measures) |
| `--include-visual-ids` | Include visual IDs where each measure is used in the output |

---
## Update Filters

Update report-level filters.

```bash
pbir-utils update-filters "C:\Reports" '[{"Table": "Sales", "Column": "Region", "Condition": "In", "Values": ["North", "South"]}]' --dry-run
```

### Condition Types

| Category | Conditions | Expected Values |
|----------|------------|------------------|
| **Comparison** | `GreaterThan`, `GreaterThanOrEqual`, `LessThan`, `LessThanOrEqual` | Single value |
| **Range** | `Between`, `NotBetween` | Two values (start, end) |
| **Inclusion** | `In`, `NotIn` | List of one or more values |
| **Text Matching** | `Contains`, `StartsWith`, `EndsWith`, `NotContains`, `NotStartsWith`, `NotEndsWith` | Single string |
| **Multi-Value Text** | `ContainsAnd`, `ContainsOr`, `StartsWithAnd`, `StartsWithOr`, `EndsWithAnd`, `EndsWithOr` | List of two or more strings |

### Filter Values

| Value Type | Format | Example |
|------------|--------|---------|
| **Date** | `DD-MMM-YYYY` string | `"15-Sep-2023"` |
| **Numeric** | Integer or float | `100`, `99.5` |
| **Text** | String | `"North"` |
| **Clear Filter** | `null` or `None` | Removes existing filter on the column |

---
## Sort Filters

Sort report-level filter pane items. Default sort order is `SelectedFilterTop`.

```bash
# Use default sort (SelectedFilterTop - filters with values first)
pbir-utils sort-filters "C:\Reports\MyReport.Report" --dry-run

# Sort alphabetically
pbir-utils sort-filters "C:\Reports\MyReport.Report" --sort-order Ascending --dry-run

# Custom order
pbir-utils sort-filters "C:\Reports\MyReport.Report" --sort-order Custom --custom-order "Region" "Date" "Product"
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--sort-order` | Sort strategy: `SelectedFilterTop` (default), `Ascending`, `Descending`, or `Custom` |
| `--custom-order` | List of filter names in desired order (required when using `Custom`) |
| `--reports` | List of specific reports to update (when processing a directory) |
| `--dry-run` | Preview changes without modifying files |
| `--summary` | Show count-based summary instead of detailed messages |

### Sort Order Strategies

| Strategy | Description |
|----------|-------------|
| `SelectedFilterTop` | Filters with applied conditions appear first (A-Z), followed by unselected filters (A-Z). **(Default)** |
| `Ascending` | Alphabetical order (A-Z) |
| `Descending` | Reverse alphabetical order (Z-A) |
| `Custom` | User-defined order via `--custom-order` |

---
## Configure Filter Pane

Configure filter pane visibility and expanded state.

```bash
pbir-utils configure-filter-pane "C:\Reports\MyReport.Report" --dry-run
pbir-utils configure-filter-pane "C:\Reports\MyReport.Report" --visible false --dry-run
pbir-utils configure-filter-pane "C:\Reports\MyReport.Report" --expanded true --dry-run
```

---
## Clear Filters

Inspect and clear filter conditions from Power BI reports at report, page, or visual level.

```bash
# Inspect all report-level filters (dry-run by default)
pbir-utils clear-filters "C:\Reports\MyReport.Report" --dry-run

# Clear all report-level filters (remove --dry-run to apply)
pbir-utils clear-filters "C:\Reports\MyReport.Report"

# Inspect page-level filters (all pages)
pbir-utils clear-filters "C:\Reports\MyReport.Report" --page --dry-run

# Target a specific page by name or ID
pbir-utils clear-filters "C:\Reports\MyReport.Report" --page "Overview" --dry-run

# Inspect visual-level filters including slicers
pbir-utils clear-filters "C:\Reports\MyReport.Report" --visual --dry-run

# Filter by table name (supports wildcards)
pbir-utils clear-filters "C:\Reports\MyReport.Report" --table "Date*" "Sales" --dry-run

# Filter by column name (supports wildcards)
pbir-utils clear-filters "C:\Reports\MyReport.Report" --column "Year" "*Date" --dry-run

# Filter by full field reference
pbir-utils clear-filters "C:\Reports\MyReport.Report" --field "'Sales'[Amount]" --dry-run

# Get concise summary output
pbir-utils clear-filters "C:\Reports\MyReport.Report" --page --visual --dry-run --summary
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--page [NAME]` | Target pages. If no value, includes all pages. If value given, targets specific page by displayName or ID. |
| `--visual [NAME]` | Target visuals. If no value, includes all visuals. If value given, targets specific visual by name or type. |
| `--table` | Filter by table name(s), supports wildcards (e.g., `Date*`) |
| `--column` | Filter by column name(s), supports wildcards (e.g., `*Amount`) |
| `--field` | Filter by full field reference(s), supports wildcards (e.g., `'Sales'[*]`) |
| `--dry-run` | Preview which filters would be cleared without modifying files |
| `--summary` | Show concise count-based summary instead of detailed filter list |

### Summary Output

When using `--summary`, the output shows counts instead of individual filters:

```
[DRY RUN] Would clear: 2 report filter(s), 1 page filter(s) across 1 page(s), 2 slicer filter(s) across 2 slicer(s), 10 visual filter(s) across 9 visual(s)
```

### Slicer Support

The command automatically detects all slicer types including:
- Standard slicers (`slicer`)
- Chiclet slicers (`chicletSlicer`)
- Timeline slicers (`timelineSlicer`)
- Any custom slicer visuals containing "slicer" in the type name

---
## Set Display Option

Set the display option for pages in a Power BI report. Controls how pages are rendered in the viewer.

```bash
# Set all pages to FitToWidth (dry run)
pbir-utils set-display-option "C:\Reports\MyReport.Report" --option FitToWidth --dry-run

# Set a specific page by display name
pbir-utils set-display-option "C:\Reports\MyReport.Report" --page "Trends" --option ActualSize

# Set a specific page by internal name/ID
pbir-utils set-display-option "C:\Reports\MyReport.Report" --page "bb40336091625ae0070a" --option FitToPage

# Apply to all pages with summary output
pbir-utils set-display-option "C:\Reports\MyReport.Report" --option FitToPage --summary
```

### Display Options

| Option | Description |
|--------|-------------|
| `ActualSize` | Pages display at their actual pixel dimensions |
| `FitToPage` | Pages scale to fit the entire page in the viewport |
| `FitToWidth` | Pages scale to fit the width of the viewport |

### CLI Options

| Option | Description |
|--------|-------------|
| `--page NAME` | Target specific page by displayName or internal name. If omitted, applies to all pages. |
| `--option` | **Required.** Display option to set (`ActualSize`, `FitToPage`, `FitToWidth`). |
| `--dry-run` | Preview changes without modifying files. |
| `--summary` | Show count-based summary instead of detailed messages. |

---
## YAML Configuration Basics

Both `pbir-sanitize.yaml` and `pbir-rules.yaml` share a common structure. This section covers shared features.

### Common Structure

```yaml
definitions:
  my_item:
    description: "Human-readable description"
    params:
      key: value
    disabled: true  # Skip this item by default

actions:  # or 'rules:' for validation
  - item1
  - item2

include:
  - additional_item  # Add to default list

exclude:
  - unwanted_item    # Remove from list

options:
  dry_run: false
```

### Merge Behavior

| Section | Behavior |
|---------|----------|
| `definitions` | **Deep merge**: User params merge with default params |
| `actions`/`rules` | **Replace**: Completely replaces default list |
| `include` | **Append**: Added to list |
| `exclude` | **Remove**: Removed from final list |
| `options` | **Override**: User options override defaults |

### Params Deep Merge

Params are **merged**, not replaced:

```yaml
# Default: my_action has params {a: 1, b: 2}
definitions:
  my_action:
    params:
      a: 10  # Override 'a' only
# Result: params = {a: 10, b: 2}
```

### Disabled Items

```yaml
definitions:
  noisy_action:
    disabled: true   # Won't run by default

include:
  - noisy_action     # Overrides disabled: true
```

### Config Discovery

1. **Current working directory** (checked first)
2. **Report folder** (if `report_path` provided)

Use `--config path/to/file.yaml` to specify explicitly.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `PBIR_UTILS_NO_UPDATE_CHECK` | Set to `1`, `true`, or `yes` to disable the automatic version update check on CLI startup. |
