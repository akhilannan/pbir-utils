"""Tests for the PBIR-Utils API endpoints."""

import pytest


@pytest.fixture
def api_client():
    """Create a FastAPI test client."""
    from fastapi.testclient import TestClient
    from pbir_utils.api.main import app

    return TestClient(app)


@pytest.fixture
def sample_report(tmp_path):
    """Create a minimal sample report structure for testing."""
    report_path = tmp_path / "Test.Report"
    definition = report_path / "definition"
    pages_dir = definition / "pages"
    page1_dir = pages_dir / "page1"
    visuals_dir = page1_dir / "visuals"
    visual1_dir = visuals_dir / "visual1"

    # Create directories
    visual1_dir.mkdir(parents=True)

    # Create pages.json
    (pages_dir / "pages.json").write_text(
        '{"pageOrder": ["page1"], "activePageName": "page1"}'
    )

    # Create page.json
    (page1_dir / "page.json").write_text(
        '{"name": "page1", "displayName": "Page 1", "width": 1280, "height": 720}'
    )

    # Create visual.json - position must be at top level
    (visual1_dir / "visual.json").write_text(
        """{
        "name": "visual1",
        "position": {"x": 100, "y": 100, "z": 1, "width": 200, "height": 150},
        "visual": {"visualType": "card"}
    }"""
    )

    # Create report.json
    (definition / "report.json").write_text('{"name": "Test Report"}')

    return str(report_path)


# ============ Health Check ============


def test_health_check(api_client):
    """Test health endpoint returns ok."""
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_with_initial_report(api_client, sample_report):
    """Test index page with initial_report query parameter."""
    response = api_client.get(f"/?initial_report={sample_report}")
    assert response.status_code == 200
    # Should contain the initial report path in the JavaScript variable
    assert "initialReportPath" in response.text
    # Path should be JSON-encoded in the response
    assert "Test.Report" in response.text


# ============ Browse Endpoints ============


def test_browse_root(api_client):
    """Test browse returns home directory by default."""
    response = api_client.get("/api/browse")
    assert response.status_code == 200
    data = response.json()
    assert "current_path" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_browse_directory(api_client, tmp_path):
    """Test browsing a specific directory."""
    # Create some test directories
    (tmp_path / "TestFolder").mkdir()
    (tmp_path / "Sample.Report" / "definition").mkdir(parents=True)

    response = api_client.get(f"/api/browse?path={tmp_path}")
    assert response.status_code == 200

    data = response.json()
    items = data["items"]

    # Should find both directories
    names = [item["name"] for item in items]
    assert "TestFolder" in names
    assert "Sample.Report" in names

    # Sample.Report should be marked as report
    report_item = next(i for i in items if i["name"] == "Sample.Report")
    assert report_item["is_report"] is True
    assert report_item["is_dir"] is True


def test_browse_nonexistent_returns_404(api_client):
    """Test that nonexistent paths return 404."""
    response = api_client.get("/api/browse?path=/nonexistent/path/xyz123")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_browse_file_returns_400(api_client, tmp_path):
    """Test that browsing a file returns 400."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")

    response = api_client.get(f"/api/browse?path={test_file}")
    assert response.status_code == 400
    assert "not a directory" in response.json()["detail"].lower()


def test_browse_excluded_path_returns_403(api_client):
    """Test that browsing excluded system paths returns 403."""
    import platform

    if platform.system().lower() == "windows":
        excluded_path = "C:\\Windows"
    else:
        excluded_path = "/etc"

    response = api_client.get(f"/api/browse?path={excluded_path}")
    assert response.status_code == 403
    assert "restricted" in response.json()["detail"].lower()


def test_browse_normal_path_allowed(api_client, tmp_path):
    """Test that normal (non-excluded) paths are still allowed."""
    response = api_client.get(f"/api/browse?path={tmp_path}")
    assert response.status_code == 200


# ============ Wireframe Endpoints ============


def test_wireframe_data(api_client, sample_report):
    """Test getting wireframe data for a report."""
    response = api_client.post(
        "/api/reports/wireframe", json={"report_path": sample_report}
    )
    assert response.status_code == 200

    data = response.json()
    assert "report_name" in data
    assert data["report_name"] == "Test"
    assert "pages" in data
    assert len(data["pages"]) == 1
    assert "fields_index" in data
    assert "active_page_id" in data
    assert "html_content" in data
    assert data["html_content"] is not None
    assert "header" in data["html_content"]


def test_wireframe_invalid_path(api_client):
    """Test wireframe with invalid report path returns 404."""
    response = api_client.post(
        "/api/reports/wireframe", json={"report_path": "/invalid/path"}
    )
    assert response.status_code == 400


def test_wireframe_with_page_filter(api_client, sample_report):
    """Test wireframe with page filters."""
    # Test that API accepts filter parameters (filter matches page ID)
    response = api_client.post(
        "/api/reports/wireframe",
        json={"report_path": sample_report, "show_hidden": True},
    )
    assert response.status_code == 200


# ============ Actions Endpoints ============


def test_list_actions(api_client):
    """Test listing available sanitize actions."""
    response = api_client.get("/api/reports/actions")
    assert response.status_code == 200

    data = response.json()
    assert "actions" in data
    actions = data["actions"]

    # Actions are ActionInfo objects with id, description, is_default
    action_ids = [a["id"] for a in actions]
    # Should have some common default actions
    assert "remove_unused_bookmarks" in action_ids
    assert "cleanup_invalid_bookmarks" in action_ids


def test_get_config(api_client):
    """Test getting default sanitize config."""
    response = api_client.get("/api/reports/config")
    assert response.status_code == 200

    data = response.json()
    assert "actions" in data
    assert "definitions" in data


def test_load_custom_config(api_client, tmp_path):
    """Test uploading a custom config file."""
    config_file = tmp_path / "custom.yaml"
    config_file.write_text(
        """
actions:
  - remove_unused_bookmarks
definitions:
  custom_action:
    enabled: true
"""
    )

    with open(config_file, "rb") as f:
        response = api_client.post("/api/reports/config", files={"file": f})

    assert response.status_code == 200
    data = response.json()
    assert "remove_unused_bookmarks" in data["actions"]


def test_load_invalid_config(api_client, tmp_path):
    """Test uploading invalid YAML returns 400."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("invalid: yaml: content: [")

    with open(config_file, "rb") as f:
        response = api_client.post("/api/reports/config", files={"file": f})

    assert response.status_code == 400


# ============ Run Actions ============


def test_run_action_dry_run(api_client, sample_report):
    """Test running an action in dry-run mode."""
    response = api_client.post(
        "/api/reports/run",
        json={
            "report_path": sample_report,
            "actions": ["clear_filters"],
            "dry_run": True,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert "success" in data
    assert "output" in data


# ============ CSV Export ============


def test_metadata_csv_download(api_client, sample_report):
    """Test downloading metadata CSV."""
    response = api_client.get(f"/api/reports/metadata/csv?report_path={sample_report}")
    # May return 404 if no metadata, which is fine for minimal sample
    assert response.status_code in [200, 404]

    if response.status_code == 200:
        assert "text/csv" in response.headers.get("content-type", "")


def test_visuals_csv_download(api_client, sample_report):
    """Test downloading visuals CSV."""
    response = api_client.get(f"/api/reports/visuals/csv?report_path={sample_report}")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")

    # Check CSV content
    content = response.text
    assert "Visual Type" in content
    assert "card" in content


def test_wireframe_html_download(api_client, sample_report):
    """Test downloading wireframe as HTML file."""
    response = api_client.get(
        f"/api/reports/wireframe/html?report_path={sample_report}"
    )
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "<html" in response.text.lower()


# ============ Console Broadcast ============


def test_console_broadcast_pattern():
    """Test that console broadcast works without breaking CLI."""
    from pbir_utils.console_utils import console

    with console.capture_output() as queue:
        console.print_success("Test message")
        console.print_warning("Warning message")
        console.print_info("Info message")

        # Drain queue
        messages = []
        while not queue.empty():
            messages.append(queue.get_nowait())

    assert len(messages) == 3
    assert messages[0]["type"] == "success"
    assert messages[0]["message"] == "Test message"
    assert messages[1]["type"] == "warning"
    assert messages[2]["type"] == "info"


def test_console_broadcast_multiple_queues():
    """Test that multiple queues receive the same messages."""
    from pbir_utils.console_utils import console

    with console.capture_output() as q1:
        with console.capture_output() as q2:
            console.print_success("Shared message")

            msg1 = q1.get_nowait()
            msg2 = q2.get_nowait()

    assert msg1["message"] == "Shared message"
    assert msg2["message"] == "Shared message"
