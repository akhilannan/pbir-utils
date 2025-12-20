# CLI Reference

The `pbir-utils` command-line interface provides access to all utilities after installation.

!!! tip "Summary Mode"
    Use the `--summary` flag with any command to get concise count-based output instead of detailed messages.

## Sanitize Report

Sanitize a Power BI report by removing unused or unwanted components. Runs default actions from config when no `--actions` specified.

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

!!! tip "Default Actions"
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

Create a `pbir-sanitize.yaml` file to customize defaults. You only need to specify what you want to **change** - defaults are inherited:

```yaml
# pbir-sanitize.yaml - extends package defaults

# Define or override action implementations and parameters
definitions:
  set_page_size_hd:         # Custom action name
    description: Set page size to HD (1920x1080)  # Human-readable description for CLI output
    implementation: set_page_size
    params:
      width: 1920
      height: 1080
      exclude_tooltip: true

# Override default action list (replaces, does not merge)
actions:
  - cleanup_invalid_bookmarks
  - remove_unused_measures
  - set_page_size_hd          # Use our custom definition

# Or use include/exclude to modify defaults
include:
  - standardize_pbir_folders  # Add to defaults

exclude:
  - set_first_page_as_active  # Remove from defaults

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

---

## Extract Metadata

Export attribute metadata from PBIR to CSV. Extracts detailed information about tables, columns, measures, DAX expressions, and usage contexts.

```bash
# Basic extraction
pbir-utils extract-metadata "C:\Reports\MyReport.Report" "C:\Output\metadata.csv"

# Filter by page name
pbir-utils extract-metadata "C:\Reports\MyReport.Report" "C:\Output\metadata.csv" --filters '{"Page Name": ["Overview"]}'
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--filters` | JSON string to filter results (e.g., `'{"Page Name": ["Page1", "Page2"]}'`) |

---

## Visualize Wireframes

Display report wireframes using Dash and Plotly. Visualizes the layout of pages and their visual components in an interactive web interface.

```bash
# Visualize all pages
pbir-utils visualize "C:\Reports\MyReport.Report"

# Filter by specific pages
pbir-utils visualize "C:\Reports\MyReport.Report" --pages "Overview" "Detail"

# Filter by visual type
pbir-utils visualize "C:\Reports\MyReport.Report" --visual-types slicer card

# Hide hidden visuals
pbir-utils visualize "C:\Reports\MyReport.Report" --no-show-hidden
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--pages` | List of page names to include (uses AND logic with other filters) |
| `--visual-types` | List of visual types to include (e.g., `slicer`, `card`, `table`) |
| `--visual-ids` | List of specific visual IDs to include |
| `--no-show-hidden` | Hide hidden visuals (default: show them) |

!!! note "Filter Logic"
    The `--pages`, `--visual-types`, and `--visual-ids` options use AND logic—only visuals matching ALL specified criteria are shown.

---

## Batch Update

Batch update attributes in PBIR project using a mapping CSV.

```bash
pbir-utils batch-update "C:\PBIR\Project" "C:\Mapping.csv" --dry-run
```

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

### YAML Configuration

Use `clear_filters` in your `pbir-sanitizer.yaml` to include it in sanitization pipelines:

```yaml
definitions:
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

  clear_page_filters:
    description: Clear all page-level filters
    implementation: clear_filters
    params:
      show_page_filters: true
      clear_all: true

actions:
  - clear_all_report_filters  # Add to your action list
```

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

### YAML Configuration

Use display option actions in your `pbir-sanitize.yaml`:

```yaml
definitions:
  # These are already defined in package defaults
  set_display_option_fit_to_page:
    description: Set all pages to FitToPage display
    implementation: set_page_display_option
    params:
      display_option: FitToPage

  set_display_option_fit_to_width:
    description: Set all pages to FitToWidth display
    implementation: set_page_display_option
    params:
      display_option: FitToWidth

  set_display_option_actual_size:
    description: Set all pages to ActualSize display
    implementation: set_page_display_option
    params:
      display_option: ActualSize

actions:
  - set_display_option_fit_to_page  # Add to your sanitization pipeline
```


