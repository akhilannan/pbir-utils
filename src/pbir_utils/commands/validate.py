"""Validate command for PBIR Utils CLI."""

__all__ = ["register", "handle"]

import argparse
import json
import sys
import textwrap


def register(subparsers):
    """Register the validate command."""
    validate_desc = """
        Validate a Power BI report against configurable checks.
        
        By default, runs BOTH:
        - Sanitizer checks: Verify sanitize actions wouldn't make changes
        - Expression rules: Evaluate conditions on report structure
        
        Use --source to run only sanitizer checks or only expression rules.
        
        Severity Levels:
          - error: Critical issues (fails in strict mode)
          - warning: Important issues (configurable via fail_on_warning)
          - info: Recommendations only
        
        Configuration:
          Create 'pbir-sanitize.yaml' and/or 'pbir-rules.yaml' in your project
          to customize checks. Or use --sanitize-config / --rules-config to 
          specify custom config file paths.
    """

    validate_epilog = textwrap.dedent(
        r"""
        Examples:
          # Validate with all checks (default)
          pbir-utils validate "C:\Reports\MyReport.Report"
          
          # Run only sanitizer checks
          pbir-utils validate "C:\Reports\MyReport.Report" --source sanitize
          
          # Run only expression rules
          pbir-utils validate "C:\Reports\MyReport.Report" --source rules
          
          # Run specific sanitizer actions only
          pbir-utils validate "C:\Reports\MyReport.Report" --actions remove_unused_measures cleanup_invalid_bookmarks
          
          # Run specific expression rules only
          pbir-utils validate "C:\Reports\MyReport.Report" --rules reduce_pages reduce_visuals_on_page
          
          # Filter by minimum severity
          pbir-utils validate "C:\Reports\MyReport.Report" --severity warning
          
          # Strict mode for CI/CD (exit 1 on violations)
          pbir-utils validate "C:\Reports\MyReport.Report" --strict
          
          # JSON output for scripting
          pbir-utils validate "C:\Reports\MyReport.Report" --format json
          
          # Use custom config files
          pbir-utils validate "C:\Reports\MyReport.Report" --sanitize-config my-sanitize.yaml
          pbir-utils validate "C:\Reports\MyReport.Report" --rules-config my-rules.yaml
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
        "--source",
        choices=["all", "sanitize", "rules"],
        default="all",
        help="Which checks to run: 'all' (default), 'sanitize' only, or 'rules' only",
    )
    parser.add_argument(
        "--actions",
        nargs="+",
        metavar="ACTION",
        help="Specific sanitizer action IDs to check (from pbir-sanitize.yaml)",
    )
    parser.add_argument(
        "--rules",
        nargs="+",
        metavar="RULE",
        help="Specific expression rule IDs to run (from pbir-rules.yaml)",
    )
    parser.add_argument(
        "--sanitize-config",
        metavar="PATH",
        help="Path to a custom sanitize config YAML file (default: auto-discovered).",
    )
    parser.add_argument(
        "--rules-config",
        metavar="PATH",
        help="Path to a custom rules config YAML file (default: auto-discovered).",
    )
    parser.add_argument(
        "--severity",
        choices=["info", "warning", "error"],
        help="Minimum severity to report (default: info - all checks)",
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
                    source=args.source,
                    actions=args.actions,
                    rules=args.rules,
                    sanitize_config=getattr(args, "sanitize_config", None),
                    rules_config=getattr(args, "rules_config", None),
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
            # Console mode - function prints output directly
            validate_report(
                report_path,
                source=args.source,
                actions=args.actions,
                rules=args.rules,
                sanitize_config=getattr(args, "sanitize_config", None),
                rules_config=getattr(args, "rules_config", None),
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
