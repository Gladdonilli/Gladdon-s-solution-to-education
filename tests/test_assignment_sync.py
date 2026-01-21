"""Tests for assignment sync module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestSyncAssignments:
    """Tests for sync_assignments function."""

    def test_creates_markdown_file_for_new_assignment(self, tmp_path):
        """Creates markdown file with frontmatter for new assignment."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        with patch("canvas_sync.sync.assignments.get_canvas_client") as mock_client:
            mock_canvas = MagicMock()
            mock_client.return_value = mock_canvas

            mock_course = MagicMock()
            mock_course.id = 123
            mock_course.name = "CS 101"
            mock_canvas.get_course.return_value = mock_course

            mock_assignment = MagicMock()
            mock_assignment.id = 456
            mock_assignment.name = "Homework 1"
            mock_assignment.due_at = "2026-02-15T23:59:00Z"
            mock_assignment.points_possible = 100
            mock_assignment.html_url = "https://canvas.illinois.edu/courses/123/assignments/456"
            mock_assignment.description = "<p>Do homework</p>"
            mock_assignment.updated_at = "2026-01-20T10:00:00Z"
            mock_assignment.submission = None
            mock_assignment.submission_types = ["online_upload"]

            mock_course.get_assignments.return_value = [mock_assignment]

            from canvas_sync.sync.assignments import sync_assignments

            synced, skipped = sync_assignments(123, str(vault_path))

            assert synced == 1
            assert skipped == 0

            expected_path = vault_path / "Courses" / "CS 101" / "Assignments" / "Homework 1.md"
            assert expected_path.exists()

            content = expected_path.read_text()
            assert "type: assignment" in content
            assert "course: CS 101" in content
            assert "canvas_id: 456" in content
            assert "2026-02-15" in content
            assert "points: 100" in content

    def test_skips_locally_edited_file(self, tmp_path):
        """Skips file if locally edited (hash mismatch)."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        with patch("canvas_sync.sync.assignments.get_canvas_client") as mock_client:
            with patch("canvas_sync.sync.assignments.get_db") as mock_get_db:
                mock_canvas = MagicMock()
                mock_client.return_value = mock_canvas

                mock_course = MagicMock()
                mock_course.id = 123
                mock_course.name = "CS 101"
                mock_canvas.get_course.return_value = mock_course

                mock_assignment = MagicMock()
                mock_assignment.id = 456
                mock_assignment.name = "Homework 1"
                mock_assignment.due_at = "2026-02-15T23:59:00Z"
                mock_assignment.points_possible = 100
                mock_assignment.html_url = "https://canvas.illinois.edu/..."
                mock_assignment.description = "<p>Do homework</p>"
                mock_assignment.updated_at = "2026-01-20T10:00:00Z"
                mock_assignment.submission = None
                mock_assignment.submission_types = ["online_upload"]

                mock_course.get_assignments.return_value = [mock_assignment]

                file_path = vault_path / "Courses" / "CS 101" / "Assignments" / "Homework 1.md"
                file_path.parent.mkdir(parents=True)
                file_path.write_text("# My local edits\nI changed this file")

                mock_conn = MagicMock()
                mock_get_db.return_value = mock_conn
                mock_conn.execute.return_value.fetchone.return_value = {
                    "content_hash": "different_hash",
                    "canvas_updated_at": "2026-01-19T10:00:00Z",
                }

                from canvas_sync.sync.assignments import sync_assignments

                synced, skipped = sync_assignments(123, str(vault_path))

                assert synced == 0
                assert skipped == 1
                assert "My local edits" in file_path.read_text()

    def test_derives_status_from_submission(self, tmp_path):
        """Correctly derives status from submission data."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        with patch("canvas_sync.sync.assignments.get_canvas_client") as mock_client:
            mock_canvas = MagicMock()
            mock_client.return_value = mock_canvas

            mock_course = MagicMock()
            mock_course.id = 123
            mock_course.name = "CS 101"
            mock_canvas.get_course.return_value = mock_course

            mock_submission = MagicMock()
            mock_submission.workflow_state = "graded"
            mock_submission.grade = "95"

            mock_assignment = MagicMock()
            mock_assignment.id = 456
            mock_assignment.name = "Graded HW"
            mock_assignment.due_at = None
            mock_assignment.points_possible = 100
            mock_assignment.html_url = "https://canvas.illinois.edu/..."
            mock_assignment.description = ""
            mock_assignment.updated_at = "2026-01-20T10:00:00Z"
            mock_assignment.submission = mock_submission
            mock_assignment.submission_types = ["online_upload"]

            mock_course.get_assignments.return_value = [mock_assignment]

            from canvas_sync.sync.assignments import sync_assignments

            sync_assignments(123, str(vault_path))

            file_path = vault_path / "Courses" / "CS 101" / "Assignments" / "Graded HW.md"
            content = file_path.read_text()
            assert "status: graded" in content
