"""Assignment sync from Canvas to Obsidian markdown."""

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from canvas_sync.api.auth import get_canvas_client
from canvas_sync.db.models import get_db, get_sync_state, set_sync_state
from canvas_sync.sync.utils import (
    compute_hash,
    get_file_path,
    html_to_markdown,
    should_sync_item,
)


def derive_assignment_status(assignment: Any) -> str:
    """Derive status from Canvas assignment submission data."""
    submission = getattr(assignment, "submission", None)

    if submission is None:
        return "pending"

    workflow_state = getattr(submission, "workflow_state", "unsubmitted")
    grade = getattr(submission, "grade", None)

    if workflow_state == "graded" or grade is not None:
        return "graded"
    elif workflow_state in ("submitted", "pending_review"):
        return "submitted"
    else:
        return "pending"


def format_due_date(due_at: str | None) -> str:
    """Format due date for display."""
    if not due_at:
        return "No due date"
    try:
        dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y at %I:%M %p")
    except (ValueError, AttributeError):
        return due_at


def build_assignment_markdown(assignment: Any, course: Any) -> str:
    """Build markdown content for assignment."""
    now = datetime.now().isoformat()
    status = derive_assignment_status(assignment)

    frontmatter = {
        "type": "assignment",
        "course": course.name,
        "course_id": course.id,
        "canvas_id": assignment.id,
        "due": getattr(assignment, "due_at", None),
        "points": getattr(assignment, "points_possible", None),
        "status": status,
        "url": getattr(assignment, "html_url", ""),
        "synced_at": now,
    }

    description = html_to_markdown(getattr(assignment, "description", "") or "")
    due_display = format_due_date(getattr(assignment, "due_at", None))
    points = getattr(assignment, "points_possible", None)
    points_display = str(points) if points else "Ungraded"
    submission_types = getattr(assignment, "submission_types", [])
    types_display = ", ".join(submission_types) if submission_types else "None"

    body = f"""# {assignment.name}

## Description

{description or "No description provided."}

## Details

- **Due**: {due_display}
- **Points**: {points_display}
- **Submission Types**: {types_display}

[Open in Canvas]({frontmatter['url']})
"""

    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n\n{body}"


def sync_assignments(course_id: int, vault_path: str) -> tuple[int, int]:
    """Sync assignments for a course to markdown files.

    Returns:
        (synced_count, skipped_count)
    """
    canvas = get_canvas_client(vault_path)
    course = canvas.get_course(course_id)
    conn = get_db(vault_path)

    assignments = course.get_assignments(include=["submission"], order_by="due_at")

    synced = 0
    skipped = 0

    for assignment in assignments:
        file_path = get_file_path(vault_path, course, "Assignments", assignment.name)
        db_record = get_sync_state(conn, assignment.id, "assignment")

        canvas_updated = getattr(assignment, "updated_at", None)
        should_sync, reason = should_sync_item(file_path, canvas_updated, db_record)

        if not should_sync:
            if reason == "locally_edited":
                skipped += 1
            continue

        content = build_assignment_markdown(assignment, course)
        content_hash = compute_hash(content)

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        set_sync_state(
            conn,
            canvas_id=assignment.id,
            canvas_type="assignment",
            course_id=course_id,
            file_path=str(file_path.relative_to(vault_path)),
            content_hash=content_hash,
            canvas_updated_at=canvas_updated,
            synced_at=datetime.now().isoformat(),
        )
        synced += 1

    conn.close()
    return synced, skipped
