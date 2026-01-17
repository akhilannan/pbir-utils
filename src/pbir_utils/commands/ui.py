"""UI command for PBIR Utils CLI."""

__all__ = ["register", "handle"]

from pathlib import Path


def register(subparsers):
    """Register the ui command."""
    parser = subparsers.add_parser(
        "ui",
        aliases=["serve"],
        help="Launch the web-based UI client",
        description="Start a local web server to browse and manage PBIR reports.",
    )
    parser.add_argument(
        "report_path",
        nargs="?",
        help="Path to auto-open (optional; detects .Report folders from CWD)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to bind to (default: 8765)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't automatically open the browser",
    )
    parser.set_defaults(func=handle)


def _resolve_initial_report(path_arg: str | None) -> str | None:
    """
    Resolve initial report path with graceful fallback.

    Returns the path if valid, or None if not found.
    Unlike resolve_report_path, this does not exit on error.
    """
    if path_arg:
        # User provided explicit path
        return path_arg

    # Check if CWD is a .Report folder
    cwd = Path.cwd()
    if cwd.name.lower().endswith(".report"):
        return str(cwd)

    return None


def handle(args):
    """Handle the ui command."""
    try:
        import uvicorn
    except ImportError:
        print("\nUI dependencies not installed.")
        print('Run: pip install "pbir-utils[ui]"')
        print('  or: uv add "pbir-utils[ui]"\n')
        return

    import webbrowser
    from urllib.parse import urlencode

    from ..api.main import app

    # Resolve initial report path (graceful, no error if not found)
    initial_report = _resolve_initial_report(args.report_path)

    # Build URL with optional initial_report query parameter
    base_url = f"http://{args.host}:{args.port}"
    if initial_report:
        url = f"{base_url}?{urlencode({'initial_report': initial_report})}"
    else:
        url = base_url

    print("\n          -- Web UI --\n")
    print(f"  Starting UI server at: {base_url}")
    if initial_report:
        print(f"  Auto-opening report: {initial_report}")
    print("  Press Ctrl+C to stop\n")

    if not args.no_browser:
        webbrowser.open(url)

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
