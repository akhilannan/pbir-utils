"""
Rule engine for validating Power BI reports.

Provides expression-based and sanitizer-based rule evaluation.
"""

import logging
import re  # Added for regex support in rules
from pathlib import Path

from .common import load_json, iter_pages, iter_visuals
from .console_utils import console
from .rule_config import RuleSpec, load_rules
from .pbir_report_sanitizer import sanitize_powerbi_report, get_available_actions

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails in strict mode."""

    def __init__(self, message: str, violations: list[dict]):
        super().__init__(message)
        self.violations = violations


class ValidationResult:
    """Result of validate_report with statistics."""

    def __init__(self, results: dict[str, bool], violations: list[dict]):
        self.results = results
        self.violations = violations
        self.passed = sum(1 for v in results.values() if v)
        self.failed = len(results) - self.passed
        self.error_count = sum(1 for v in violations if v.get("severity") == "error")
        self.warning_count = sum(
            1 for v in violations if v.get("severity") == "warning"
        )
        self.info_count = sum(1 for v in violations if v.get("severity") == "info")

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0

    @property
    def has_warnings(self) -> bool:
        return self.warning_count > 0

    def __repr__(self) -> str:
        return (
            f"{self.passed} passed, {self.error_count} errors, "
            f"{self.warning_count} warnings, {self.info_count} info"
        )


def load_pbir_context(report_path: str) -> dict:
    """
    Load entire PBIR report into a structured object for rule evaluation.

    Returns dict with: report, reportExtensions, version, pages (with visuals),
    bookmarks, customTheme, baseTheme.
    """
    report_dir = Path(report_path)
    definition_dir = report_dir / "definition"

    context = {
        "report": {},
        "reportExtensions": {},
        "version": {},
        "pages": [],
        "bookmarks": [],
        "customTheme": {},
        "baseTheme": {},
    }

    # Load report.json
    report_json = definition_dir / "report.json"
    if report_json.exists():
        context["report"] = load_json(report_json)

    # Load reportExtensions.json (measures)
    extensions_json = definition_dir / "reportExtensions.json"
    if extensions_json.exists():
        context["reportExtensions"] = load_json(extensions_json)

    # Load version.json
    version_json = definition_dir / "version.json"
    if version_json.exists():
        context["version"] = load_json(version_json)

    # Load pages with nested visuals
    pages = []
    for page_id, page_folder, page_data in iter_pages(report_path):
        page_entry = {
            "name": page_id,
            **page_data,
            "visuals": [],
        }

        # Load visuals for this page
        for visual_id, visual_folder, visual_data in iter_visuals(page_folder):
            visual_entry = {
                "name": visual_id,
                **visual_data,
            }
            page_entry["visuals"].append(visual_entry)

        pages.append(page_entry)

    context["pages"] = pages

    # Load bookmarks
    bookmarks_dir = definition_dir / "bookmarks"
    bookmarks_meta = bookmarks_dir / "bookmarks.json"
    if bookmarks_meta.exists():
        bookmarks_data = load_json(bookmarks_meta)
        bookmarks = []
        for item in bookmarks_data.get("items", []):
            bookmark_name = item.get("name")
            bookmark_file = bookmarks_dir / f"{bookmark_name}.bookmark.json"
            if bookmark_file.exists():
                bookmark_data = load_json(bookmark_file)
                bookmarks.append(bookmark_data)
        context["bookmarks"] = bookmarks

    # Load themes (optional)
    static_resources = report_dir / "StaticResources"
    registered_resources = static_resources / "RegisteredResources"
    if registered_resources.exists():
        for theme_file in registered_resources.glob("*.json"):
            context["customTheme"] = load_json(theme_file)
            break  # Take first custom theme

    shared_resources = static_resources / "SharedResources" / "BaseThemes"
    if shared_resources.exists():
        for theme_file in shared_resources.glob("*.json"):
            context["baseTheme"] = load_json(theme_file)
            break  # Take first base theme

    return context


def _evaluate_sanitizer_rule(
    rule: RuleSpec,
    report_path: str,
    available_actions: dict,
) -> tuple[bool, list[dict]]:
    """
    Evaluate sanitizer-based rule by checking if action would make changes.

    Returns:
        (passed: bool, violations: list[dict])
    """

    # Run sanitizer in dry-run mode, capturing steps
    captured_messages = []
    with console.capture_output() as queue:
        with console.suppress_all():
            results = sanitize_powerbi_report(
                report_path,
                actions=[rule.id],
                dry_run=True,
            )

        # Collect captured step messages
        while not queue.empty():
            msg = queue.get_nowait()
            # Capture 'step' messages (details) and 'dry_run' (summary)
            if msg.get("type") == "step" or (
                msg.get("type") == "dry_run" and msg.get("message")
            ):
                captured_messages.append(msg.get("message"))

    # If the action would make changes, rule fails
    would_change = results.get(rule.id, False)
    if would_change:
        violations = []
        if captured_messages:
            for msg in captured_messages:
                # Filter out generic start/end messages if they exist, or just use all
                if "Running action" in msg or "Action completed" in msg:
                    continue
                violations.append({"message": msg})

        # Fallback if no specific steps captured
        if not violations:
            violations.append(
                {
                    "message": rule.description
                    or f"{rule.display_name} would make changes"
                }
            )

        return False, violations

    return True, []


def _get_path(obj, path: str, default=None):
    """
    Navigate nested dict/list using dot notation with optional array indexing.

    Examples:
        _get_path({"a": {"b": 1}}, "a.b") -> 1
        _get_path({"items": [{"x": 10}]}, "items[0].x") -> 10
        _get_path({}, "a.b.c", "default") -> "default"
    """
    if obj is None:
        return default

    current = obj
    # Split by dots, but handle array indices like "items[0]"
    parts = path.replace("]", "").replace("[", ".").split(".")

    for part in parts:
        if not part:
            continue
        try:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                current = current[idx] if 0 <= idx < len(current) else None
            else:
                return default
        except (KeyError, IndexError, TypeError):
            return default

        if current is None:
            return default

    return current


def _has_path(obj, path: str) -> bool:
    """
    Check if a nested path exists in the object.

    Returns True if path resolves to a non-None value.
    """
    sentinel = object()
    return _get_path(obj, path, sentinel) is not sentinel


def _find_all(obj, key: str) -> list:
    """
    Recursively find all values for a given key name.

    Similar to JsonPath's $..key syntax.

    Examples:
        _find_all({"a": {"x": 1}, "b": {"x": 2}}, "x") -> [1, 2]
        _find_all({"items": [{"x": 1}, {"x": 2}]}, "x") -> [1, 2]
    """
    results = []

    def _recurse(data):
        if isinstance(data, dict):
            for k, v in data.items():
                if k == key:
                    results.append(v)
                _recurse(v)
        elif isinstance(data, list):
            for item in data:
                _recurse(item)

    _recurse(obj)
    return results


def _create_safe_evaluator(context: dict):
    """
    Create a simpleeval evaluator with safe functions and context.

    Uses simpleeval instead of Python's eval() for security:
    - Parses expressions into AST, never executes arbitrary code
    - Strict whitelist of operations and functions
    - Safe for CI/CD pipelines where config may come from PRs
    """
    from simpleeval import EvalWithCompoundTypes

    # Create evaluator with compound type support (lists, dicts)
    evaluator = EvalWithCompoundTypes()

    # Add safe functions
    evaluator.functions = {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "sum": sum,
        "min": min,
        "max": max,
        "any": any,
        "all": all,
        "abs": abs,
        "round": round,
        "sorted": sorted,
        "reversed": lambda x: list(reversed(x)),
        # Regex support via re module functions
        "re_match": lambda pattern, string: (
            bool(re.match(pattern, string)) if string else False
        ),
        "re_search": lambda pattern, string: (
            bool(re.search(pattern, string)) if string else False
        ),
        # JSON traversal helpers
        "get_path": _get_path,
        "has_path": _has_path,
        "find_all": _find_all,
    }

    # Add context as names (variables available in expressions)
    evaluator.names = context

    return evaluator


def _safe_eval(expression: str, context: dict):
    """
    Safely evaluate an expression using simpleeval.

    Args:
        expression: The expression string to evaluate
        context: Dict of variables available in the expression

    Returns:
        The result of evaluating the expression
    """
    evaluator = _create_safe_evaluator(context)
    return evaluator.eval(expression.strip())


def _evaluate_expression_rule(
    rule: RuleSpec,
    pbir_context: dict,
) -> tuple[bool, list[dict]]:
    """
    Evaluate expression-based rule using simpleeval (safe, no code execution).

    Returns:
        (passed: bool, violations: list of violation dicts)
    """
    violations = []

    # Build base context with params
    base_context = {
        **pbir_context,
        **rule.params,
        "True": True,
        "False": False,
        "None": None,
    }

    if rule.scope == "report":
        # Evaluate once for entire report
        try:
            result = _safe_eval(rule.expression, base_context)
            if not result:
                violations.append(
                    {
                        "message": rule.description or f"{rule.display_name} failed",
                    }
                )
        except Exception as e:
            violations.append({"message": f"Expression error: {e}"})

    elif rule.scope == "page":
        # Evaluate per page
        for page in pbir_context.get("pages", []):
            page_context = {**base_context, "page": page}
            try:
                result = _safe_eval(rule.expression, page_context)
                if not result:
                    page_name = page.get("displayName", page.get("name", "Unknown"))
                    violations.append(
                        {
                            "message": rule.description
                            or f"{rule.display_name} failed",
                            "page_name": page_name,
                        }
                    )
            except Exception as e:
                violations.append({"message": f"Expression error on page: {e}"})

    elif rule.scope == "visual":
        # Evaluate per visual (iterate all pages and visuals)
        for page in pbir_context.get("pages", []):
            page_name = page.get("displayName", page.get("name", "Unknown"))
            for visual in page.get("visuals", []):
                visual_context = {**base_context, "visual": visual, "page": page}
                try:
                    result = _safe_eval(rule.expression, visual_context)
                    if not result:
                        visual_type = visual.get("visual", {}).get(
                            "visualType", "unknown"
                        )
                        visual_name = visual.get("name", "unknown")
                        violations.append(
                            {
                                "message": rule.description
                                or f"{rule.display_name} failed",
                                "page_name": page_name,
                                "visual_name": visual_name,
                                "visual_type": visual_type,
                            }
                        )
                except Exception as e:
                    # Skip visuals that don't match expression structure
                    logger.debug(
                        "Skipping visual %s: %s", visual.get("name", "unknown"), e
                    )

    elif rule.scope == "measure":
        # Evaluate per measure (iterate entities -> measures)
        entities = pbir_context.get("reportExtensions", {}).get("entities", [])
        for entity in entities:
            entity_name = entity.get("name", "Unknown")
            for measure in entity.get("measures", []):
                measure_context = {
                    **base_context,
                    "measure": measure,
                    "entity": entity,
                }
                try:
                    result = _safe_eval(rule.expression, measure_context)
                    if not result:
                        measure_name = measure.get("name", "unknown")
                        violations.append(
                            {
                                "message": rule.description
                                or f"{rule.display_name} failed",
                                "measure_name": measure_name,
                                "entity_name": entity_name,
                            }
                        )
                except Exception as e:
                    # Skip measures that don't match expression structure
                    logger.debug(
                        "Skipping measure %s: %s", measure.get("name", "unknown"), e
                    )

    elif rule.scope == "bookmark":
        # Evaluate per bookmark
        for bookmark in pbir_context.get("bookmarks", []):
            bookmark_context = {**base_context, "bookmark": bookmark}
            try:
                result = _safe_eval(rule.expression, bookmark_context)
                if not result:
                    bookmark_name = bookmark.get("name", "unknown")
                    violations.append(
                        {
                            "message": rule.description
                            or f"{rule.display_name} failed",
                            "bookmark_name": bookmark_name,
                        }
                    )
            except Exception as e:
                # Skip bookmarks that don't match expression structure
                logger.debug(
                    "Skipping bookmark %s: %s", bookmark.get("name", "unknown"), e
                )

    passed = len(violations) == 0
    return passed, violations


def validate_report(
    report_path: str,
    *,
    # Source filtering
    source: str = "all",  # "all", "sanitizer", "rules"
    # Cherry-pick specific items
    actions: list[str] | None = None,  # Sanitizer action IDs
    rules: list[str] | None = None,  # Expression rule IDs
    # Config paths
    sanitize_config: str | Path | None = None,
    rules_config: str | Path | None = None,
    # Output filtering
    severity: str | None = None,
    strict: bool = True,
) -> ValidationResult:
    """
    Validate a Power BI report by running sanitizer checks and/or expression rules.

    Args:
        report_path: Path to the report folder.
        source: Which checks to run - "all" (default), "sanitizer", or "rules".
        actions: Specific sanitizer action IDs to check.
        rules: Specific expression rule IDs to run.
        sanitize_config: Custom sanitize config path (default: auto-discovered).
        rules_config: Custom rules config path (default: auto-discovered).
        severity: Minimum severity to check ("info", "warning", "error").
        strict: If True (default), raise exception on error violations.

    Returns:
        ValidationResult with .passed, .failed, .error_count, .warning_count,
        .info_count, .results (dict), and .violations (list).

    Raises:
        ValidationError: If strict=True and any error violations found
                        (or warnings if fail_on_warning option is set).
    """
    from .sanitize_config import load_config as load_sanitize_config
    from .rule_config import RuleSpec

    severity_order = {"info": 0, "warning": 1, "error": 2}

    results: dict[str, bool] = {}
    all_violations: list[dict] = []
    fail_on_warning = False

    report_name = Path(report_path).name
    console.print_heading(f"Validating {report_name}")

    # ========================================
    # Run sanitizer checks if source includes them
    # ========================================
    if source in ("all", "sanitizer"):
        # Load sanitize config
        san_cfg = load_sanitize_config(
            config_path=sanitize_config, report_path=report_path
        )

        # Determine which actions to check
        if actions:
            # Cherry-pick specific actions
            action_specs = [
                san_cfg.definitions.get(a) for a in actions if a in san_cfg.definitions
            ]
        else:
            # Use all active actions from config
            action_specs = san_cfg.actions

        # Filter by severity
        if severity:
            min_severity = severity_order.get(severity, 0)
            action_specs = [
                a
                for a in action_specs
                if a and severity_order.get(a.severity, 0) >= min_severity
            ]

        # Get available sanitizer actions
        available_actions = get_available_actions()

        # Run each sanitizer action as a check
        if action_specs:
            console.print("\n[Sanitizer Checks]")
            for action in action_specs:
                if action is None:
                    continue
                # Create a RuleSpec from ActionSpec for evaluation
                rule = RuleSpec(
                    id=action.id,
                    description=action.description,
                    severity=action.severity,
                )
                passed, violations = _evaluate_sanitizer_rule(
                    rule, report_path, available_actions
                )
                results[action.id] = passed

                if passed:
                    _print_rule_result(rule, True)
                else:
                    _print_rule_result(rule, False, violations)
                    for v in violations:
                        all_violations.append(
                            {
                                "rule_id": action.id,
                                "rule_name": action.display_name,
                                "severity": action.severity,
                                **v,
                            }
                        )

    # ========================================
    # Run expression rules if source includes them
    # ========================================
    if source in ("all", "rules"):
        # Load rules config
        rules_cfg = load_rules(config_path=rules_config, report_path=report_path)
        fail_on_warning = rules_cfg.fail_on_warning

        # Determine which rules to run
        if rules:
            # Cherry-pick specific rules
            rule_specs = [r for r in rules_cfg.rules if r.id in rules]
        else:
            # Use all rules from config
            rule_specs = rules_cfg.rules

        # Filter by severity
        if severity:
            min_severity = severity_order.get(severity, 0)
            rule_specs = [
                r
                for r in rule_specs
                if severity_order.get(r.severity, 0) >= min_severity
            ]

        # Load PBIR context for expression rules
        pbir_context = load_pbir_context(report_path)

        # Run each expression rule
        if rule_specs:
            console.print("\n[Expression Rules]")
            for rule in rule_specs:
                passed, violations = _evaluate_expression_rule(rule, pbir_context)
                results[rule.id] = passed

                if passed:
                    _print_rule_result(rule, True)
                else:
                    _print_rule_result(rule, False, violations)
                    for v in violations:
                        all_violations.append(
                            {
                                "rule_id": rule.id,
                                "rule_name": rule.display_name,
                                "severity": rule.severity,
                                **v,
                            }
                        )

    # Print summary
    _print_summary(results, all_violations)

    # Handle strict mode
    if strict and all_violations:
        # Check if any violations should cause failure
        fail_severities = {"error"}
        if fail_on_warning:
            fail_severities.add("warning")

        failing_violations = [
            v for v in all_violations if v.get("severity") in fail_severities
        ]

        if failing_violations:
            raise ValidationError(
                f"Validation failed with {len(failing_violations)} violation(s)",
                failing_violations,
            )

    return ValidationResult(results, all_violations)


def _print_rule_result(
    rule: RuleSpec, passed: bool, violations: list[dict] | None = None
):
    """Print formatted rule result."""
    if passed:
        # Green [PASS] badge - use console for SSE broadcast
        badge = console._format("[PASS]", console.GREEN, console.BOLD)
        console.print(f"{badge} {rule.display_name}")
    else:
        # Colored badge based on severity
        severity_upper = rule.severity.upper()
        if rule.severity == "error":
            badge = console._format(f"[{severity_upper}]", console.RED, console.BOLD)
        elif rule.severity == "warning":
            badge = console._format(f"[{severity_upper}]", console.YELLOW, console.BOLD)
        else:
            badge = console._format(f"[{severity_upper}]", console.BLUE, console.BOLD)
        console.print(f"{badge} {rule.display_name}")

        # Print violation details (indented) - only if they add new information
        if violations:
            for v in violations[:3]:  # Limit to 3 examples
                detail = v.get("message", "")
                # Build detail string from visual/page/measure/bookmark info
                parts = []
                if "page_name" in v:
                    parts.append(f"Page: {v['page_name']}")
                if "visual_name" in v:
                    parts.append(f"Visual: {v['visual_name']}")
                if "measure_name" in v:
                    parts.append(f"Measure: {v['measure_name']}")
                if "entity_name" in v:
                    parts.append(f"Entity: {v['entity_name']}")
                if "bookmark_name" in v:
                    parts.append(f"Bookmark: {v['bookmark_name']}")

                # Only show detail if it adds new info (not same as display name)
                if parts:
                    console.print(f"    └─ {', '.join(parts)}")
                elif detail and detail != rule.display_name:
                    console.print(f"    └─ {detail}")
            if len(violations) > 3:
                console.print(f"    └─ ... and {len(violations) - 3} more")


def _print_summary(results: dict[str, bool], violations: list[dict]):
    """Print validation summary."""
    passed = sum(1 for v in results.values() if v)
    failed = len(results) - passed

    # Count by severity
    error_count = sum(1 for v in violations if v.get("severity") == "error")
    warning_count = sum(1 for v in violations if v.get("severity") == "warning")
    info_count = sum(1 for v in violations if v.get("severity") == "info")

    print()
    console.print("━" * 50)
    if failed == 0:
        console.print_success(f"Validation complete: All {passed} rules passed")
    else:
        parts = []
        if error_count:
            parts.append(f"{error_count} error(s)")
        if warning_count:
            parts.append(f"{warning_count} warning(s)")
        if info_count:
            parts.append(f"{info_count} info")
        summary_text = ", ".join(parts) if parts else f"{failed} failed"
        console.print(f"Validation complete: {passed} passed, {summary_text}")
    console.print("━" * 50)
