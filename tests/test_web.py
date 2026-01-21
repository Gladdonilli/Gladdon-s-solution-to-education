"""Tests for Flask web application."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def app(tmp_path):
    """Create test Flask app."""
    with patch("canvas_sync.web.app.DEFAULT_VAULT_PATH", tmp_path):
        from canvas_sync.web.app import create_app
        
        app = create_app(testing=True)
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestSetupRoute:
    """Tests for /setup route."""

    def test_get_shows_form(self, client):
        """GET /setup shows setup form."""
        with patch("canvas_sync.web.app.get_api_token", return_value=None):
            response = client.get("/setup")
            
            assert response.status_code == 200
            assert b"API Token" in response.data
            assert b"Canvas URL" in response.data

    def test_post_saves_token_and_redirects(self, client, tmp_path):
        """POST /setup saves token and redirects to courses."""
        with patch("canvas_sync.web.app.get_api_token", return_value=None):
            with patch("canvas_sync.web.app.set_api_token") as mock_set:
                response = client.post(
                    "/setup",
                    data={
                        "canvas_url": "https://test.instructure.com",
                        "api_token": "test-token-123",
                    },
                    follow_redirects=False,
                )
                
                assert response.status_code == 302
                assert "/courses" in response.location
                mock_set.assert_called_once_with("test-token-123")


class TestCoursesRoute:
    """Tests for /courses route."""

    def test_redirects_to_setup_without_token(self, client):
        """Redirects to setup if no token."""
        with patch("canvas_sync.web.app.get_api_token", return_value=None):
            response = client.get("/courses", follow_redirects=False)
            
            assert response.status_code == 302
            assert "/setup" in response.location

    def test_shows_course_list(self, client, tmp_path):
        """GET /courses shows list of courses."""
        mock_course = MagicMock()
        mock_course.id = 123
        mock_course.name = "CS 101"
        
        with patch("canvas_sync.web.app.get_api_token", return_value="token"):
            with patch("canvas_sync.web.app.get_all_courses", return_value=[mock_course]):
                with patch("canvas_sync.web.app.get_selected_courses", return_value=[]):
                    response = client.get("/courses")
                    
                    assert response.status_code == 200
                    assert b"CS 101" in response.data


class TestSyncRoute:
    """Tests for /sync route."""

    def test_redirects_without_courses(self, client, tmp_path):
        """Redirects to courses if none selected."""
        with patch("canvas_sync.web.app.get_api_token", return_value="token"):
            with patch("canvas_sync.web.app.get_selected_courses", return_value=[]):
                response = client.get("/sync", follow_redirects=False)
                
                assert response.status_code == 302
                assert "/courses" in response.location

    def test_runs_sync_and_shows_results(self, client, tmp_path):
        """Runs sync and displays results."""
        with patch("canvas_sync.web.app.get_api_token", return_value="token"):
            with patch("canvas_sync.web.app.get_selected_courses") as mock_get:
                mock_get.return_value = [{"course_id": 123, "course_name": "CS 101"}]
                
                with patch("canvas_sync.web.app.run_sync") as mock_sync:
                    mock_sync.return_value = {
                        "assignments_synced": 5,
                        "events_synced": 2,
                        "skipped": 1,
                        "errors": [],
                    }
                    
                    response = client.get("/sync")
                    
                    assert response.status_code == 200
                    assert b"5" in response.data


class TestStatusRoute:
    """Tests for /status route."""

    def test_shows_no_sync_message(self, client, tmp_path):
        """Shows message when no sync performed."""
        with patch("canvas_sync.web.app.get_api_token", return_value="token"):
            with patch("canvas_sync.web.app.get_config", return_value=None):
                response = client.get("/status")
                
                assert response.status_code == 200
                assert b"No sync has been performed" in response.data


class TestSettingsRoute:
    """Tests for /settings route."""

    def test_shows_current_settings(self, client, tmp_path):
        """GET /settings shows current configuration."""
        with patch("canvas_sync.web.app.get_api_token", return_value="token"):
            with patch("canvas_sync.web.app.get_vault_path_from_config", return_value=str(tmp_path)):
                with patch("canvas_sync.web.app.get_config", return_value="https://canvas.illinois.edu"):
                    with patch("canvas_sync.web.app.get_sync_time_from_config", return_value="06:00"):
                        response = client.get("/settings")
                        
                        assert response.status_code == 200
                        assert b"06:00" in response.data
