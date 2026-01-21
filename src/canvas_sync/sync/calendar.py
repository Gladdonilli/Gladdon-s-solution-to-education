"""Calendar event sync from Canvas to Obsidian markdown."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from canvas_sync.api.auth import get_canvas_client
from canvas_sync.db.models import get_db, get_sync_state, set_sync_state
from canvas_sync.sync.utils import (
    compute_hash,
    get_course_folder_name,
    get_file_path,
    html_to_markdown,
    sanitize_filename,
    should_sync_item,
)


def get_calendar_date_range() -> tuple[str, str]:
    """Get start/end dates for calendar event query."""
    today = datetime.now()
    start = today - timedelta(days=30)
    end = today + timedelta(days=365)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def is_all_day_event(start_at: str | None) -> bool:
    """Check if event is all-day based on start time."""
    if not start_at:
        return False
    try:
        dt = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
        return dt.hour == 0 and dt.minute == 0 and dt.second == 0
    except (ValueError, AttributeError):
        return False


def format_event_time(start_at: str | None, end_at: str | None) -> str:
    """Format event time for display."""
    if not start_at:
        return "Time not specified"

    try:
        start_dt = datetime.fromisoformat(start_at.replace("Z", "+00:00"))

        if is_all_day_event(start_at):
            return f"{start_dt.strftime('%B %d, %Y')} (All Day)"

        if end_at:
            end_dt = datetime.fromisoformat(end_at.replace("Z", "+00:00"))
            return f"{start_dt.strftime('%B %d, %Y from %I:%M %p')} to {end_dt.strftime('%I:%M %p')}"
        else:
            return start_dt.strftime("%B %d, %Y at %I:%M %p")
    except (ValueError, AttributeError):
        return start_at


def build_event_markdown(event: Any, course: Any) -> str:
    """Build markdown content for calendar event."""
    now = datetime.now().isoformat()
    start_at = getattr(event, "start_at", None)
    end_at = getattr(event, "end_at", None)
    location = getattr(event, "location_name", None)

    frontmatter = {
        "type": "calendar_event",
        "course": course.name,
        "course_id": course.id,
        "canvas_id": event.id,
        "start": start_at,
        "end": end_at,
        "all_day": is_all_day_event(start_at),
        "location": location,
        "synced_at": now,
    }

    description = html_to_markdown(getattr(event, "description", "") or "")
    time_display = format_event_time(start_at, end_at)
    url = getattr(event, "html_url", "")

    body = f"""# {event.title}

## When

{time_display}

## Location

{location or "Not specified"}

## Description

{description or "No description provided."}

[Open in Canvas]({url})
"""

    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n\n{body}"


def sync_calendar_events(course_ids: list[int], vault_path: str) -> tuple[int, int]:
    """Sync calendar events for courses to markdown files.

    Returns:
        (synced_count, skipped_count)
    """
    canvas = get_canvas_client(vault_path)
    conn = get_db(vault_path)

    start_date, end_date = get_calendar_date_range()
    context_codes = [f"course_{cid}" for cid in course_ids]

    events = canvas.get_calendar_events(
        context_codes=context_codes,
        type="event",
        start_date=start_date,
        end_date=end_date,
    )

    course_cache: dict[int, Any] = {}
    synced = 0
    skipped = 0

    for event in events:
        context_code = getattr(event, "context_code", "")
        if not context_code.startswith("course_"):
            continue

        course_id = int(context_code.replace("course_", ""))

        if course_id not in course_cache:
            course_cache[course_id] = canvas.get_course(course_id)
        course = course_cache[course_id]

        file_path = get_file_path(vault_path, course, "Events", event.title)
        db_record = get_sync_state(conn, event.id, "calendar_event")

        canvas_updated = getattr(event, "updated_at", None)
        should_sync, reason = should_sync_item(file_path, canvas_updated, db_record)

        if not should_sync:
            if reason == "locally_edited":
                skipped += 1
            continue

        content = build_event_markdown(event, course)
        content_hash = compute_hash(content)

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        set_sync_state(
            conn,
            canvas_id=event.id,
            canvas_type="calendar_event",
            course_id=course_id,
            file_path=str(file_path.relative_to(vault_path)),
            content_hash=content_hash,
            canvas_updated_at=canvas_updated,
            synced_at=datetime.now().isoformat(),
        )
        synced += 1

    conn.close()
    return synced, skipped
