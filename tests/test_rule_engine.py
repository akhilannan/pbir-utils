"""Tests for rule_engine module."""

import pytest
from unittest.mock import patch, MagicMock

from pbir_utils.rule_engine import (
    load_pbir_context,
    validate_report,
    ValidationError,
    _evaluate_expression_rule,
)
from pbir_utils.rule_config import RuleSpec


class TestLoadPbirContext:
    """Tests for load_pbir_context function."""

    def test_loads_report_json(self, tmp_path):
        """Test that report.json is loaded into context."""
        report_path = tmp_path / "Test.Report"
        definition_path = report_path / "definition"
        definition_path.mkdir(parents=True)

        report_json = definition_path / "report.json"
        report_json.write_text('{"activeSectionIndex": 0}')

        context = load_pbir_context(str(report_path))
        assert context["report"]["activeSectionIndex"] == 0

    def test_loads_pages_with_visuals(self, tmp_path):
        """Test that pages and visuals are loaded into context."""
        report_path = tmp_path / "Test.Report"
        definition_path = report_path / "definition"
        pages_path = definition_path / "pages"
        page_path = pages_path / "abc123"
        visuals_path = page_path / "visuals"
        visual_path = visuals_path / "xyz789"

        visual_path.mkdir(parents=True)

        # Create page.json
        page_json = page_path / "page.json"
        page_json.write_text('{"name": "abc123", "displayName": "Overview"}')

        # Create visual.json
        visual_json = visual_path / "visual.json"
        visual_json.write_text('{"name": "xyz789", "visual": {"visualType": "card"}}')

        context = load_pbir_context(str(report_path))

        assert len(context["pages"]) == 1
        assert context["pages"][0]["displayName"] == "Overview"
        assert len(context["pages"][0]["visuals"]) == 1
        assert context["pages"][0]["visuals"][0]["visual"]["visualType"] == "card"

    def test_empty_report_returns_valid_structure(self, tmp_path):
        """Test that empty report returns valid empty structure."""
        report_path = tmp_path / "Empty.Report"
        definition_path = report_path / "definition"
        definition_path.mkdir(parents=True)

        context = load_pbir_context(str(report_path))

        assert context["report"] == {}
        assert context["pages"] == []
        assert context["bookmarks"] == []


class TestEvaluateExpressionRule:
    """Tests for _evaluate_expression_rule function."""

    def test_report_scope_passes(self):
        """Test report-scope rule that passes."""
        rule = RuleSpec(
            id="test_rule",
            expression="len(pages) <= 10",
            scope="report",
        )
        context = {"pages": [{"name": "page1"}]}

        passed, violations = _evaluate_expression_rule(rule, context)

        assert passed is True
        assert violations == []

    def test_report_scope_fails(self):
        """Test report-scope rule that fails."""
        rule = RuleSpec(
            id="test_rule",
            expression="len(pages) <= 1",
            scope="report",
        )
        context = {"pages": [{"name": "p1"}, {"name": "p2"}, {"name": "p3"}]}

        passed, violations = _evaluate_expression_rule(rule, context)

        assert passed is False
        assert len(violations) == 1

    def test_page_scope_evaluates_per_page(self):
        """Test page-scope rule evaluates for each page."""
        rule = RuleSpec(
            id="visual_limit",
            expression="len(page.get('visuals', [])) <= 2",
            scope="page",
        )
        context = {
            "pages": [
                {"name": "p1", "displayName": "Good Page", "visuals": [{}]},
                {"name": "p2", "displayName": "Bad Page", "visuals": [{}, {}, {}]},
            ]
        }

        passed, violations = _evaluate_expression_rule(rule, context)

        assert passed is False
        assert len(violations) == 1
        assert violations[0]["page_name"] == "Bad Page"

    def test_params_available_in_expression(self):
        """Test that rule params are available in expression context."""
        rule = RuleSpec(
            id="test_rule",
            expression="len(pages) <= max_pages",
            scope="report",
            params={"max_pages": 5},
        )
        context = {"pages": [{}] * 3}

        passed, violations = _evaluate_expression_rule(rule, context)
        assert passed is True

    def test_expression_error_creates_violation(self):
        """Test that expression errors create violations."""
        rule = RuleSpec(
            id="test_rule",
            expression="undefined_variable > 0",
            scope="report",
        )
        context = {}

        passed, violations = _evaluate_expression_rule(rule, context)

        assert passed is False
        assert len(violations) == 1
        assert "Expression error" in violations[0]["message"]


class TestValidateReport:
    """Tests for validate_report function."""

    def test_returns_validation_result(self, tmp_path):
        """Test that validate_report returns ValidationResult with results."""
        from pbir_utils.rule_engine import ValidationResult

        # Create minimal report structure
        report_path = tmp_path / "Test.Report"
        definition_path = report_path / "definition"
        definition_path.mkdir(parents=True)

        # Mock sanitize to not actually run
        with patch("pbir_utils.rule_engine.sanitize_powerbi_report") as mock_sanitize:
            mock_sanitize.return_value = {}
            with patch("pbir_utils.rule_engine.load_rules") as mock_load:
                mock_load.return_value = MagicMock(
                    rules=[
                        RuleSpec(
                            id="test_rule",
                            expression="True",
                            scope="report",
                        )
                    ],
                    fail_on_warning=False,
                )
                with patch("pbir_utils.rule_engine.console"):
                    result = validate_report(str(report_path), strict=False)

        assert isinstance(result, ValidationResult)
        assert "test_rule" in result.results
        assert result.results["test_rule"] is True

    def test_strict_mode_raises_on_violations(self, tmp_path):
        """Test that strict mode raises ValidationError on violations."""
        report_path = tmp_path / "Test.Report"
        definition_path = report_path / "definition"
        definition_path.mkdir(parents=True)

        with patch("pbir_utils.rule_engine.sanitize_powerbi_report") as mock_sanitize:
            mock_sanitize.return_value = {}
            with patch("pbir_utils.rule_engine.load_rules") as mock_load:
                mock_load.return_value = MagicMock(
                    rules=[
                        RuleSpec(
                            id="failing_rule",
                            expression="False",
                            scope="report",
                            severity="error",
                        )
                    ],
                    fail_on_warning=False,
                )
                with patch("pbir_utils.rule_engine.console"):
                    with pytest.raises(ValidationError) as exc_info:
                        validate_report(str(report_path), strict=True)

        assert len(exc_info.value.violations) > 0

    def test_severity_filter_works(self, tmp_path):
        """Test that severity filter excludes lower severity rules."""
        report_path = tmp_path / "Test.Report"
        definition_path = report_path / "definition"
        definition_path.mkdir(parents=True)

        with patch("pbir_utils.rule_engine.sanitize_powerbi_report") as mock_sanitize:
            mock_sanitize.return_value = {}
            with patch("pbir_utils.rule_engine.load_rules") as mock_load:
                mock_load.return_value = MagicMock(
                    rules=[
                        RuleSpec(id="info_rule", severity="info", expression="True"),
                        RuleSpec(id="warn_rule", severity="warning", expression="True"),
                    ],
                    fail_on_warning=False,
                )
                with patch("pbir_utils.rule_engine.console"):
                    result = validate_report(
                        str(report_path), severity="warning", strict=False
                    )

        # Only warning severity and above should be in results
        assert "warn_rule" in result.results
        assert "info_rule" not in result.results
