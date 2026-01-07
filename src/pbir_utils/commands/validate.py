"""Validate command for PBIR Utils CLI."""

__all__ = ["register", "handle"]

import argparse
import json
import sys
import textwrap

from ..rule_config import get_default_rules_path, _load_yaml


def register(subparsers):
    """Register the validate command."""
    # Build description dynamically from defaults/rules.yaml
    default_rules_path = get_default_rules_path()
    if default_rules_path.exists():
        default_config = _load_yaml(default_rules_path)
    else:
        default_config = {}

    # Get default rule IDs
    default_rule_ids = default_config.get("rules", [])

    # Build dynamic description
    rules_list = "\n".join(f"          - {rule_id}" for rule_id in default_rule_ids)

    validate_desc = f"""
        Validate a Power BI report against configurable rules.
        
        Rules can be:
        - Sanitizer-based: Check if a sanitize action would make changes
        - Expression-based: Evaluate conditions on report structure
        
        Default Rules:
{rules_list}
        
        Severity Levels:
          - error: Critical issues (fails in strict mode)
          - warning: Important issues (configurable via fail_on_warning)
          - info: Recommendations only
        
        Configuration:
          Create a 'pbir-rules.yaml' in your project to customize rules.
          Or use --config to specify a custom config file path.
    """

    validate_epilog = textwrap.dedent(
        r"""
        Examples:
          # Validate with default rules
          pbir-utils validate "C:\Reports\MyReport.Report"
          
          # Validate with specific rules only
          pbir-utils validate "C:\Reports\MyReport.Report" --rules remove_unused_bookmarks reduce_pages
          
          # Filter by minimum severity
          pbir-utils validate "C:\Reports\MyReport.Report" --severity warning
          
          # Strict mode for CI/CD (exit 1 on violations)
          pbir-utils validate "C:\Reports\MyReport.Report" --strict
          
          # JSON output for scripting
          pbir-utils validate "C:\Reports\MyReport.Report" --format json
          
          # Use a custom config file
          pbir-utils validate "C:\Reports\MyReport.Report" --config pbir-rules.yaml
    """
    )

    parser = subparsers.add_parser(
        "validate",
        help="Validate a Power BI report against rules",
        description=validate_desc,
        epilog=validate_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to the Power BI report folder (optional if inside a .Report folder)",
    )
    parser.add_argument(
        "--rules",
        nargs="+",
        metavar="RULE",
        help="Specific rule IDs to run (default: all rules from config)",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to a custom rules config YAML file.",
    )
    parser.add_argument(
        "--sanitize-config",
        metavar="PATH",
        help="Path to a custom sanitize config YAML file (default: auto-discovered).",
    )
    parser.add_argument(
        "--severity",
        choices=["info", "warning", "error"],
        help="Minimum severity to report (default: info - all rules)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any violations found (respects fail_on_warning option)",
    )
    parser.add_argument(
        "--format",
        choices=["console", "json"],
        default="console",
        help="Output format (default: console)",
    )
    parser.set_defaults(func=handle)


def handle(args):
    """Handle the validate command."""
    # Lazy imports
    from ..common import resolve_report_path
    from ..rule_engine import validate_report, ValidationError
    from ..console_utils import console

    report_path = resolve_report_path(args.report_path)

    try:
        if args.format == "json":
            # Suppress console output for JSON mode
            with console.suppress_all():
                result = validate_report(
                    report_path,
                    rules=args.rules,
                    config=args.config,
                    sanitize_config=getattr(args, "sanitize_config", None),
                    severity=args.severity,
                    strict=args.strict,
                )
            # Output as JSON
            output = {
                "results": result.results,
                "summary": {
                    "passed": result.passed,
                    "failed": result.failed,
                    "errors": result.error_count,
                    "warnings": result.warning_count,
                    "info": result.info_count,
                },
                "violations": result.violations,
            }
            print(json.dumps(output, indent=2))
        else:
            # Console mode
            results = validate_report(
                report_path,
                rules=args.rules,
                config=args.config,
                sanitize_config=getattr(args, "sanitize_config", None),
                severity=args.severity,
                strict=args.strict,
            )

    except ValidationError as e:
        if args.format == "json":
            output = {
                "error": str(e),
                "violations": e.violations,
            }
            print(json.dumps(output, indent=2))
        else:
            console.print_error(f"\n{str(e)}")
        sys.exit(1)
