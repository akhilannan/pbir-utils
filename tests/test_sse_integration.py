import json
import pytest
from fastapi.testclient import TestClient
from pbir_utils.api.main import app


@pytest.fixture
def api_client():
    return TestClient(app)


@pytest.fixture
def sample_report_structure(tmp_path):
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

    # Create visual.json
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


def test_run_actions_stream(api_client, sample_report_structure):
    """Test the run_actions_stream endpoint with a dry run."""
    # Use a simple default action 'cleanup_invalid_bookmarks' which should be harmless
    action = "cleanup_invalid_bookmarks"
    url = f"/api/reports/run/stream?path={sample_report_structure}&actions={action}&dry_run=true"

    with api_client.stream("GET", url) as response:
        assert response.status_code == 200
        # SSE streams return text/event-stream
        assert "text/event-stream" in response.headers["content-type"]

        # Collect messages
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                events.append(data)

        # Verify we got some output
        assert len(events) > 0
        # Should have a 'steps' or 'info' message
        types = [e.get("type") for e in events]
        assert "info" in types or "steps" in types
        # Should NOT have error
        assert "error" not in types


def test_validate_run_stream(api_client, sample_report_structure):
    """Test the validation stream endpoint."""
    url = f"/api/reports/validate/run/stream?report_path={sample_report_structure}&include_sanitizer=true"

    with api_client.stream("GET", url) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                events.append(data)

        assert len(events) > 0

        # Check for expected messages
        messages = [e.get("message", "") for e in events]
        # Should mention starting validation or running actions
        # Note: validate_report prints "Validating {report_name}"
        assert any("Validating" in m or "Running" in m for m in messages)
        # Should verify no errors (unless expected)
        types = [e.get("type") for e in events]
        assert "error" not in types
