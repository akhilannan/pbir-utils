import os
import pytest
from pbir_utils.folder_standardizer import standardize_pbir_folders, _sanitize_name
from pbir_utils.common import write_json


@pytest.fixture
def temp_report_structure(tmp_path):
    report_dir = tmp_path / "TestReport.Report"
    pages_dir = report_dir / "definition" / "pages"
    os.makedirs(pages_dir)
    return report_dir


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
