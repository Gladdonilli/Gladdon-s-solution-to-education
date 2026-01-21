"""Shared utilities for sync operations."""

import hashlib
import re
from pathlib import Path
from typing import Any

from html2text import HTML2Text


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sanitize_filename(name: str) -> str:
    """Convert Canvas item name to safe filename."""
    safe = re.sub(r'[<>:"/\\|?*]', "_", name)
    safe = re.sub(r"_+", "_", safe)
    safe = safe.strip(" _")
    safe = safe[:100]
    return safe or "untitled"


def get_course_folder_name(course: Any) -> str:
    """Derive folder name from Canvas course object."""
    name = getattr(course, "name", None) or getattr(
        course, "course_code", f"course_{course.id}"
    )
    return sanitize_filename(name)


def get_file_path(
    vault_path: str, course: Any, item_type: str, item_name: str
) -> Path:
    """Build full file path for a synced item.

    Structure: {vault}/Courses/{course_folder}/{type_folder}/{item_name}.md
    """
    course_folder = get_course_folder_name(course)
    safe_name = sanitize_filename(item_name)
    return Path(vault_path) / "Courses" / course_folder / item_type / f"{safe_name}.md"


def html_to_markdown(html: str) -> str:
    """Convert Canvas HTML content to Obsidian-friendly markdown."""
    if not html:
        return ""
    h = HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0
    return h.handle(html).strip()


def should_sync_item(
    file_path: Path, canvas_updated_at: str | None, db_record: dict[str, Any] | None
) -> tuple[bool, str]:
    """Determine if item should be synced.

    Returns:
        (should_sync, reason)
    """
    if not file_path.exists():
        return True, "new_file"

    if db_record is None:
        return True, "no_db_record"

    disk_content = file_path.read_text(encoding="utf-8")
    disk_hash = compute_hash(disk_content)

    if disk_hash != db_record["content_hash"]:
        return False, "locally_edited"

    if canvas_updated_at and db_record.get("canvas_updated_at"):
        if canvas_updated_at > db_record["canvas_updated_at"]:
            return True, "canvas_updated"

    return False, "no_changes"
