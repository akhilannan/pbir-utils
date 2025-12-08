import os
import json
from pbir_utils.metadata_extractor import (
    _consolidate_metadata_from_directory,
    export_pbir_metadata_to_csv,
)
from pbir_utils.pbir_report_sanitizer import sanitize_powerbi_report
from pbir_utils.pbir_processor import batch_update_pbir_project


def test_metadata_extraction(complex_report):
    print(f"\nTesting Metadata Extraction on: {complex_report}")
    metadata = _consolidate_metadata_from_directory(complex_report)

    print(f"Metadata rows found: {len(metadata)}")
    assert len(metadata) > 0, "No metadata extracted"

    # Check for expected fields
    first_row = metadata[0]
    expected_fields = [
        "Report",
        "Page Name",
        "Page ID",
        "Table",
        "Column or Measure",
        "Expression",
        "Used In",
        "Used In Detail",
        "ID",
    ]
    for field in expected_fields:
        assert field in first_row


def test_export_pbir_metadata_to_csv(complex_report, tmp_path):
    print(f"\nTesting Metadata Export to CSV on: {complex_report}")
    csv_output_path = tmp_path / "metadata.csv"
    export_pbir_metadata_to_csv(complex_report, str(csv_output_path))

    assert csv_output_path.exists(), "CSV file was not created"

    with open(csv_output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) > 1, "CSV file is empty or only has header"
    header = lines[0].strip().split(",")
    expected_fields = [
        "Report",
        "Page Name",
        "Page ID",
        "Table",
        "Column or Measure",
        "Expression",
        "Used In",
        "Used In Detail",
        "ID",
    ]
    assert header == expected_fields


def test_sanitization_remove_unused_measures(complex_report):
    print("\nTesting Sanitization: Remove Unused Measures...")
    # complex_report has "UnusedMeasure"
    sanitize_powerbi_report(complex_report, ["remove_unused_measures"])

    # Verify UnusedMeasure is gone
    ext_path = os.path.join(complex_report, "definition", "reportExtensions.json")
    with open(ext_path, "r") as f:
        data = json.load(f)
    measures = data["entities"][0]["measures"]
    measure_names = [m["name"] for m in measures]
    assert "Measure1" in measure_names
    assert "UnusedMeasure" not in measure_names


def test_sanitization_remove_unused_bookmarks(complex_report):
    print("\nTesting Sanitization: Remove Unused Bookmarks...")
    # complex_report has Bookmark1 which is valid.
    # Let's add an invalid bookmark to test removal.
    bookmarks_dir = os.path.join(complex_report, "definition", "bookmarks")

    # Add invalid bookmark (referencing non-existent page)
    invalid_bookmark = {
        "name": "InvalidBookmark",
        "explorationState": {"activeSection": "NonExistentPage"},
    }
    with open(os.path.join(bookmarks_dir, "InvalidBookmark.bookmark.json"), "w") as f:
        json.dump(invalid_bookmark, f)

    # Update bookmarks.json
    with open(os.path.join(bookmarks_dir, "bookmarks.json"), "r+") as f:
        data = json.load(f)
        data["items"].append({"name": "InvalidBookmark"})
        f.seek(0)
        json.dump(data, f)
        f.truncate()

    sanitize_powerbi_report(
        complex_report, ["cleanup_invalid_bookmarks"]
    )  # Using cleanup_invalid_bookmarks as per original test logic for invalid refs

    # Verify InvalidBookmark is gone
    assert not os.path.exists(
        os.path.join(bookmarks_dir, "InvalidBookmark.bookmark.json")
    )
    # Verify Bookmark1 is still there
    assert os.path.exists(os.path.join(bookmarks_dir, "Bookmark1.bookmark.json"))


def test_batch_update(complex_report, tmp_path):
    print("\nTesting Batch Update...")
    # Create a dummy mapping CSV
    csv_path = tmp_path / "mapping.csv"
    with open(csv_path, "w", newline="") as f:
        f.write("old_tbl,old_col,new_tbl,new_col\n")
        f.write("Table1,Column1,NewTable,NewColumn\n")

    definition_folder = os.path.join(complex_report, "definition")
    batch_update_pbir_project(definition_folder, str(csv_path))

    # Verify update
    # Check reportExtensions.json for measure expression update
    ext_path = os.path.join(definition_folder, "reportExtensions.json")
    with open(ext_path, "r") as f:
        data = json.load(f)
    measure_expr = data["entities"][0]["measures"][0]["expression"]
    # Original: SUM(Table1[Column1])
    # Expected: SUM('NewTable'[NewColumn]) or similar depending on quoting logic
    assert "NewTable" in measure_expr
    assert "NewColumn" in measure_expr


def test_sanitization_remove_unused_custom_visuals(complex_report):
    print("\nTesting Sanitization: Remove Unused Custom Visuals...")
    # complex_report has customVisual1 in report.json, and Visual1 is columnChart (standard).
    sanitize_powerbi_report(complex_report, ["remove_unused_custom_visuals"])

    report_json_path = os.path.join(complex_report, "definition", "report.json")
    with open(report_json_path, "r") as f:
        data = json.load(f)
    assert "customVisual1" not in data.get("publicCustomVisuals", [])


def test_sanitization_disable_show_items_with_no_data(complex_report):
    print("\nTesting Sanitization: Disable Show Items With No Data...")
    # Add showAll: True to Visual1
    visual_path = os.path.join(
        complex_report,
        "definition",
        "pages",
        "Page1",
        "visuals",
        "Visual1",
        "visual.json",
    )
    with open(visual_path, "r+") as f:
        data = json.load(f)
        # Inject showAll property
        if "objects" not in data["visual"]:
            data["visual"]["objects"] = {}
        data["visual"]["objects"]["general"] = [{"properties": {"showAll": True}}]
        f.seek(0)
        json.dump(data, f)
        f.truncate()

    sanitize_powerbi_report(complex_report, ["disable_show_items_with_no_data"])

    with open(visual_path, "r") as f:
        data = json.load(f)
    # Check if showAll is removed or set to False (implementation removes it usually)
    props = data["visual"]["objects"]["general"][0]["properties"]
    assert "showAll" not in props


def test_sanitization_hide_tooltip_pages(complex_report):
    print("\nTesting Sanitization: Hide Tooltip Pages...")
    # complex_report Page2 is Tooltip but already HiddenInViewMode.
    # Let's set it to Visible to test the sanitizer.
    page2_path = os.path.join(
        complex_report, "definition", "pages", "Page2", "page.json"
    )
    with open(page2_path, "r+") as f:
        data = json.load(f)
        data["visibility"] = "Visible"
        f.seek(0)
        json.dump(data, f)
        f.truncate()

    sanitize_powerbi_report(complex_report, ["hide_tooltip_pages"])

    with open(page2_path, "r") as f:
        data = json.load(f)
    assert data["visibility"] == "HiddenInViewMode"


def test_sanitization_remove_empty_pages(complex_report):
    print("\nTesting Sanitization: Remove Empty Pages...")
    # complex_report Page2 is empty but it is a Tooltip page, so it might be preserved depending on logic.
    # Let's create a standard empty page.
    pages_dir = os.path.join(complex_report, "definition", "pages")
    empty_page_dir = os.path.join(pages_dir, "EmptyPage")
    os.makedirs(empty_page_dir, exist_ok=True)
    os.makedirs(os.path.join(empty_page_dir, "visuals"), exist_ok=True)

    with open(os.path.join(empty_page_dir, "page.json"), "w") as f:
        json.dump(
            {
                "name": "EmptyPage",
                "displayName": "Empty Page",
                "pageBinding": {"type": "ReportSection"},
            },
            f,
        )

    # Update pages.json
    pages_json_path = os.path.join(pages_dir, "pages.json")
    with open(pages_json_path, "r+") as f:
        data = json.load(f)
        data["pageOrder"].append("EmptyPage")
        f.seek(0)
        json.dump(data, f)
        f.truncate()

    sanitize_powerbi_report(complex_report, ["remove_empty_pages"])

    assert not os.path.exists(empty_page_dir)


def test_sanitization_remove_hidden_visuals_never_shown(complex_report):
    print("\nTesting Sanitization: Remove Hidden Visuals Never Shown...")
    # Create a hidden visual in Page1 that is NOT used in bookmarks or interactions
    visuals_dir = os.path.join(
        complex_report, "definition", "pages", "Page1", "visuals"
    )
    hidden_visual_dir = os.path.join(visuals_dir, "HiddenVisual")
    os.makedirs(hidden_visual_dir, exist_ok=True)

    with open(os.path.join(hidden_visual_dir, "visual.json"), "w") as f:
        json.dump(
            {
                "name": "HiddenVisual",
                "isHidden": True,
                "visual": {"visualType": "card"},
            },
            f,
        )

    sanitize_powerbi_report(complex_report, ["remove_hidden_visuals_never_shown"])

    assert not os.path.exists(hidden_visual_dir)
