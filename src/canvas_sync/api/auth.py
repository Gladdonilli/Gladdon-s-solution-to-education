"""Canvas API authentication module.

Handles API token storage/retrieval via Windows Credential Manager (keyring)
and provides authenticated Canvas client instances.
"""

import keyring
from canvasapi import Canvas

from canvas_sync.config import DEFAULT_CANVAS_URL
from canvas_sync.db.models import get_config, get_db


class ConfigError(Exception):
    """Raised when required configuration is missing."""


def get_api_token(require: bool = True) -> str | None:
    """Get API token from Windows Credential Manager.

    Args:
        require: If True, raise ConfigError when token missing.
                 If False, return None when missing.

    Returns:
        API token string or None

    Raises:
        ConfigError: When token missing and require=True
    """
    token = keyring.get_password("canvas_sync", "api_token")
    if token is None and require:
        raise ConfigError("No API token configured. Run web UI first.")
    return token


def set_api_token(token: str) -> None:
    """Store API token in Windows Credential Manager.

    Args:
        token: Canvas API token to store
    """
    keyring.set_password("canvas_sync", "api_token", token)


def get_canvas_client(vault_path: str | None = None) -> Canvas:
    """Get authenticated Canvas API client.

    Args:
        vault_path: Path to vault for reading config. Uses default if None.

    Returns:
        Authenticated canvasapi.Canvas instance

    Raises:
        ConfigError: When no API token is configured
    """
    token = get_api_token(require=True)

    conn = get_db(vault_path)
    canvas_url = get_config(conn, "canvas_url") or DEFAULT_CANVAS_URL
    conn.close()

    return Canvas(canvas_url, token)
