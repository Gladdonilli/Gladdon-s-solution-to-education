"""Canvas Sync - Sync Canvas LMS data to Obsidian markdown notes."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("canvas-sync")
except PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback for development
