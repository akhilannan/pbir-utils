## Added
- **Pages**: Introduced `set_page_order()` for reordering tabs and `set_active_page()` to specify default open pages.
- **Themes**: Added capabilities to apply themes with `set_theme()`. Introduced `reset_hardcoded_colors` (and the `reset-colors` CLI command) to strip hardcoded hex colors from visuals, reverting them to their theme defaults.
- **Metadata**: Enhanced `extract-metadata` to now capture DAX calculation contexts defined directly on visuals (`NativeVisualCalculation`).

## Changed
- **UI**:
  - **UI Overhaul**: Replaced structural emojis with crisp Lucide SVG icons (with secure emoji fallbacks for standalone HTML exports), refined the dark mode palette, standardized visual selection borders, and introduced sleek, modern scrollbars.
  - **Activity Bar**: Introduced a navigation rail to the left sidebar, replacing stacked accordions with a clean, dynamic sidebar that switches context (Reports, Actions, Validate, Export) and can be fully collapsed to maximize screen real estate.

