"""Tests for Canvas course fetching module."""

import pytest
from unittest.mock import patch, MagicMock
from canvasapi.exceptions import RateLimitExceeded


class TestGetAllCourses:
    """Tests for get_all_courses function."""

    def test_returns_list_of_courses(self, tmp_path):
        """Returns list of active courses for user."""
        with patch("canvas_sync.api.courses.get_canvas_client") as mock_get_client:
            mock_canvas = MagicMock()
            mock_get_client.return_value = mock_canvas
            
            mock_course1 = MagicMock()
            mock_course1.id = 123
            mock_course1.name = "CS 101"
            mock_course2 = MagicMock()
            mock_course2.id = 456
            mock_course2.name = "MATH 241"
            
            mock_canvas.get_courses.return_value = [mock_course1, mock_course2]
            
            from canvas_sync.api.courses import get_all_courses
            
            courses = get_all_courses(str(tmp_path))
            
            assert len(courses) == 2
            assert courses[0].id == 123
            assert courses[1].name == "MATH 241"
            mock_canvas.get_courses.assert_called_once_with(enrollment_state="active")

    def test_handles_rate_limit_with_backoff(self, tmp_path):
        """Retries with exponential backoff on rate limit."""
        with patch("canvas_sync.api.courses.get_canvas_client") as mock_get_client:
            with patch("canvas_sync.api.courses.time.sleep") as mock_sleep:
                mock_canvas = MagicMock()
                mock_get_client.return_value = mock_canvas
                
                mock_course = MagicMock()
                mock_course.id = 123
                
                mock_canvas.get_courses.side_effect = [
                    RateLimitExceeded("Rate limit"),
                    RateLimitExceeded("Rate limit"),
                    [mock_course],
                ]
                
                from canvas_sync.api.courses import get_all_courses
                
                courses = get_all_courses(str(tmp_path))
                
                assert len(courses) == 1
                assert mock_sleep.call_count == 2
                mock_sleep.assert_any_call(1)
                mock_sleep.assert_any_call(2)

    def test_raises_after_max_retries(self, tmp_path):
        """Raises exception after 3 failed retries."""
        with patch("canvas_sync.api.courses.get_canvas_client") as mock_get_client:
            with patch("canvas_sync.api.courses.time.sleep"):
                mock_canvas = MagicMock()
                mock_get_client.return_value = mock_canvas
                
                mock_canvas.get_courses.side_effect = RateLimitExceeded("Rate limit")
                
                from canvas_sync.api.courses import get_all_courses, RateLimitError
                
                with pytest.raises(RateLimitError, match="after 3 retries"):
                    get_all_courses(str(tmp_path))


class TestGetCourseDetails:
    """Tests for get_course_details function."""

    def test_returns_course_with_syllabus(self, tmp_path):
        """Returns single course with syllabus included."""
        with patch("canvas_sync.api.courses.get_canvas_client") as mock_get_client:
            mock_canvas = MagicMock()
            mock_get_client.return_value = mock_canvas
            
            mock_course = MagicMock()
            mock_course.id = 123
            mock_course.name = "CS 101"
            mock_course.syllabus_body = "<p>Course syllabus</p>"
            
            mock_canvas.get_course.return_value = mock_course
            
            from canvas_sync.api.courses import get_course_details
            
            course = get_course_details(123, str(tmp_path))
            
            assert course.id == 123
            assert course.syllabus_body == "<p>Course syllabus</p>"
            mock_canvas.get_course.assert_called_once_with(
                123, include=["syllabus_body", "term"]
            )

    def test_handles_rate_limit_with_backoff(self, tmp_path):
        """Retries with exponential backoff on rate limit."""
        with patch("canvas_sync.api.courses.get_canvas_client") as mock_get_client:
            with patch("canvas_sync.api.courses.time.sleep") as mock_sleep:
                mock_canvas = MagicMock()
                mock_get_client.return_value = mock_canvas
                
                mock_course = MagicMock()
                mock_course.id = 123
                
                mock_canvas.get_course.side_effect = [
                    RateLimitExceeded("Rate limit"),
                    mock_course,
                ]
                
                from canvas_sync.api.courses import get_course_details
                
                course = get_course_details(123, str(tmp_path))
                
                assert course.id == 123
                mock_sleep.assert_called_once_with(1)
