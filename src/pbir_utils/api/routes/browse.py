"""File browser API routes."""

import logging
import platform
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..models import BrowseResponse, FileItem

router = APIRouter(prefix="/browse", tags=["browse"])
logger = logging.getLogger(__name__)

# Exclusion patterns for sensitive directories
# These paths are blocked from browsing for security
EXCLUDED_PATHS: dict[str, list[str]] = {
    "windows": [
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\ProgramData",
        "C:\\$Recycle.Bin",
        "C:\\Recovery",
        "C:\\System Volume Information",
    ],
    "linux": [
        "/etc",
        "/bin",
        "/sbin",
        "/usr/bin",
        "/usr/sbin",
        "/var",
        "/root",
        "/boot",
        "/sys",
        "/proc",
    ],
    "darwin": [  # macOS
        "/System",
        "/Library",
        "/private",
        "/sbin",
        "/usr/sbin",
    ],
}


def _is_path_excluded(resolved: Path) -> bool:
    """Check if path is in the exclusion list."""
    system = platform.system().lower()
    excluded = EXCLUDED_PATHS.get(system, [])

    resolved_str = str(resolved)
    for excluded_path in excluded:
        # Case-insensitive on Windows
        if system == "windows":
            if resolved_str.lower().startswith(excluded_path.lower()):
                logger.warning("Access denied to excluded path: %s", resolved)
                return True
        else:
            if resolved_str.startswith(excluded_path):
                logger.warning("Access denied to excluded path: %s", resolved)
                return True
    return False


@router.get("", response_model=BrowseResponse)
async def browse_directory(path: str = None):
    """
    Browse the file system to find .Report folders.

    Args:
        path: Directory path to browse. Defaults to user's home directory.

    Returns:
        BrowseResponse with current path, parent path, and list of items.
    """
    if path:
        resolved = Path(path).resolve()
        if not resolved.exists():
            raise HTTPException(status_code=404, detail="Path not found")
        if not resolved.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")
        if _is_path_excluded(resolved):
            raise HTTPException(
                status_code=403, detail="Access to this path is restricted"
            )
        logger.info("Browsing directory: %s", resolved)
    else:
        # Default to user's home directory
        resolved = Path.home()

    items: list[FileItem] = []
    try:
        for item in resolved.iterdir():
            try:
                # Skip hidden files/folders
                if item.name.startswith("."):
                    continue
                # Check is_dir - may raise PermissionError on protected folders
                item_is_dir = item.is_dir()
                is_report = item.name.endswith(".Report") and item_is_dir
                items.append(
                    FileItem(
                        name=item.name,
                        path=str(item),
                        is_dir=item_is_dir,
                        is_report=is_report,
                    )
                )
            except PermissionError:
                # Skip items we can't access
                continue
    except PermissionError:
        logger.error("Permission denied accessing: %s", resolved)
        raise HTTPException(
            status_code=403, detail=f"Permission denied accessing: {resolved}"
        )

    # Sort: directories first, then by name (case-insensitive)
    items.sort(key=lambda x: (not x.is_dir, x.name.lower()))

    return BrowseResponse(
        current_path=str(resolved),
        parent_path=str(resolved.parent) if resolved.parent != resolved else None,
        items=items,
    )
