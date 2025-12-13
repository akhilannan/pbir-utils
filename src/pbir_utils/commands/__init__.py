"""Command modules for PBIR Utils CLI."""

from . import (
    sanitize,
    extract_metadata,
    visualize,
    batch_update,
    interactions,
    measures,
    filters,
    pages,
)

# All command modules for registration
ALL_COMMANDS = [
    sanitize,
    extract_metadata,
    visualize,
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
