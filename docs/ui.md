---
hide:
  - navigation
---

# PBIR-Utils UI

The PBIR-Utils UI visualizes Power BI reports, explores their structure, and runs cleanup actions. It launches in your default browser.

---

## Launch

Start the UI from your terminal:

```bash
# Open for the current directory
pbir-utils ui

# Open a specific report
pbir-utils ui "C:\Reports\Sales.Report"

# Use a specific port
pbir-utils ui --port 9000

# Start without opening the browser
pbir-utils ui --no-browser
```

### Options

| Option | Description |
|--------|-------------|
| `report_path` | Path to auto-open (optional; defaults to finding a `.Report` in CWD) |
| `--port` | Port to bind to (default: 8765) |
| `--host` | Host to bind to (default: 127.0.0.1) |
| `--no-browser` | Don't open the browser automatically |

---

## Browsing & Viewing

The UI provides a wireframe view of your report layout.

- **Navigation**: Use the sidebar to browse your file system and open `.Report` folders.
- **Search**: Use the main search bar in the header to filter the view. You can search by:
    - **Visuals**: Filter by unique ID or visual type (e.g., `slicer`).
    - **Pages**: Filter by display name or page ID. Entering a page ID will narrow the tab bar to only that page.
- **Canvas**: The center area shows your report visuals. Zoom in or out using the controls in the top-right.
- **Tabs**: Switch pages at the top. Right-click a tab to **Copy Page Name**, **Copy Page ID**, or **Hide Page**.
- **Dark Mode**: Toggle the 🌙 icon in the header.
- **Panes**: You can resize the sidebar and the output panel by dragging their edges.
- **Active States**: Zoom levels and theme preferences are saved to your local storage across sessions.

---

## Interacting with Visuals

Click visuals to select them. Hold `Ctrl` (or `Cmd`) to select multiple, or click and drag to draw a selection box.


Right-click any visual (or selection) to:

- **Copy ID**: Get the visual's unique ID.
- **Hide Visual**: Temporarily remove it from the wireframe.

### Hiding & Restoring

You can hide visuals or pages to declutter the view.

- **Undo**: Restores the last hidden item.
- **Reset**: Restores everything.
- **Hidden Pills**: The header shows pills like `+3 hidden` if items are hidden. Clicking a pill **unhides all** items of that type immediately.

---

## Data Model

The **Fields Pane** (right side) lists your tables, columns, and measures.

- **Search**: Find fields by name.
- **Field Usage**: Hover over a field to see where it is used (visuals, bookmarks, filters).
- **Fields Selection**: Click a field to select it (and deselect others). Hold `Ctrl` (or `Cmd`) to select multiple fields.
- **Filter by Field**: Selected fields highlight the visuals that use them.
- **Selection Controls**: A summary of selected fields appears at the top of the pane, allowing you to quickly clear the selection.

---

## Actions & Validation

### Running Actions
The **Actions** panel lists available cleanup tasks.

- **Run**: Executes the selected actions.
- **Dry Run**: Simulates the actions and prints a log of what *would* happen, without changing files.
- **Load Config**: Click the "📄" button to upload a custom `pbir-rules.yaml` or `pbir-sanitize.yaml` to override default action behaviors.

### Validation
The **Validate** panel checks your report against rules.

- **Expression Rules**: Checks logic (e.g., "Visuals must not overlap").
- **Sanitizer Checks**: If "Include sanitizer action checks" is selected, it also checks if any sanitizer actions (like "Remove unused bookmarks") would trigger changes.
- **Load Rules**: You can upload a custom `pbir-rules.yaml` here.

---

## Exporting

You can export data for external use:

- **Attributes CSV**: Metadata for visible visuals.
- **Visuals CSV**: List of visuals with IDs and types.
- **Wireframe HTML**: Generates a standalone HTML file of the current view that you can share.

## Static Wireframes

If you just need a portable file to share with colleagues, you can generate a **static wireframe**. This contains the same rich visualization but as a standalone file.

### CLI Export
You can also generate the standalone wireframe from the command line:

```bash
pbir-utils visualize "C:\Reports\Sales.Report"
```

**Options:**

- `--pages`: Filter by page name or ID.
- `--visual-types`: Filter by type (e.g., `slicer`).
- `--visual-ids`: Filter by specific IDs.
- `--no-show-hidden`: Exclude hidden visuals from the output.
