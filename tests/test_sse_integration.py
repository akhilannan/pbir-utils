import base64
import json
from pathlib import Path
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
    url = f"/api/reports/validate/run/stream?report_path={sample_report_structure}&include_sanitizer=true&sanitize_actions=cleanup_invalid_bookmarks"

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


def test_validate_run_stream_with_custom_sanitize_config(
    api_client, sample_report_structure, tmp_path
):
    """Test validation stream preserves custom sanitize action params."""
    theme_file = tmp_path / "Corporate.json"
    theme_file.write_text('{"name": "Corporate"}')

    report_path = Path(sample_report_structure)
    report_json = report_path / "definition" / "report.json"
    report_json.write_text(
        json.dumps(
            {
                "name": "Test Report",
                "themeCollection": {
                    "customTheme": {
                        "name": "Corporate.json",
                        "reportVersionAtImport": {
                            "visual": "1.8.0",
                            "report": "2.0.0",
                            "page": "1.3.0",
                        },
                        "type": "RegisteredResources",
                    }
                },
                "resourcePackages": [
                    {
                        "name": "RegisteredResources",
                        "type": "RegisteredResources",
                        "items": [
                            {
                                "name": "Corporate.json",
                                "path": "Corporate.json",
                                "type": "CustomTheme",
                            }
                        ],
                    }
                ],
            }
        )
    )

    registered_resources = report_path / "StaticResources" / "RegisteredResources"
    registered_resources.mkdir(parents=True)
    (registered_resources / "Corporate.json").write_text('{"name": "Corporate"}')

    sanitize_yaml = f"""
definitions:
  set_theme:
    description: Apply corporate theme
    params:
      theme_path: '{theme_file.as_posix()}'
include:
  - set_theme
"""
    encoded_yaml = base64.b64encode(sanitize_yaml.encode("utf-8")).decode("ascii")

    with api_client.stream(
        "GET",
        "/api/reports/validate/run/stream",
        params={
            "report_path": sample_report_structure,
            "include_sanitizer": "true",
            "sanitize_actions": "set_theme",
            "sanitize_config_yaml": encoded_yaml,
        },
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        assert len(events) > 0
        assert any(event.get("passed") == 1 for event in events if "passed" in event)
