"""File browser API routes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..models import BrowseResponse, FileItem

router = APIRouter(prefix="/browse", tags=["browse"])


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
        raise HTTPException(status_code=403, detail="Permission denied")

    # Sort: directories first, then by name (case-insensitive)
    items.sort(key=lambda x: (not x.is_dir, x.name.lower()))

    return BrowseResponse(
        current_path=str(resolved),
        parent_path=str(resolved.parent) if resolved.parent != resolved else None,
        items=items,
    )
