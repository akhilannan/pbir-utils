"""Command modules for PBIR Utils CLI."""

__all__ = ["register_all", "ALL_COMMANDS"]

from . import (
    sanitize,
    extract_metadata,
    visualize,
    batch_update,
    interactions,
    measures,
    filters,
    pages,
    ui,
    validate,
)

# All command modules for registration
ALL_COMMANDS = [
    ui,
    sanitize,
    validate,
    visualize,
    extract_metadata,
    batch_update,
    interactions,
    measures,
    filters,
    pages,
]


def register_all(subparsers):
    """Register all command modules with the given subparsers."""
    for module in ALL_COMMANDS:
        module.register(subparsers)
