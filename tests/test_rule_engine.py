"""Tests for rule_engine module."""

import pytest
from unittest.mock import patch, MagicMock

from pbir_utils.rule_engine import (
    load_pbir_context,
    validate_report,
    ValidationError,
    ValidationResult,
    _evaluate_expression_rule,
    _safe_eval,
    _create_safe_evaluator,
    _get_path,
    _has_path,
    _find_all,
)
from pbir_utils.rule_config import RuleSpec


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_counts_errors_warnings_info(self):
        """Test that ValidationResult counts severity correctly."""
        results = {"r1": False, "r2": False, "r3": True}
        violations = [
            {"rule_id": "r1", "severity": "error"},
            {"rule_id": "r2", "severity": "warning"},
        ]

        result = ValidationResult(results, violations)

        assert result.error_count == 1
        assert result.warning_count == 1
        assert result.info_count == 0
        assert result.passed == 1
        assert result.failed == 2

    def test_has_errors_property(self):
        """Test has_errors property returns True when errors exist."""
        violations = [{"severity": "error"}]
        result = ValidationResult({"r1": False}, violations)
        assert result.has_errors is True

        result_no_errors = ValidationResult({"r1": True}, [])
        assert result_no_errors.has_errors is False

    def test_has_warnings_property(self):
        """Test has_warnings property returns True when warnings exist."""
        violations = [{"severity": "warning"}]
        result = ValidationResult({"r1": False}, violations)
        assert result.has_warnings is True

        result_no_warnings = ValidationResult({"r1": True}, [])
        assert result_no_warnings.has_warnings is False

    def test_repr_format(self):
        """Test __repr__ returns formatted string."""
        results = {"r1": True, "r2": False}
        violations = [
            {"severity": "error"},
            {"severity": "warning"},
            {"severity": "info"},
        ]
        result = ValidationResult(results, violations)

        repr_str = repr(result)
        assert "1 passed" in repr_str
        assert "1 errors" in repr_str
        assert "1 warnings" in repr_str
        assert "1 info" in repr_str


class TestSafeEval:
    """Tests for safe evaluation functions."""

    def test_safe_eval_basic_expression(self):
        """Test _safe_eval evaluates basic expressions."""
        result = _safe_eval("1 + 2", {})
        assert result == 3

    def test_safe_eval_with_context(self):
        """Test _safe_eval uses provided context."""
        result = _safe_eval("x + y", {"x": 10, "y": 20})
        assert result == 30

    def test_safe_eval_len_function(self):
        """Test _safe_eval has len available."""
        result = _safe_eval("len(items)", {"items": [1, 2, 3]})
        assert result == 3

    def test_safe_eval_regex_match(self):
        """Test re_match function is available."""
        result = _safe_eval("re_match('^test', 'test_string')", {})
        assert result is True

        result = _safe_eval("re_match('^foo', 'test_string')", {})
        assert result is False

    def test_safe_eval_regex_search(self):
        """Test re_search function is available."""
        result = _safe_eval("re_search('pattern', 'has pattern here')", {})
        assert result is True

        result = _safe_eval("re_search('missing', 'has pattern here')", {})
        assert result is False

    def test_safe_eval_with_none_string(self):
        """Test re_match handles None strings."""
        result = _safe_eval("re_match('^test', None)", {})
        assert result is False

    def test_create_safe_evaluator_has_all_functions(self):
        """Test evaluator has all expected safe functions."""
        evaluator = _create_safe_evaluator({})

        expected_funcs = [
            "len",
            "str",
            "int",
            "float",
            "bool",
            "sum",
            "min",
            "max",
            "any",
            "all",
            "abs",
            "round",
            "sorted",
            "reversed",
            "re_match",
            "re_search",
        ]
        for func in expected_funcs:
            assert func in evaluator.functions


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

    def test_loads_bookmarks(self, tmp_path):
        """Test that bookmarks are loaded into context."""
        report_path = tmp_path / "Test.Report"
        definition_path = report_path / "definition"
        bookmarks_path = definition_path / "bookmarks"
        bookmarks_path.mkdir(parents=True)

        # Create bookmarks.json
        bookmarks_meta = bookmarks_path / "bookmarks.json"
        bookmarks_meta.write_text('{"items": [{"name": "bm1"}]}')

        # Create bookmark file
        bookmark_file = bookmarks_path / "bm1.bookmark.json"
        bookmark_file.write_text('{"name": "bm1", "displayName": "Bookmark 1"}')

        context = load_pbir_context(str(report_path))

        assert len(context["bookmarks"]) == 1
        assert context["bookmarks"][0]["displayName"] == "Bookmark 1"

    def test_loads_report_extensions(self, tmp_path):
        """Test that reportExtensions.json is loaded."""
        report_path = tmp_path / "Test.Report"
        definition_path = report_path / "definition"
        definition_path.mkdir(parents=True)

        extensions = definition_path / "reportExtensions.json"
        extensions.write_text('{"entities": [{"name": "Measures"}]}')

        context = load_pbir_context(str(report_path))

        assert len(context["reportExtensions"]["entities"]) == 1


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

    def test_visual_scope_evaluates_per_visual(self):
        """Test visual-scope rule evaluates for each visual."""
        rule = RuleSpec(
            id="visual_type_check",
            expression="visual.get('visual', {}).get('visualType') != 'table'",
            scope="visual",
        )
        context = {
            "pages": [
                {
                    "name": "p1",
                    "displayName": "Page 1",
                    "visuals": [
                        {"name": "v1", "visual": {"visualType": "card"}},
                        {"name": "v2", "visual": {"visualType": "table"}},
                    ],
                }
            ]
        }

        passed, violations = _evaluate_expression_rule(rule, context)

        assert passed is False
        assert len(violations) == 1
        assert violations[0]["visual_name"] == "v2"

    def test_measure_scope_evaluates_per_measure(self):
        """Test measure-scope rule evaluates for each measure."""
        rule = RuleSpec(
            id="measure_name_check",
            expression="not measure.get('name', '').startswith('_')",
            scope="measure",
        )
        context = {
            "reportExtensions": {
                "entities": [
                    {
                        "name": "Measures",
                        "measures": [
                            {"name": "Total Sales"},
                            {"name": "_Hidden Measure"},
                        ],
                    }
                ]
            }
        }

        passed, violations = _evaluate_expression_rule(rule, context)

        assert passed is False
        assert len(violations) == 1
        assert violations[0]["measure_name"] == "_Hidden Measure"

    def test_bookmark_scope_evaluates_per_bookmark(self):
        """Test bookmark-scope rule evaluates for each bookmark."""
        rule = RuleSpec(
            id="bookmark_name_check",
            expression="len(bookmark.get('name', '')) <= 20",
            scope="bookmark",
        )
        context = {
            "bookmarks": [
                {"name": "short"},
                {"name": "this_is_a_very_long_bookmark_name_that_exceeds_limit"},
            ]
        }

        passed, violations = _evaluate_expression_rule(rule, context)

        assert passed is False
        assert len(violations) == 1
        assert (
            violations[0]["bookmark_name"]
            == "this_is_a_very_long_bookmark_name_that_exceeds_limit"
        )

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

    def test_page_scope_expression_error(self):
        """Test that page-scope expression errors create violations."""
        rule = RuleSpec(
            id="test_rule",
            expression="undefined_var > 0",
            scope="page",
        )
        context = {"pages": [{"name": "p1"}]}

        passed, violations = _evaluate_expression_rule(rule, context)

        assert passed is False
        assert "Expression error" in violations[0]["message"]

    def test_visual_scope_skips_non_matching_structure(self):
        """Test that visual-scope silently skips visuals that don't match."""
        rule = RuleSpec(
            id="test_rule",
            # Expression that will fail for visuals without 'visual' key
            expression="visual['visual']['someProp'] == 'value'",
            scope="visual",
        )
        context = {
            "pages": [{"name": "p1", "visuals": [{"name": "v1"}]}]  # No 'visual' key
        }

        # Should not raise, just skip
        passed, violations = _evaluate_expression_rule(rule, context)
        # No violations because the visual is skipped
        assert passed is True


class TestValidateReport:
    """Tests for validate_report function."""

    def test_returns_validation_result(self, tmp_path):
        """Test that validate_report returns ValidationResult with results."""
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

    def test_source_rules_only(self, tmp_path):
        """Test that source='rules' only runs expression rules."""
        report_path = tmp_path / "Test.Report"
        definition_path = report_path / "definition"
        definition_path.mkdir(parents=True)

        with patch("pbir_utils.rule_engine.load_rules") as mock_load:
            mock_load.return_value = MagicMock(
                rules=[RuleSpec(id="test_rule", expression="True", scope="report")],
                fail_on_warning=False,
            )
            with patch("pbir_utils.rule_engine.console"):
                result = validate_report(str(report_path), source="rules", strict=False)

        assert "test_rule" in result.results

    def test_fail_on_warning_raises_on_warnings(self, tmp_path):
        """Test that fail_on_warning option causes warnings to raise."""
        report_path = tmp_path / "Test.Report"
        definition_path = report_path / "definition"
        definition_path.mkdir(parents=True)

        with patch("pbir_utils.rule_engine.sanitize_powerbi_report") as mock_sanitize:
            mock_sanitize.return_value = {}
            with patch("pbir_utils.rule_engine.load_rules") as mock_load:
                mock_load.return_value = MagicMock(
                    rules=[
                        RuleSpec(
                            id="warning_rule",
                            expression="False",
                            scope="report",
                            severity="warning",
                        )
                    ],
                    fail_on_warning=True,  # Enable fail on warning
                )
                with patch("pbir_utils.rule_engine.console"):
                    with pytest.raises(ValidationError):
                        validate_report(str(report_path), strict=True)


class TestHelperFunctions:
    """Tests for expression helper functions."""

    # --- _get_path tests ---

    def test_get_path_simple(self):
        """Test basic nested access."""
        obj = {"a": {"b": {"c": 42}}}
        assert _get_path(obj, "a.b.c") == 42

    def test_get_path_with_array_index(self):
        """Test array index access."""
        obj = {"items": [{"name": "first"}, {"name": "second"}]}
        assert _get_path(obj, "items[0].name") == "first"
        assert _get_path(obj, "items[1].name") == "second"

    def test_get_path_missing_returns_default(self):
        """Test default value for missing paths."""
        obj = {"a": 1}
        assert _get_path(obj, "a.b.c", "default") == "default"
        assert _get_path(obj, "x.y.z") is None

    def test_get_path_none_object(self):
        """Test with None input."""
        assert _get_path(None, "a.b") is None
        assert _get_path(None, "a.b", "fallback") == "fallback"

    def test_get_path_array_out_of_bounds(self):
        """Test array index out of bounds."""
        obj = {"items": [{"x": 1}]}
        assert _get_path(obj, "items[5].x") is None

    # --- _has_path tests ---

    def test_has_path_exists(self):
        """Test path exists."""
        obj = {"visual": {"objects": {"fill": []}}}
        assert _has_path(obj, "visual.objects.fill") is True
        assert _has_path(obj, "visual.objects") is True

    def test_has_path_missing(self):
        """Test path does not exist."""
        obj = {"visual": {}}
        assert _has_path(obj, "visual.objects.fill") is False
        assert _has_path(obj, "nonexistent") is False

    # --- _find_all tests ---

    def test_find_all_recursive(self):
        """Test recursive search finds all matching keys."""
        obj = {"a": {"projections": [1]}, "b": {"c": {"projections": [2, 3]}}}
        result = _find_all(obj, "projections")
        assert result == [[1], [2, 3]]

    def test_find_all_in_list(self):
        """Test finds keys inside list items."""
        obj = {"items": [{"x": 1}, {"x": 2}, {"y": 3}]}
        result = _find_all(obj, "x")
        assert result == [1, 2]

    def test_find_all_no_match(self):
        """Test returns empty list when key not found."""
        obj = {"a": {"b": 1}}
        assert _find_all(obj, "nonexistent") == []

    def test_find_all_none_input(self):
        """Test handles None input gracefully."""
        assert _find_all(None, "key") == []

    # --- Integration with simpleeval ---

    def test_helpers_available_in_evaluator(self):
        """Test that helper functions are accessible in expressions."""
        context = {"data": {"visual": {"query": {"projections": [1, 2, 3]}}}}
        evaluator = _create_safe_evaluator(context)

        # Test get_path
        assert evaluator.eval("get_path(data, 'visual.query.projections')") == [1, 2, 3]

        # Test has_path
        assert evaluator.eval("has_path(data, 'visual.query')") is True
        assert evaluator.eval("has_path(data, 'visual.missing')") is False

        # Test find_all
        assert evaluator.eval("find_all(data, 'projections')") == [[1, 2, 3]]
