"""Tests for background scheduler."""

import pytest
from unittest.mock import patch, MagicMock
from freezegun import freeze_time
import schedule


class TestScheduledSync:
    """Tests for scheduled_sync function."""

    def test_skips_when_no_courses_selected(self, tmp_path):
        """Logs warning when no courses selected."""
        with patch("canvas_sync.scheduler.get_db") as mock_get_db:
            with patch("canvas_sync.scheduler.get_selected_courses", return_value=[]):
                with patch("canvas_sync.scheduler.logging") as mock_logging:
                    from canvas_sync.scheduler import scheduled_sync
                    
                    mock_conn = MagicMock()
                    mock_get_db.return_value = mock_conn
                    
                    scheduled_sync(str(tmp_path))
                    
                    mock_logging.warning.assert_called_once()
                    assert "No courses selected" in str(mock_logging.warning.call_args)

    def test_syncs_selected_courses(self, tmp_path):
        """Syncs assignments and events for selected courses."""
        with patch("canvas_sync.scheduler.get_db") as mock_get_db:
            with patch("canvas_sync.scheduler.get_selected_courses") as mock_get_courses:
                with patch("canvas_sync.scheduler.sync_assignments") as mock_sync_a:
                    with patch("canvas_sync.scheduler.sync_calendar_events") as mock_sync_e:
                        with patch("canvas_sync.scheduler.set_config"):
                            from canvas_sync.scheduler import scheduled_sync
                            
                            mock_conn = MagicMock()
                            mock_get_db.return_value = mock_conn
                            mock_get_courses.return_value = [
                                {"course_id": 123, "course_name": "CS 101"}
                            ]
                            mock_sync_a.return_value = (5, 1)
                            mock_sync_e.return_value = (3, 0)
                            
                            scheduled_sync(str(tmp_path))
                            
                            mock_sync_a.assert_called_once_with(123, str(tmp_path))
                            mock_sync_e.assert_called_once_with([123], str(tmp_path))


class TestSchedulerTiming:
    """Tests for scheduler timing behavior."""

    @freeze_time("2026-01-21 05:59:00")
    def test_sync_not_triggered_before_time(self):
        """Sync not triggered before scheduled time."""
        with patch("canvas_sync.scheduler.scheduled_sync") as mock_sync:
            schedule.clear()
            schedule.every().day.at("06:00").do(mock_sync, "/tmp/vault")
            
            schedule.run_pending()
            
            assert mock_sync.call_count == 0

    def test_sync_triggered_at_scheduled_time(self):
        """Sync triggered when run_pending called after scheduled time."""
        schedule.clear()
        
        mock_sync = MagicMock()
        job = schedule.every().day.at("06:00").do(mock_sync, "/tmp/vault")
        
        # Manually mark job as due by setting last_run to None and next_run to past
        from datetime import datetime, timedelta
        job.next_run = datetime.now() - timedelta(minutes=1)
        
        schedule.run_pending()
        
        assert mock_sync.call_count == 1


class TestGracefulShutdown:
    """Tests for graceful shutdown behavior."""

    def test_signal_handler_sets_shutdown_flag(self):
        """Signal handler sets shutdown flag."""
        from canvas_sync.scheduler import signal_handler
        import canvas_sync.scheduler as scheduler_module
        
        with patch.object(scheduler_module, "_shutdown_requested", False):
            with patch("canvas_sync.scheduler.logging"):
                signal_handler(15, None)
                
                assert scheduler_module._shutdown_requested is True
