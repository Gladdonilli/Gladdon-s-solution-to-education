"""Tests for Canvas API authentication module."""

import pytest
from unittest.mock import patch, MagicMock


class TestGetApiToken:
    """Tests for get_api_token function."""

    def test_returns_token_when_exists(self):
        """Token is returned when stored in keyring."""
        with patch("canvas_sync.api.auth.keyring") as mock_keyring:
            mock_keyring.get_password.return_value = "test-token-123"
            
            from canvas_sync.api.auth import get_api_token
            
            token = get_api_token()
            assert token == "test-token-123"
            mock_keyring.get_password.assert_called_once_with("canvas_sync", "api_token")

    def test_raises_when_missing_and_required(self):
        """ConfigError raised when token missing and require=True."""
        with patch("canvas_sync.api.auth.keyring") as mock_keyring:
            mock_keyring.get_password.return_value = None
            
            from canvas_sync.api.auth import get_api_token, ConfigError
            
            with pytest.raises(ConfigError, match="No API token configured"):
                get_api_token(require=True)

    def test_returns_none_when_missing_and_not_required(self):
        """None returned when token missing and require=False."""
        with patch("canvas_sync.api.auth.keyring") as mock_keyring:
            mock_keyring.get_password.return_value = None
            
            from canvas_sync.api.auth import get_api_token
            
            token = get_api_token(require=False)
            assert token is None


class TestSetApiToken:
    """Tests for set_api_token function."""

    def test_stores_token_in_keyring(self):
        """Token is stored in keyring."""
        with patch("canvas_sync.api.auth.keyring") as mock_keyring:
            from canvas_sync.api.auth import set_api_token
            
            set_api_token("new-token-456")
            mock_keyring.set_password.assert_called_once_with(
                "canvas_sync", "api_token", "new-token-456"
            )


class TestGetCanvasClient:
    """Tests for get_canvas_client function."""

    def test_returns_canvas_instance(self, tmp_path):
        """Returns authenticated Canvas client."""
        with patch("canvas_sync.api.auth.keyring") as mock_keyring:
            with patch("canvas_sync.api.auth.Canvas") as mock_canvas_class:
                mock_keyring.get_password.return_value = "test-token"
                mock_canvas_instance = MagicMock()
                mock_canvas_class.return_value = mock_canvas_instance
                
                from canvas_sync.api.auth import get_canvas_client
                from canvas_sync.db.models import get_db, set_config
                
                conn = get_db(str(tmp_path))
                set_config(conn, "canvas_url", "https://test.instructure.com")
                conn.close()
                
                client = get_canvas_client(str(tmp_path))
                
                assert client == mock_canvas_instance
                mock_canvas_class.assert_called_once_with(
                    "https://test.instructure.com", "test-token"
                )

    def test_uses_default_url_when_not_configured(self, tmp_path):
        """Uses DEFAULT_CANVAS_URL when not in config."""
        with patch("canvas_sync.api.auth.keyring") as mock_keyring:
            with patch("canvas_sync.api.auth.Canvas") as mock_canvas_class:
                mock_keyring.get_password.return_value = "test-token"
                mock_canvas_instance = MagicMock()
                mock_canvas_class.return_value = mock_canvas_instance
                
                from canvas_sync.api.auth import get_canvas_client
                from canvas_sync.config import DEFAULT_CANVAS_URL
                
                client = get_canvas_client(str(tmp_path))
                
                mock_canvas_class.assert_called_once_with(
                    DEFAULT_CANVAS_URL, "test-token"
                )

    def test_raises_when_no_token(self, tmp_path):
        """Raises ConfigError when no token available."""
        with patch("canvas_sync.api.auth.keyring") as mock_keyring:
            mock_keyring.get_password.return_value = None
            
            from canvas_sync.api.auth import get_canvas_client, ConfigError
            
            with pytest.raises(ConfigError):
                get_canvas_client(str(tmp_path))
