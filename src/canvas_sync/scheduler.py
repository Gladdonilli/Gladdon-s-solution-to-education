"""Background scheduler for daily Canvas sync."""

import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule

from canvas_sync.config import DEFAULT_VAULT_PATH
from canvas_sync.db.models import (
    get_config,
    get_db,
    get_selected_courses,
    get_sync_time_from_config,
    get_vault_path_from_config,
    set_config,
)
from canvas_sync.sync.assignments import sync_assignments
from canvas_sync.sync.calendar import sync_calendar_events


_shutdown_requested = False


def setup_logging(vault_path: str) -> None:
    """Configure logging to file."""
    log_path = Path(vault_path) / ".canvas_sync" / "sync.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    logging.info("Shutdown signal received, stopping scheduler...")
    _shutdown_requested = True


def scheduled_sync(vault_path: str) -> None:
    """Execute scheduled sync for selected courses."""
    conn = get_db(vault_path)
    selected = get_selected_courses(conn)

    if not selected:
        logging.warning("No courses selected, skipping sync")
        conn.close()
        return

    logging.info(f"Sync started for {len(selected)} courses")

    results = {
        "started_at": datetime.now().isoformat(),
        "assignments_synced": 0,
        "events_synced": 0,
        "skipped": 0,
        "errors": [],
        "courses_synced": [],
    }

    for course in selected:
        try:
            a_count, a_skipped = sync_assignments(course["course_id"], vault_path)
            results["assignments_synced"] += a_count
            results["skipped"] += a_skipped
            results["courses_synced"].append(course["course_name"])
        except Exception as e:
            error_msg = f"Assignments for {course['course_name']}: {e}"
            logging.error(error_msg)
            results["errors"].append(error_msg)

    try:
        course_ids = [c["course_id"] for c in selected]
        e_count, e_skipped = sync_calendar_events(course_ids, vault_path)
        results["events_synced"] += e_count
        results["skipped"] += e_skipped
    except Exception as e:
        error_msg = f"Calendar events: {e}"
        logging.error(error_msg)
        results["errors"].append(error_msg)

    results["completed_at"] = datetime.now().isoformat()

    set_config(conn, "last_sync_at", datetime.now().isoformat())
    set_config(conn, "last_sync_status", json.dumps(results))
    conn.close()

    logging.info(
        f"Synced {results['assignments_synced']} assignments, "
        f"{results['events_synced']} events"
    )


def run_daemon() -> None:
    """Run background sync daemon."""
    global _shutdown_requested

    conn = get_db(str(DEFAULT_VAULT_PATH))
    vault_path = get_vault_path_from_config(conn)
    sync_time = get_sync_time_from_config(conn)
    conn.close()

    setup_logging(vault_path)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logging.info(f"Scheduler started, next sync at {sync_time}")
    print(f"Canvas Sync daemon started. Daily sync at {sync_time}")
    print(f"Vault: {vault_path}")
    print("Press Ctrl+C to stop.")

    schedule.every().day.at(sync_time).do(scheduled_sync, vault_path)

    while not _shutdown_requested:
        schedule.run_pending()
        time.sleep(60)

    logging.info("Scheduler stopped")
    print("\nScheduler stopped.")
