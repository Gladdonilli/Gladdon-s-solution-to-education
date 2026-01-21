"""Configuration constants for Canvas Sync.

This module contains ONLY constants - no database access.
All config values that need DB access live in db/models.py.
"""

from pathlib import Path

# Default vault path - relative to project root
DEFAULT_VAULT_PATH = Path(__file__).parent.parent.parent.parent / "Project-obsidian-vault"

# Default daily sync time (24-hour format)
DEFAULT_SYNC_TIME = "06:00"

# Default Canvas instance URL
DEFAULT_CANVAS_URL = "https://canvas.illinois.edu"
