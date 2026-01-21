"""Tests for project structure and package imports."""

import pytest


def test_package_has_version():
    """Test that canvas_sync package exposes __version__."""
    from canvas_sync import __version__
    
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_config_module_exists():
    """Test that config module with constants exists."""
    from canvas_sync.config import (
        DEFAULT_VAULT_PATH,
        DEFAULT_SYNC_TIME,
        DEFAULT_CANVAS_URL,
    )
    
    assert DEFAULT_VAULT_PATH is not None
    assert DEFAULT_SYNC_TIME == "06:00"
    assert DEFAULT_CANVAS_URL == "https://canvas.illinois.edu"


def test_db_models_import():
    """Test that db.models module can be imported with required functions."""
    from canvas_sync.db.models import (
        init_db,
        get_db,
        get_config,
        set_config,
        get_vault_path_from_config,
        get_sync_time_from_config,
    )
    
    # Verify they are callable
    assert callable(init_db)
    assert callable(get_db)
    assert callable(get_config)
    assert callable(set_config)
    assert callable(get_vault_path_from_config)
    assert callable(get_sync_time_from_config)


def test_db_creates_tables(tmp_path):
    """Test that init_db creates database with required tables."""
    from canvas_sync.db.models import init_db
    
    vault_path = str(tmp_path / "test_vault")
    conn = init_db(vault_path)
    
    # Check tables exist
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    
    assert "sync_state" in tables
    assert "selected_courses" in tables
    assert "config" in tables
    
    conn.close()


def test_config_get_set(tmp_path):
    """Test config get/set operations."""
    from canvas_sync.db.models import init_db, get_config, set_config
    
    vault_path = str(tmp_path / "test_vault")
    conn = init_db(vault_path)
    
    # Initially empty
    assert get_config(conn, "test_key") is None
    
    # Set and get
    set_config(conn, "test_key", "test_value")
    assert get_config(conn, "test_key") == "test_value"
    
    # Update existing
    set_config(conn, "test_key", "new_value")
    assert get_config(conn, "test_key") == "new_value"
    
    conn.close()


def test_subpackages_exist():
    """Test that required subpackages exist."""
    import canvas_sync.api
    import canvas_sync.sync
    import canvas_sync.web
    import canvas_sync.db
    
    # Just verify they import without error
    assert True
