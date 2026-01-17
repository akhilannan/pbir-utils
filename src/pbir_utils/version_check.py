import json
import os
import sys
import time
import urllib.request
import urllib.error
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
from typing import Tuple

# Constants
PACKAGE_NAME = "pbir-utils"
PYPI_JSON_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
CACHE_DIR = Path.home() / ".pbir-utils"
CACHE_FILE = CACHE_DIR / "version_cache.json"
CHECK_INTERVAL = 24 * 60 * 60  # 24 hours in seconds


class SimpleColor:
    """Minimal ANSI color codes for terminal output."""

    BLUE = "\033[34m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    RESET = "\033[0m"


def _get_installed_version() -> str:
    """Get the currently installed version of the package."""
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        # Fallback for local dev or if package name differs
        return "0.0.0"


def _parse_version(v: str) -> Tuple[int, ...]:
    """
    Parse version string into a tuple of integers for comparison.
    Extracts purely numeric components to behave like simple semver.
    Example: '1.2.3' -> (1, 2, 3), '1.2.3rc1' -> (1, 2, 3, 1)
    """
    try:
        import re

        # Extract all sequences of digits
        parts = [int(p) for p in re.findall(r"\d+", v)]
        return tuple(parts)
    except Exception:
        return (0, 0, 0)


def _print_notice(current: str, latest: str) -> None:
    """Print the upgrade notification to stderr to avoid corrupting stdout pipes."""
    msg = (
        f"\n{SimpleColor.BLUE}[notice]{SimpleColor.RESET} A new release of {PACKAGE_NAME} is available: "
        f"{SimpleColor.RED}{current}{SimpleColor.RESET} -> {SimpleColor.GREEN}{latest}{SimpleColor.RESET}\n"
        f"{SimpleColor.BLUE}[notice]{SimpleColor.RESET} See what's new: "
        f"{SimpleColor.CYAN}https://github.com/akhilannan/pbir-utils/releases/tag/v{latest}{SimpleColor.RESET}\n"
    )
    # Print to stderr so it doesn't break pipeable commands (like pbir-utils validate --json | jq)
    print(msg, file=sys.stderr)


def check_for_updates() -> None:
    """
    Check for updates on PyPI and notify the user if a new version is available.
    Runs at most once every 24 hours.
    Fail silently on any errors to avoid disrupting the user.
    """
    # 1. Fast Exit: User opt-out
    if os.environ.get("PBIR_UTILS_NO_UPDATE_CHECK", "").lower() in ("1", "true", "yes"):
        return

    try:
        _check_update_logic()
    except (OSError, urllib.error.URLError, json.JSONDecodeError, KeyError, ValueError):
        # Fail silently on expected errors (network, permission, parsing, etc.)
        pass


def _check_update_logic() -> None:
    # 2. Setup Cache Directory
    if not CACHE_DIR.exists():
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            # If we can't create cache dir, we can't cache, so we might want to skip
            # or proceed without caching?
            # Better to just return to avoid re-checking every time if permission denied.
            return

    current_time = time.time()
    last_checked_time = 0.0
    cached_latest_version = None

    # 3. Load Cache
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                last_checked_time = data.get("last_checked", 0.0)
                cached_latest_version = data.get("latest_version")
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            # Invalid or corrupted cache file, ignore and refetch
            pass

    # Use cached version as current Source of Truth unless stale
    latest_version = cached_latest_version

    # 4. Check Validity / Stale
    is_stale = (current_time - last_checked_time) > CHECK_INTERVAL

    # If never checked (None) or stale, fetch update
    if is_stale or not latest_version:
        try:
            # Timeout set to 1 second to minimize delay
            with urllib.request.urlopen(PYPI_JSON_URL, timeout=1) as response:  # nosec B310
                if response.status == 200:
                    content = response.read().decode("utf-8")
                    data = json.loads(content)
                    real_latest_version = data["info"]["version"]

                    # Update our local var
                    latest_version = real_latest_version

                    # Write to cache
                    with open(CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump(
                            {
                                "last_checked": current_time,
                                "latest_version": latest_version,
                            },
                            f,
                        )
        except Exception:
            # If fetch fails, we stick with cached_latest_version if we had one.
            # If we didn't have one, we can't compare, so return.
            if not latest_version:
                return

    # 5. Compare Versions
    if not latest_version:
        return

    installed_version = _get_installed_version()

    # We purposefully check if installed < latest.
    # If installed >= latest, we do NOTHING.
    if _parse_version(installed_version) < _parse_version(latest_version):
        _print_notice(installed_version, latest_version)
