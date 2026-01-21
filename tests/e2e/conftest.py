"""E2E test fixtures for Playwright tests."""

import pytest
import threading
import time
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="module")
def flask_server(tmp_path_factory):
    """Start Flask app in background thread for Playwright tests."""
    tmp_path = tmp_path_factory.mktemp("vault")
    
    with patch("canvas_sync.web.app.DEFAULT_VAULT_PATH", tmp_path):
        with patch("canvas_sync.web.app.get_api_token", return_value=None):
            from canvas_sync.web.app import create_app
            
            app = create_app(testing=True)
            
            server_thread = threading.Thread(
                target=lambda: app.run(port=5001, use_reloader=False, threaded=True),
                daemon=True
            )
            server_thread.start()
            
            time.sleep(1)
            
            yield "http://localhost:5001", tmp_path


@pytest.fixture
def mock_canvas_api():
    """Mock Canvas API responses for E2E tests."""
    mock_courses = [
        MagicMock(id=123, name="CS 101 - Intro to Programming"),
        MagicMock(id=456, name="MATH 241 - Calculus III"),
    ]
    
    mock_assignment = MagicMock()
    mock_assignment.id = 789
    mock_assignment.name = "Homework 1"
    mock_assignment.due_at = "2026-02-15T23:59:00Z"
    mock_assignment.points_possible = 100
    mock_assignment.html_url = "https://canvas.illinois.edu/courses/123/assignments/789"
    mock_assignment.description = "<p>Complete the exercises</p>"
    mock_assignment.updated_at = "2026-01-20T10:00:00Z"
    mock_assignment.submission = None
    mock_assignment.submission_types = ["online_upload"]
    
    mock_event = MagicMock()
    mock_event.id = 999
    mock_event.title = "Midterm Exam"
    mock_event.start_at = "2026-03-01T14:00:00Z"
    mock_event.end_at = "2026-03-01T16:00:00Z"
    mock_event.location_name = "Room 100"
    mock_event.description = "<p>Bring pencils</p>"
    mock_event.updated_at = "2026-01-20T10:00:00Z"
    mock_event.context_code = "course_123"
    mock_event.html_url = "https://canvas.illinois.edu/calendar?event_id=999"
    
    mock_course_obj = MagicMock()
    mock_course_obj.id = 123
    mock_course_obj.name = "CS 101 - Intro to Programming"
    mock_course_obj.get_assignments.return_value = [mock_assignment]
    
    return {
        "courses": mock_courses,
        "course": mock_course_obj,
        "assignments": [mock_assignment],
        "events": [mock_event],
    }
