"""PBIR Utilities CLI - A tool for managing Power BI Enhanced Report Format (PBIR) projects."""

import argparse
from importlib.metadata import version

from .commands import register_all
from .version_check import check_for_updates


def main():
    """Main entry point for the CLI."""
    # Check for updates before doing anything else
    check_for_updates()

    parser = argparse.ArgumentParser(
        description="PBIR Utilities CLI - A tool for managing Power BI Enhanced Report Format (PBIR) projects.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('pbir-utils')}",
    )
    print(
        r"""
    ____  ____  ____  ____           __  ____  _ __
   / __ \/ __ )/  _/ / __ \         / / / / /_(_) /____
  / /_/ / __  |/ /  / /_/ /_____   / / / / __/ / / ___/
 / ____/ /_/ // /  / _, _/_____/  / /_/ / /_/ / (__  )
/_/   /_____/___/ /_/ |_|         \____/\__/_/_/____/ 
                                                       
          -- Power BI PBIR Utilities --
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Register all command modules
    register_all(subparsers)

    args = parser.parse_args()

    # Dispatch to the appropriate handler
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
