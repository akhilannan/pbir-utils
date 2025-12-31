import os
from pbir_utils.folder_standardizer import standardize_pbir_folders, _sanitize_name
from pbir_utils.common import write_json


def test_sanitize_name():
    assert _sanitize_name("Simple Name") == "Simple_Name"
    assert _sanitize_name("Name with @ Special # Chars!") == "Name_with_Special_Chars"
    assert _sanitize_name("  Trim Me  ") == "Trim_Me"
    assert _sanitize_name("Multiple___Underscores") == "Multiple_Underscores"


def test_rename_pages_and_visuals(temp_report_structure):
    # Setup Page 1
    page1_id = "page1guid"
    page1_name = "Page 1"
    page1_dir = temp_report_structure / "definition" / "pages" / page1_id
    os.makedirs(page1_dir)
    write_json(
        str(page1_dir / "page.json"), {"name": page1_id, "displayName": page1_name}
    )

    # Setup Visual 1 in Page 1
    visual1_id = "visual1guid"
    visual1_type = "card"
    visual1_dir = page1_dir / "visuals" / visual1_id
    os.makedirs(visual1_dir)
    write_json(
        str(visual1_dir / "visual.json"),
        {"name": visual1_id, "visual": {"visualType": visual1_type}},
    )

    # Setup Page 2 (Already renamed format, should be idempotent or update if name changed)
    page2_id = "page2guid"
    page2_name = "Page 2"
    page2_folder_name = "Page_2_page2guid"
    page2_dir = temp_report_structure / "definition" / "pages" / page2_folder_name
    os.makedirs(page2_dir)
    write_json(
        str(page2_dir / "page.json"), {"name": page2_id, "displayName": page2_name}
    )

    # Run renaming
    standardize_pbir_folders(str(temp_report_structure))

    # Verify Page 1 Renamed
    expected_page1_dir = (
        temp_report_structure / "definition" / "pages" / "Page_1_page1guid"
    )
    assert os.path.exists(expected_page1_dir)
    assert not os.path.exists(page1_dir)

    # Verify Visual 1 Renamed
    expected_visual1_dir = expected_page1_dir / "visuals" / "card_visual1guid"
    assert os.path.exists(expected_visual1_dir)

    # Verify Page 2 Unchanged (Idempotency)
    assert os.path.exists(page2_dir)


def test_rename_with_special_chars(temp_report_structure):
    page_id = "specialguid"
    page_name = "Page & More!"
    page_dir = temp_report_structure / "definition" / "pages" / page_id
    os.makedirs(page_dir)
    write_json(str(page_dir / "page.json"), {"name": page_id, "displayName": page_name})

    standardize_pbir_folders(str(temp_report_structure))

    expected_dir = (
        temp_report_structure / "definition" / "pages" / "Page_More_specialguid"
    )
    assert os.path.exists(expected_dir)


def test_pages_dir_not_found(tmp_path, capsys):
    """Test behavior when pages directory does not exist."""
    report_dir = tmp_path / "EmptyReport.Report"
    os.makedirs(report_dir)

    result = standardize_pbir_folders(str(report_dir))

    assert result is False
    captured = capsys.readouterr()
    assert "Pages directory not found" in captured.out


def test_page_json_not_found(temp_report_structure):
    """Test behavior when page.json does not exist in a page folder."""
    page_dir = temp_report_structure / "definition" / "pages" / "orphan_folder"
    os.makedirs(page_dir)

    result = standardize_pbir_folders(str(temp_report_structure))

    # No rename should happen, folder should remain
    assert result is False
    assert os.path.exists(page_dir)


def test_page_missing_name_or_displayname(temp_report_structure):
    """Test behavior when page.json is missing name or displayName."""
    page_dir = temp_report_structure / "definition" / "pages" / "incomplete_page"
    os.makedirs(page_dir)
    # Missing displayName
    write_json(str(page_dir / "page.json"), {"name": "someid"})

    result = standardize_pbir_folders(str(temp_report_structure))

    assert result is False
    assert os.path.exists(page_dir)


def test_visual_json_not_found(temp_report_structure):
    """Test behavior when visual.json does not exist in a visual folder."""
    page_id = "page_with_orphan_visual"
    page_dir = temp_report_structure / "definition" / "pages" / page_id
    os.makedirs(page_dir)
    write_json(
        str(page_dir / "page.json"), {"name": page_id, "displayName": "TestPage"}
    )

    visual_dir = page_dir / "visuals" / "orphan_visual"
    os.makedirs(visual_dir)
    # No visual.json

    result = standardize_pbir_folders(str(temp_report_structure))

    # Page should be renamed, but visual should remain unchanged
    assert result is True
    new_page_dir = (
        temp_report_structure
        / "definition"
        / "pages"
        / "TestPage_page_with_orphan_visual"
    )
    assert os.path.exists(new_page_dir / "visuals" / "orphan_visual")


def test_visual_missing_name_or_type(temp_report_structure):
    """Test behavior when visual.json is missing name or visualType."""
    page_id = "page_with_incomplete_visual"
    page_dir = temp_report_structure / "definition" / "pages" / page_id
    os.makedirs(page_dir)
    write_json(
        str(page_dir / "page.json"), {"name": page_id, "displayName": "TestPage"}
    )

    visual_dir = page_dir / "visuals" / "incomplete_visual"
    os.makedirs(visual_dir)
    # Missing visualType
    write_json(str(visual_dir / "visual.json"), {"name": "vizid"})

    result = standardize_pbir_folders(str(temp_report_structure))

    # Page should be renamed, but visual should remain unchanged
    assert result is True
    new_page_dir = (
        temp_report_structure
        / "definition"
        / "pages"
        / "TestPage_page_with_incomplete_visual"
    )
    assert os.path.exists(new_page_dir / "visuals" / "incomplete_visual")


def test_dry_run_mode(temp_report_structure):
    """Test that dry_run mode does not make changes."""
    page_id = "dryrunpage"
    page_dir = temp_report_structure / "definition" / "pages" / page_id
    os.makedirs(page_dir)
    write_json(
        str(page_dir / "page.json"), {"name": page_id, "displayName": "DryRunPage"}
    )

    result = standardize_pbir_folders(str(temp_report_structure), dry_run=True)

    assert result is True
    # Original folder should still exist
    assert os.path.exists(page_dir)
    # New folder should not exist
    new_dir = temp_report_structure / "definition" / "pages" / "DryRunPage_dryrunpage"
    assert not os.path.exists(new_dir)


def test_dry_run_with_summary(temp_report_structure, capsys):
    """Test dry_run with summary mode."""
    page_id = "summarypage"
    page_dir = temp_report_structure / "definition" / "pages" / page_id
    os.makedirs(page_dir)
    write_json(
        str(page_dir / "page.json"), {"name": page_id, "displayName": "SummaryPage"}
    )

    result = standardize_pbir_folders(
        str(temp_report_structure), dry_run=True, summary=True
    )

    assert result is True
    captured = capsys.readouterr()
    assert "Would rename" in captured.out


def test_no_changes_needed(temp_report_structure, capsys):
    """Test when all folders are already standardized."""
    page_id = "alreadystandardized"
    page_folder_name = "AlreadyStandardized_alreadystandardized"
    page_dir = temp_report_structure / "definition" / "pages" / page_folder_name
    os.makedirs(page_dir)
    write_json(
        str(page_dir / "page.json"),
        {"name": page_id, "displayName": "AlreadyStandardized"},
    )

    result = standardize_pbir_folders(str(temp_report_structure))

    assert result is False
    captured = capsys.readouterr()
    assert "already using standard naming" in captured.out


def test_summary_mode_non_dry_run(temp_report_structure, capsys):
    """Test summary mode without dry_run."""
    page_id = "summarynondry"
    page_dir = temp_report_structure / "definition" / "pages" / page_id
    os.makedirs(page_dir)
    write_json(
        str(page_dir / "page.json"), {"name": page_id, "displayName": "SummaryNonDry"}
    )

    result = standardize_pbir_folders(str(temp_report_structure), summary=True)

    assert result is True
    captured = capsys.readouterr()
    assert "Renamed" in captured.out
    assert "1 page folders" in captured.out
