"""E2E tests for full user flow with Playwright."""

import pytest
from unittest.mock import patch, MagicMock
from playwright.sync_api import Page, expect


class TestSetupFlow:
    """E2E tests for initial setup flow."""

    def test_setup_page_shows_form(self, page: Page, flask_server):
        """Setup page displays token entry form."""
        base_url, _ = flask_server
        
        with patch("canvas_sync.web.app.get_api_token", return_value=None):
            page.goto(f"{base_url}/setup")
            
            expect(page.locator("#api_token")).to_be_visible()
            expect(page.locator("#canvas_url")).to_be_visible()
            expect(page.get_by_role("button", name="Save")).to_be_visible()

    def test_index_redirects_to_setup_without_token(self, page: Page, flask_server):
        """Index redirects to setup when no token configured."""
        base_url, _ = flask_server
        
        with patch("canvas_sync.web.app.get_api_token", return_value=None):
            page.goto(base_url)
            
            expect(page).to_have_url(f"{base_url}/setup")


class TestCourseSelection:
    """E2E tests for course selection flow."""

    def test_courses_page_shows_course_list(self, page: Page, flask_server, mock_canvas_api):
        """Courses page displays list of available courses."""
        base_url, tmp_path = flask_server
        
        with patch("canvas_sync.web.app.get_api_token", return_value="test-token"):
            with patch("canvas_sync.web.app.get_all_courses", return_value=mock_canvas_api["courses"]):
                with patch("canvas_sync.web.app.get_selected_courses", return_value=[]):
                    page.goto(f"{base_url}/courses")
                    
                    expect(page.get_by_text("CS 101")).to_be_visible()
                    expect(page.get_by_text("MATH 241")).to_be_visible()

    def test_can_select_courses(self, page: Page, flask_server, mock_canvas_api):
        """User can select courses via checkboxes."""
        base_url, tmp_path = flask_server
        
        with patch("canvas_sync.web.app.get_api_token", return_value="test-token"):
            with patch("canvas_sync.web.app.get_all_courses", return_value=mock_canvas_api["courses"]):
                with patch("canvas_sync.web.app.get_selected_courses", return_value=[]):
                    page.goto(f"{base_url}/courses")
                    
                    checkbox = page.locator("input[value='123']")
                    expect(checkbox).to_be_visible()
                    
                    checkbox.check()
                    expect(checkbox).to_be_checked()


class TestStatusPage:
    """E2E tests for status page."""

    def test_status_shows_no_sync_message(self, page: Page, flask_server):
        """Status page shows message when no sync performed."""
        base_url, _ = flask_server
        
        with patch("canvas_sync.web.app.get_api_token", return_value="test-token"):
            with patch("canvas_sync.web.app.get_config", return_value=None):
                page.goto(f"{base_url}/status")
                
                expect(page.get_by_text("No sync has been performed")).to_be_visible()


class TestSettingsPage:
    """E2E tests for settings page."""

    def test_settings_shows_sync_time_dropdown(self, page: Page, flask_server):
        """Settings page displays sync time configuration."""
        base_url, tmp_path = flask_server
        
        with patch("canvas_sync.web.app.get_api_token", return_value="test-token"):
            with patch("canvas_sync.web.app.get_vault_path_from_config", return_value=str(tmp_path)):
                with patch("canvas_sync.web.app.get_config", return_value="https://canvas.illinois.edu"):
                    with patch("canvas_sync.web.app.get_sync_time_from_config", return_value="06:00"):
                        page.goto(f"{base_url}/settings")
                        
                        expect(page.locator("#sync_time")).to_be_visible()
                        expect(page.locator("#sync_time")).to_have_value("06:00")
