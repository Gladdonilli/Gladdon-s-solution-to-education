"""Tests for calendar event sync module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSyncCalendarEvents:
    """Tests for sync_calendar_events function."""

    def test_creates_markdown_file_for_new_event(self, tmp_path):
        """Creates markdown file with frontmatter for new calendar event."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        with patch("canvas_sync.sync.calendar.get_canvas_client") as mock_client:
            mock_canvas = MagicMock()
            mock_client.return_value = mock_canvas

            mock_course = MagicMock()
            mock_course.id = 123
            mock_course.name = "CS 101"
            mock_canvas.get_course.return_value = mock_course

            mock_event = MagicMock()
            mock_event.id = 789
            mock_event.title = "Midterm Exam"
            mock_event.start_at = "2026-03-01T14:00:00Z"
            mock_event.end_at = "2026-03-01T16:00:00Z"
            mock_event.location_name = "Room 100"
            mock_event.description = "<p>Bring pencils</p>"
            mock_event.updated_at = "2026-01-20T10:00:00Z"
            mock_event.context_code = "course_123"
            mock_event.html_url = "https://canvas.illinois.edu/calendar?event_id=789"

            mock_canvas.get_calendar_events.return_value = [mock_event]

            from canvas_sync.sync.calendar import sync_calendar_events

            synced, skipped = sync_calendar_events([123], str(vault_path))

            assert synced == 1
            assert skipped == 0

            expected_path = vault_path / "Courses" / "CS 101" / "Events" / "Midterm Exam.md"
            assert expected_path.exists()

            content = expected_path.read_text()
            assert "type: calendar_event" in content
            assert "course: CS 101" in content
            assert "canvas_id: 789" in content
            assert "2026-03-01" in content
            assert "location: Room 100" in content

    def test_skips_locally_edited_event(self, tmp_path):
        """Skips event file if locally edited."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        with patch("canvas_sync.sync.calendar.get_canvas_client") as mock_client:
            with patch("canvas_sync.sync.calendar.get_db") as mock_get_db:
                mock_canvas = MagicMock()
                mock_client.return_value = mock_canvas

                mock_course = MagicMock()
                mock_course.id = 123
                mock_course.name = "CS 101"
                mock_canvas.get_course.return_value = mock_course

                mock_event = MagicMock()
                mock_event.id = 789
                mock_event.title = "Midterm Exam"
                mock_event.start_at = "2026-03-01T14:00:00Z"
                mock_event.end_at = "2026-03-01T16:00:00Z"
                mock_event.location_name = "Room 100"
                mock_event.description = ""
                mock_event.updated_at = "2026-01-20T10:00:00Z"
                mock_event.context_code = "course_123"
                mock_event.html_url = "https://canvas.illinois.edu/..."

                mock_canvas.get_calendar_events.return_value = [mock_event]

                file_path = vault_path / "Courses" / "CS 101" / "Events" / "Midterm Exam.md"
                file_path.parent.mkdir(parents=True)
                file_path.write_text("# My notes about midterm")

                mock_conn = MagicMock()
                mock_get_db.return_value = mock_conn
                mock_conn.execute.return_value.fetchone.return_value = {
                    "content_hash": "different_hash",
                    "canvas_updated_at": "2026-01-19T10:00:00Z",
                }

                from canvas_sync.sync.calendar import sync_calendar_events

                synced, skipped = sync_calendar_events([123], str(vault_path))

                assert synced == 0
                assert skipped == 1

    def test_handles_all_day_events(self, tmp_path):
        """Correctly identifies all-day events."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        with patch("canvas_sync.sync.calendar.get_canvas_client") as mock_client:
            mock_canvas = MagicMock()
            mock_client.return_value = mock_canvas

            mock_course = MagicMock()
            mock_course.id = 123
            mock_course.name = "CS 101"
            mock_canvas.get_course.return_value = mock_course

            mock_event = MagicMock()
            mock_event.id = 789
            mock_event.title = "Holiday"
            mock_event.start_at = "2026-03-01T00:00:00Z"
            mock_event.end_at = None
            mock_event.location_name = None
            mock_event.description = ""
            mock_event.updated_at = "2026-01-20T10:00:00Z"
            mock_event.context_code = "course_123"
            mock_event.html_url = "https://canvas.illinois.edu/..."

            mock_canvas.get_calendar_events.return_value = [mock_event]

            from canvas_sync.sync.calendar import sync_calendar_events

            sync_calendar_events([123], str(vault_path))

            file_path = vault_path / "Courses" / "CS 101" / "Events" / "Holiday.md"
            content = file_path.read_text()
            assert "all_day: true" in content
