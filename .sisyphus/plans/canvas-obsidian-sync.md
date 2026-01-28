# Canvas-Obsidian Sync Tool

## Context

### Original Request
Create a personal project that collects info about all classes, assignments, tests, modules from Canvas LMS and stores them as notes in Obsidian with smart organization.

### Interview Summary
**Key Discussions**:
- Canvas instance: https://canvas.illinois.edu
- Obsidian vault: `C:\Users\li859\Documents\Personal-projects\canvas-obsidian-sync\Project-obsidian-vault`
- Priority data: Assignments (due dates) → Calendar events (time windows) → Modules/syllabus/announcements/grades
- Course selection: Web GUI to pick specific courses (not all)
- Sync frequency: Daily via Python daemon
- Conflict handling: Skip locally-edited files (preserve user edits)
- API token: First-run prompt → Windows Credential Manager via keyring

**Research Findings**:
- `canvasapi` library: PaginatedList (lazy loading), needs `include` params, manual rate-limit backoff required
- Obsidian: YAML frontmatter with status/due/course/type fields, Dataview plugin for queries

### Metis Review
**Identified Gaps** (addressed):
- Edit detection algorithm: Use content hash stored in SQLite
- Deletion policy: Keep orphaned notes (don't delete when Canvas items removed)
- Timezone handling: Use user's system timezone, store ISO8601 in frontmatter
- Scope creep risk: Lock MVP to assignments + calendar only
- Rate limit strategy: Exponential backoff with max 3 retries

---

## Work Objectives

### Core Objective
Build a Python tool that syncs Canvas LMS data (assignments, calendar events) to Obsidian markdown notes with YAML frontmatter, featuring a web GUI for course selection and daily scheduled sync.

### Concrete Deliverables
- Python package with CLI entry point
- Flask web UI for course selection
- SQLite database for sync state
- Markdown notes in Obsidian vault with Dataview-compatible frontmatter
- Background scheduler for daily sync
- pytest + Playwright test suites

### Definition of Done
- [x] `python -m canvas_sync` launches web UI
- [x] User can authenticate with Canvas API token (stored in keyring)
- [x] User can select courses via web UI
- [x] Sync creates markdown files with correct YAML frontmatter
- [x] Re-running sync skips locally-edited files
- [x] All tests pass: `pytest` (includes Playwright tests via pytest-playwright)

---

## Technical Specifications

### SQLite Schema
Database file: `{vault}/.canvas_sync/sync.db`

**Database Initialization:**
- DB file and tables are created on first access by `src/canvas_sync/db/models.py`
- `init_db(vault_path)` function creates `.canvas_sync/` directory if missing
- Uses `CREATE TABLE IF NOT EXISTS` for idempotent initialization
- Called by: web app on startup, sync functions before first write

```python
# src/canvas_sync/db/models.py
import sqlite3
from pathlib import Path

def get_db_path(vault_path: str) -> Path:
    return Path(vault_path) / ".canvas_sync" / "sync.db"

def init_db(vault_path: str) -> sqlite3.Connection:
    """Initialize database, creating tables if needed.
    
    Called on app startup and before any sync operation.
    Safe to call multiple times (idempotent).
    """
    db_path = get_db_path(vault_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS sync_state (...);
        CREATE TABLE IF NOT EXISTS selected_courses (...);
        CREATE TABLE IF NOT EXISTS config (...);
        CREATE INDEX IF NOT EXISTS idx_sync_canvas ON sync_state(canvas_id, canvas_type);
        CREATE INDEX IF NOT EXISTS idx_sync_course ON sync_state(course_id);
    ''')
    conn.commit()
    return conn

def get_db(vault_path: str) -> sqlite3.Connection:
    """Get database connection. Initializes if needed."""
    return init_db(vault_path)
```

**Shared Access:**
- Web and scheduler run in separate processes → each opens own connection
- SQLite handles concurrent reads; writes are serialized by SQLite's locking
- No connection pooling needed (single-user app)

```sql
-- Tracks sync state for each Canvas item
CREATE TABLE sync_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canvas_id INTEGER NOT NULL,          -- Canvas item ID
    canvas_type TEXT NOT NULL,           -- 'assignment' | 'calendar_event'
    course_id INTEGER NOT NULL,          -- Canvas course ID
    file_path TEXT NOT NULL UNIQUE,      -- Relative path in vault
    content_hash TEXT NOT NULL,          -- SHA256 of markdown content
    canvas_updated_at TEXT,              -- ISO8601 from Canvas API
    synced_at TEXT NOT NULL,             -- ISO8601 of last sync
    UNIQUE(canvas_id, canvas_type)
);

-- Tracks user-selected courses
CREATE TABLE selected_courses (
    course_id INTEGER PRIMARY KEY,
    course_name TEXT NOT NULL,
    selected_at TEXT NOT NULL            -- ISO8601
);

-- Stores app configuration
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- Keys: 'canvas_url', 'sync_time', 'vault_path', 'last_sync_at', 'last_sync_status'

CREATE INDEX idx_sync_canvas ON sync_state(canvas_id, canvas_type);
CREATE INDEX idx_sync_course ON sync_state(course_id);
```

### Module Organization and Imports

**Config/DB Helper Functions Location:**
All config and database functions live in `src/canvas_sync/db/models.py`:

```python
# src/canvas_sync/db/models.py
# Contains: init_db, get_db, get_config, set_config, get_vault_path, get_sync_time,
#           get_selected_courses, set_selected_courses, get_sync_state, set_sync_state

# Other modules import like this:
from canvas_sync.db.models import get_db, get_config, set_config, get_vault_path
```

**Import Map:**
| Function | Defined In | Used By |
|----------|-----------|---------|
| `get_db`, `init_db` | `db/models.py` | All modules needing DB |
| `get_config`, `set_config` | `db/models.py` | `api/auth.py`, `web/app.py`, `scheduler.py` |
| `get_vault_path`, `get_sync_time` | `db/models.py` | `web/app.py`, `scheduler.py`, `sync/*.py` |
| `get_selected_courses` | `db/models.py` | `web/app.py`, `scheduler.py` |
| `get_api_token`, `set_api_token`, `get_canvas_client` | `api/auth.py` | `api/courses.py`, `sync/*.py`, `web/app.py` |
| `sync_assignments` | `sync/assignments.py` | `web/app.py`, `scheduler.py` |
| `sync_calendar_events` | `sync/calendar.py` | `web/app.py`, `scheduler.py` |

### Version Sourcing

**`__version__` is single-sourced from `pyproject.toml` via `importlib.metadata`:**

```python
# src/canvas_sync/__init__.py
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("canvas-sync")
except PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback for development
```

**`pyproject.toml`:**
```toml
[project]
name = "canvas-sync"
version = "0.1.0"
# ... rest of config
```

### Last Sync Status Schema

**Stored in SQLite `config` table as JSON string:**

Key: `last_sync_status`

```python
# Schema for last_sync_status value (JSON)
{
    "started_at": "2026-01-21T06:00:00-06:00",  # ISO8601
    "completed_at": "2026-01-21T06:02:15-06:00",  # ISO8601
    "assignments_synced": 12,
    "events_synced": 5,
    "skipped": 3,
    "errors": [
        "Assignments for CS 101: RateLimitExceeded after 3 retries"
    ],
    "courses_synced": ["CS 101", "MATH 241"]
}
```

**`/status` Route Rendering:**
```python
@app.route("/status")
def status():
    last_sync_at = get_config("last_sync_at")
    last_sync_status = get_config("last_sync_status")
    
    if last_sync_status:
        status_data = json.loads(last_sync_status)
    else:
        status_data = None
    
    return render_template("status.html", 
                           last_sync_at=last_sync_at,
                           status=status_data)
```

### E2E Test Harness

**Flask App Startup for Playwright:**
```python
# tests/e2e/conftest.py
import pytest
import threading
import responses
from canvas_sync.web.app import create_app

@pytest.fixture(scope="session")
def flask_server():
    """Start Flask app in background thread for Playwright tests."""
    app = create_app(testing=True)
    
    # Run Flask in a daemon thread
    server_thread = threading.Thread(
        target=lambda: app.run(port=5001, use_reloader=False, threaded=True)
    )
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to be ready
    import time
    time.sleep(1)
    
    yield "http://localhost:5001"

@pytest.fixture(autouse=True)
def mock_canvas_api():
    """Mock all Canvas API calls for E2E tests."""
    with responses.RequestsMock() as rsps:
        # Mock course list
        rsps.add(
            responses.GET,
            "https://canvas.illinois.edu/api/v1/courses",
            json=[{"id": 123, "name": "CS 101", "course_code": "CS101"}],
            status=200
        )
        # Mock assignments
        rsps.add(
            responses.GET,
            "https://canvas.illinois.edu/api/v1/courses/123/assignments",
            json=[{"id": 456, "name": "HW1", "due_at": "2026-02-15T23:59:00Z", 
                   "points_possible": 100, "html_url": "https://...", "description": "<p>Do homework</p>"}],
            status=200
        )
        # Mock calendar events
        rsps.add(
            responses.GET,
            "https://canvas.illinois.edu/api/v1/calendar_events",
            json=[{"id": 789, "title": "Midterm", "start_at": "2026-03-01T14:00:00Z",
                   "end_at": "2026-03-01T16:00:00Z", "location_name": "Room 100"}],
            status=200
        )
        yield rsps
```

**E2E Test Example:**
```python
# tests/e2e/test_full_flow.py
def test_setup_and_sync(flask_server, page, mock_canvas_api, tmp_path, monkeypatch):
    # Mock keyring to use temp storage
    mock_keyring = {}
    monkeypatch.setattr("keyring.get_password", lambda s, k: mock_keyring.get(f"{s}:{k}"))
    monkeypatch.setattr("keyring.set_password", lambda s, k, v: mock_keyring.update({f"{s}:{k}": v}))
    
    # Navigate to setup
    page.goto(f"{flask_server}/setup")
    page.fill("#api_token", "test-token-123")
    page.click("button[type=submit]")
    
    # Should redirect to courses
    assert "/courses" in page.url
    
    # Select a course
    page.check("input[value='123']")
    page.click("button#save-courses")
    
    # Trigger sync
    page.click("a[href='/sync']")
    
    # Verify status page shows results
    page.goto(f"{flask_server}/status")
    assert "CS 101" in page.content()
    assert "HW1" in page.content() or "1 assignments" in page.content()
```

### Scheduler Time Mocking

**Use `freezegun` library for time mocking:**

```toml
# Add to dev dependencies in pyproject.toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-playwright>=0.4.0",
    "responses>=0.25.0",
    "freezegun>=1.2.0",
]
```

**Scheduler Test with Time Mocking:**
```python
# tests/test_scheduler.py
import pytest
from freezegun import freeze_time
from unittest.mock import patch, MagicMock
from canvas_sync.scheduler import run_daemon, scheduled_sync

@freeze_time("2026-01-21 05:59:00")
def test_scheduler_triggers_at_sync_time():
    """Verify sync triggers at configured time."""
    with patch("canvas_sync.scheduler.get_sync_time", return_value="06:00"):
        with patch("canvas_sync.scheduler.scheduled_sync") as mock_sync:
            with patch("canvas_sync.scheduler.get_selected_courses", return_value=[{"course_id": 123}]):
                import schedule
                
                # Setup scheduler
                schedule.clear()
                schedule.every().day.at("06:00").do(scheduled_sync, "/tmp/vault")
                
                # At 05:59, no sync yet
                schedule.run_pending()
                assert mock_sync.call_count == 0
                
                # Advance to 06:00
                with freeze_time("2026-01-21 06:00:00"):
                    schedule.run_pending()
                    assert mock_sync.call_count == 1

def test_scheduler_graceful_shutdown():
    """Verify SIGTERM causes clean exit."""
    import signal
    import threading
    
    shutdown_called = threading.Event()
    
    def mock_handler(signum, frame):
        shutdown_called.set()
    
    with patch("signal.signal") as mock_signal:
        # Verify signal handlers are registered
        # Implementation should call: signal.signal(signal.SIGTERM, handler)
        pass  # Actual test depends on implementation
```

### Content Hash Algorithm
- **Algorithm**: SHA256
- **Input**: Full markdown file content (frontmatter + body)
- **Comparison**: 
  1. On sync, compute hash of generated markdown
  2. If file exists, compute hash of existing file on disk
  3. Compare disk hash with stored `content_hash` in SQLite
  4. If disk hash ≠ stored hash → file was locally edited → SKIP
  5. If disk hash = stored hash → file unchanged → overwrite if Canvas updated

```python
import hashlib

def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

### Filename Sanitization Rules
```python
import re

def sanitize_filename(name: str) -> str:
    """Convert Canvas item name to safe filename."""
    # Replace invalid chars with underscore
    safe = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Collapse multiple underscores
    safe = re.sub(r'_+', '_', safe)
    # Trim leading/trailing whitespace and underscores
    safe = safe.strip(' _')
    # Truncate to 100 chars (leave room for extension)
    safe = safe[:100]
    # Handle empty result
    return safe or 'untitled'

def get_course_folder_name(course) -> str:
    """Derive folder name from Canvas course object.
    
    Uses course.name (e.g., "CS 101 - Intro to Programming").
    Falls back to course.course_code if name is empty.
    """
    name = getattr(course, 'name', None) or getattr(course, 'course_code', f'course_{course.id}')
    return sanitize_filename(name)

def get_file_path(vault_path: str, course, item_type: str, item_name: str) -> Path:
    """Build full file path for a synced item.
    
    Structure: {vault}/Courses/{course_folder}/{type_folder}/{item_name}.md
    
    Args:
        vault_path: Root vault path
        course: Canvas course object
        item_type: 'Assignments' or 'Events'
        item_name: Canvas item name (will be sanitized)
    
    Returns:
        Path object for the markdown file
    
    Collision handling:
        If file exists with same name but different canvas_id,
        append canvas_id to filename: "Homework 1_12345.md"
    """
    course_folder = get_course_folder_name(course)
    safe_name = sanitize_filename(item_name)
    return Path(vault_path) / "Courses" / course_folder / item_type / f"{safe_name}.md"
```

### YAML Frontmatter Specification

**Assignment frontmatter:**
```yaml
---
type: assignment
course: "CS 101 - Intro to Programming"
course_id: 12345
canvas_id: 67890
due: 2026-02-15T23:59:00-06:00      # null if no due date
points: 100                          # null if ungraded
status: pending                      # Values: pending | submitted | graded
url: https://canvas.illinois.edu/courses/12345/assignments/67890
synced_at: 2026-01-21T06:00:00-06:00
content_hash: abc123...
---
```

**Calendar event frontmatter:**
```yaml
---
type: calendar_event
course: "CS 101 - Intro to Programming"
course_id: 12345
canvas_id: 11111
start: 2026-02-20T14:00:00-06:00    # Required (always present from Canvas)
end: 2026-02-20T15:30:00-06:00      # null if not specified
all_day: false                       # true if start has no time component
location: "Room 1001 Siebel"         # null if not specified
synced_at: 2026-01-21T06:00:00-06:00
content_hash: def456...
---
```

**Edge Case Handling:**
| Field | Missing Value | Behavior |
|-------|---------------|----------|
| `due` | No due date in Canvas | Set to `null` in YAML |
| `points` | Ungraded assignment | Set to `null` |
| `status` | Derive from submission state | See Assignment Status Derivation below |
| `end` | Event has no end time | Set to `null` |
| `all_day` | Check `start_at` format | `true` if time is 00:00:00, `false` otherwise |
| `location` | Not specified | Set to `null` |

### Calendar Event Query Window

**Date Range Rules for `canvas.get_calendar_events()`:**

```python
from datetime import datetime, timedelta

def get_calendar_date_range() -> tuple[str, str]:
    """Get start/end dates for calendar event query.
    
    Window: 30 days ago to 365 days ahead from current date.
    This captures:
    - Recent past events (for reference)
    - Full academic year ahead
    
    Returns:
        (start_date, end_date) as ISO8601 date strings (YYYY-MM-DD)
    """
    today = datetime.now()
    start = today - timedelta(days=30)
    end = today + timedelta(days=365)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

# Usage in sync:
start_date, end_date = get_calendar_date_range()
events = canvas.get_calendar_events(
    context_codes=[f'course_{course_id}'],
    type='event',
    start_date=start_date,
    end_date=end_date
)
```

**Rationale:**
- **30 days back**: Captures recent events for context (exams just taken, etc.)
- **365 days forward**: Covers full academic year including future semesters
- **No term-based logic**: Simpler, avoids needing to parse Canvas term data

### Assignment Status Derivation

**Clarification: "Don't sync submission data" vs "Derive status from submission"**

The guardrail "Don't sync submission data" means:
- ❌ Do NOT store: submission text/content, attachments, comments, attempt history, rubric scores
- ❌ Do NOT store: submission timestamps, grader info, late penalties
- ✅ DO READ (but don't store raw): `workflow_state` and `grade` presence → derive single `status` field

**What we store:** Only the derived `status` string (`pending`/`submitted`/`graded`) - NOT the raw submission object.

**Canvas Submission Fields Used (READ-ONLY for derivation):**
- `assignment.submission` (when `include=['submission']` is passed)
- `submission.workflow_state`: `unsubmitted`, `submitted`, `graded`, `pending_review`
- `submission.grade`: The assigned grade (null if not graded)

**Status Mapping Logic:**
```python
def derive_assignment_status(assignment) -> str:
    """Derive status from Canvas assignment submission data.
    
    Args:
        assignment: Canvas assignment object with submission included
    
    Returns:
        'pending' | 'submitted' | 'graded'
    """
    submission = getattr(assignment, 'submission', None)
    
    if submission is None:
        return 'pending'
    
    workflow_state = getattr(submission, 'workflow_state', 'unsubmitted')
    grade = getattr(submission, 'grade', None)
    
    # Priority: graded > submitted > pending
    if workflow_state == 'graded' or grade is not None:
        return 'graded'
    elif workflow_state in ('submitted', 'pending_review'):
        return 'submitted'
    else:
        return 'pending'
```

**Edge Cases:**
| Canvas State | Our Status | Reason |
|--------------|------------|--------|
| No submission object | `pending` | Never submitted |
| `workflow_state='unsubmitted'` | `pending` | Not yet submitted |
| `workflow_state='submitted'` | `submitted` | Awaiting grading |
| `workflow_state='pending_review'` | `submitted` | Peer review pending |
| `workflow_state='graded'` | `graded` | Has been graded |
| `grade` is not None | `graded` | Even if workflow_state differs |

### Markdown Body Template

**Assignment body:**
```markdown
---
{frontmatter}
---

# {assignment.name}

## Description

{assignment.description | converted from HTML to markdown}

## Details

- **Due**: {due_date formatted as "February 15, 2026 at 11:59 PM" or "No due date"}
- **Points**: {points or "Ungraded"}
- **Submission Types**: {submission_types joined with ", "}

[Open in Canvas]({url})
```

**Calendar event body:**
```markdown
---
{frontmatter}
---

# {event.title}

## When

{start_date formatted as "February 20, 2026 from 2:00 PM to 3:30 PM" or "February 20, 2026 (All Day)"}

## Location

{location or "Not specified"}

## Description

{event.description | converted from HTML to markdown, or "No description provided."}

[Open in Canvas]({url})
```

**HTML to Markdown Conversion:**
```python
from html2text import HTML2Text

def html_to_markdown(html: str) -> str:
    """Convert Canvas HTML content to Obsidian-friendly markdown."""
    if not html:
        return ""
    h = HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # Don't wrap lines
    return h.handle(html).strip()
```

### Vault Path and Sync Time Configuration

**Configuration Flow:**

1. **First Run (Web UI `/setup`):**
   - User enters: Canvas URL, API token
   - Vault path: Auto-detected as `{project_root}/Project-obsidian-vault` (hardcoded default for this project)
   - Sync time: Default `06:00`, changeable via `/settings` page

2. **Settings Page (`GET /settings`):**
   - Shows current vault path, sync time
   - Form to update sync time (dropdown: 00:00 - 23:00)
   - Vault path displayed but not editable via UI (change in SQLite directly if needed)

3. **Storage in SQLite (NO CIRCULAR CALLS):**

**CANONICAL PATTERN - Caller provides vault_path, no auto-connect:**
```python
# All functions require explicit vault_path or connection - NO RECURSION

def get_config(conn: sqlite3.Connection, key: str) -> str | None:
    """Get config value. Caller provides connection."""
    row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None

def set_config(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Set config value. Caller provides connection."""
    conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()

def get_vault_path_from_config(conn: sqlite3.Connection) -> str:
    """Get vault path from DB config, with fallback to constant."""
    from canvas_sync.config import DEFAULT_VAULT_PATH
    path = get_config(conn, "vault_path")
    return path if path else str(DEFAULT_VAULT_PATH)

def get_sync_time_from_config(conn: sqlite3.Connection) -> str:
    """Get sync time from DB config, with fallback to constant."""
    from canvas_sync.config import DEFAULT_SYNC_TIME
    return get_config(conn, "sync_time") or DEFAULT_SYNC_TIME

# USAGE PATTERN (in web/app.py, scheduler.py, etc.):
from canvas_sync.config import DEFAULT_VAULT_PATH
from canvas_sync.db.models import get_db, get_config, get_vault_path_from_config

# Step 1: Open DB with constant default (no recursion)
conn = get_db(str(DEFAULT_VAULT_PATH))

# Step 2: Read actual vault path from config (may differ from default)
vault_path = get_vault_path_from_config(conn)

# Step 3: If vault path differs, reopen DB at correct location
if vault_path != str(DEFAULT_VAULT_PATH):
    conn = get_db(vault_path)
```

### Update/Overwrite Decision Logic

**Canvas `updated_at` Field:**
- Assignments: `assignment.updated_at` (ISO8601 string)
- Calendar events: `event.updated_at` (ISO8601 string)
- Stored in SQLite `sync_state.canvas_updated_at`

**Sync Decision Flowchart:**
```
For each Canvas item:
│
├─ File exists on disk?
│  │
│  ├─ NO → Write new file, insert sync_state
│  │
│  └─ YES → Compute disk_hash = SHA256(file content)
│           │
│           ├─ disk_hash ≠ stored content_hash?
│           │  └─ YES → File locally edited → SKIP, log warning
│           │
│           └─ disk_hash = stored content_hash?
│              │
│              ├─ Canvas updated_at > stored canvas_updated_at?
│              │  └─ YES → Overwrite file, update sync_state
│              │
│              └─ Canvas updated_at ≤ stored canvas_updated_at?
│                 └─ NO change needed → SKIP silently
```

**Implementation:**
```python
def should_sync_item(
    file_path: Path,
    canvas_updated_at: str,
    db_record: dict | None
) -> tuple[bool, str]:
    """Determine if item should be synced.
    
    Returns:
        (should_sync, reason)
    """
    if not file_path.exists():
        return True, "new_file"
    
    if db_record is None:
        # File exists but no DB record - treat as new
        return True, "no_db_record"
    
    disk_content = file_path.read_text(encoding="utf-8")
    disk_hash = compute_hash(disk_content)
    
    if disk_hash != db_record["content_hash"]:
        return False, "locally_edited"
    
    if canvas_updated_at > db_record["canvas_updated_at"]:
        return True, "canvas_updated"
    
    return False, "no_changes"
```

### Sync Orchestrator Flow

**From Web UI (`POST /sync` or `GET /sync`):**
```python
@app.route("/sync", methods=["GET", "POST"])
def sync():
    """Trigger manual sync for selected courses."""
    vault_path = get_vault_path()
    selected = get_selected_courses()  # From SQLite
    
    if not selected:
        flash("No courses selected. Go to Courses to select some.")
        return redirect(url_for("courses"))
    
    results = run_sync(vault_path, selected)
    
    # Store last sync status
    set_config("last_sync_at", datetime.now().isoformat())
    set_config("last_sync_status", json.dumps(results))
    
    return render_template("sync_results.html", results=results)
```

**From Scheduler (`run_daemon()`):**
```python
def run_daemon():
    """Run background sync daemon."""
    vault_path = get_vault_path()
    sync_time = get_sync_time()  # e.g., "06:00"
    
    setup_logging(vault_path)
    logging.info(f"Scheduler started, next sync at {sync_time}")
    
    schedule.every().day.at(sync_time).do(scheduled_sync, vault_path)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def scheduled_sync(vault_path: str):
    """Execute scheduled sync."""
    selected = get_selected_courses()
    if not selected:
        logging.warning("No courses selected, skipping sync")
        return
    
    logging.info(f"Sync started for {len(selected)} courses")
    results = run_sync(vault_path, selected)
    logging.info(f"Synced {results['assignments']} assignments, {results['events']} events")
```

**Core Sync Function:**
```python
def run_sync(vault_path: str, courses: list[dict]) -> dict:
    """Run sync for given courses.
    
    Args:
        vault_path: Path to Obsidian vault
        courses: List of {"course_id": int, "course_name": str}
    
    Returns:
        {"assignments": int, "events": int, "skipped": int, "errors": list}
    """
    results = {"assignments": 0, "events": 0, "skipped": 0, "errors": []}
    
    for course in courses:
        try:
            a_count, a_skipped = sync_assignments(course["course_id"], vault_path)
            results["assignments"] += a_count
            results["skipped"] += a_skipped
        except Exception as e:
            results["errors"].append(f"Assignments for {course['course_name']}: {e}")
    
    # Calendar events fetched across all selected courses at once
    try:
        course_ids = [c["course_id"] for c in courses]
        e_count, e_skipped = sync_calendar_events(course_ids, vault_path)
        results["events"] += e_count
        results["skipped"] += e_skipped
    except Exception as e:
        results["errors"].append(f"Calendar events: {e}")
    
    return results
```

### E2E Test Mocking and UI Dependencies

**Mocking Library:** `responses` (for requests-based HTTP mocking)
```python
# pyproject.toml already includes: responses>=0.25.0
import responses

@responses.activate
def test_full_sync_flow(page):
    # Mock Canvas API endpoints
    responses.add(
        responses.GET,
        "https://canvas.illinois.edu/api/v1/courses",
        json=[{"id": 123, "name": "CS 101"}],
        status=200
    )
    responses.add(
        responses.GET,
        "https://canvas.illinois.edu/api/v1/courses/123/assignments",
        json=[{"id": 456, "name": "HW1", "due_at": "2026-02-15T23:59:00Z"}],
        status=200
    )
    # ... test flow
```

**Bootstrap UI Source:**
```html
<!-- In templates/base.html -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" 
      rel="stylesheet" 
      integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" 
      crossorigin="anonymous">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" 
        integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" 
        crossorigin="anonymous"></script>
```

**Additional Runtime Dependency:**
`html2text` is already included in the main dependencies list above.

### Token Entry Flow

**Web Mode** (`python -m canvas_sync`):
1. Launch Flask web UI on `http://localhost:5000`
2. Check `keyring.get_password("canvas_sync", "api_token")`
3. **If None** → Redirect to `/setup`
4. **`/setup` page**: Form with Canvas URL (prefilled: https://canvas.illinois.edu) and API token field
5. **On submit**: 
   - Store token: `keyring.set_password("canvas_sync", "api_token", token)`
   - Store URL in SQLite config table: `INSERT INTO config VALUES ('canvas_url', url)`
6. **Subsequent runs**: Token retrieved from keyring, URL from SQLite

**Daemon Mode** (`python -m canvas_sync --daemon`):
1. Check `keyring.get_password("canvas_sync", "api_token")`
2. **If None** → Print error: "No API token configured. Run `python -m canvas_sync` first to set up." and exit with code 1
3. **If exists** → Start scheduler loop

**`get_api_token()` Behavior**:
```python
def get_api_token(require: bool = True) -> str | None:
    """Get API token from keyring.
    
    Args:
        require: If True, raise ConfigError when token missing.
                 If False, return None when missing.
    """
    token = keyring.get_password("canvas_sync", "api_token")
    if token is None and require:
        raise ConfigError("No API token configured. Run web UI first.")
    return token
```

**`__main__.py` Routing**:
```python
import argparse
from canvas_sync.web.app import create_app
from canvas_sync.scheduler import run_daemon
from canvas_sync.api.auth import get_api_token, ConfigError

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true", help="Run as background sync daemon")
    args = parser.parse_args()
    
    if args.daemon:
        try:
            get_api_token(require=True)  # Fail fast if not configured
        except ConfigError as e:
            print(f"Error: {e}")
            sys.exit(1)
        run_daemon()
    else:
        app = create_app()
        webbrowser.open("http://localhost:5000")
        app.run(port=5000)
```

### Configuration Storage
- **API Token**: Windows Credential Manager via `keyring` library
- **Canvas URL**: SQLite `config` table (key: `canvas_url`)
- **Sync Time**: SQLite `config` table (key: `sync_time`, default: `06:00`)
- **Vault Path**: SQLite `config` table (key: `vault_path`)
- **Selected Courses**: SQLite `selected_courses` table

### canvasapi Usage Patterns

**Authentication:**
```python
from canvasapi import Canvas

def get_canvas_client() -> Canvas:
    token = keyring.get_password("canvas_sync", "api_token")
    url = get_config("canvas_url")  # From SQLite
    return Canvas(url, token)
```

**Fetching Courses:**
```python
canvas = get_canvas_client()
# Returns PaginatedList - iterates lazily
courses = canvas.get_courses(enrollment_state='active')
for course in courses:
    print(course.id, course.name)
```

**Fetching Assignments:**
```python
course = canvas.get_course(course_id)
assignments = course.get_assignments(
    include=['submission'],  # Include submission status
    order_by='due_at'
)
for a in assignments:
    # a.name, a.due_at, a.points_possible, a.html_url, a.description
```

**Fetching Calendar Events:**
```python
events = canvas.get_calendar_events(
    context_codes=[f'course_{course_id}'],
    type='event',  # Not 'assignment'
    start_date='2026-01-01',
    end_date='2026-12-31'
)
for e in events:
    # e.title, e.start_at, e.end_at, e.location_name, e.description
```

**Rate Limit Handling:**
```python
from canvasapi.exceptions import RateLimitExceeded
import time

def with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitExceeded:
            delay = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(delay)
    raise Exception("Rate limit exceeded after retries")
```

### Must Have
- Canvas API authentication via keyring
- Assignment sync with due dates
- Calendar event sync with start/end times
- Web-based course selection
- SQLite sync state tracking
- Content hash for edit detection
- YAML frontmatter compatible with Dataview

### Must NOT Have (Guardrails)
- NO file/attachment downloads in MVP
- NO quiz content sync
- NO discussion posts
- NO grade modifications (read-only)
- NO bi-directional sync (Canvas → Obsidian only)
- NO modification of `.obsidian/` directory
- NO deletion of notes when Canvas items are removed
- NO over-engineered abstractions - keep it simple
- NO excessive error handling beyond rate limits

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: NO (new project)
- **User wants tests**: TDD
- **Framework**: pytest + Playwright

### TDD Workflow
Each TODO follows RED-GREEN-REFACTOR:
1. **RED**: Write failing test first
2. **GREEN**: Implement minimum code to pass
3. **REFACTOR**: Clean up while keeping green

### Test Setup Task
- [x] 0. Setup Test Infrastructure
  - Install: `pip install pytest pytest-asyncio pytest-playwright responses freezegun`
  - Config: Create `pytest.ini` and `pyproject.toml`
  - Playwright: `playwright install chromium`
  - Verify: `pytest --version` → shows version
  - Example: Create `tests/test_example.py`
  - Verify: `pytest tests/test_example.py` → 1 test passes

**Runtime Dependencies** (declared in `pyproject.toml`):
```toml
[project]
dependencies = [
    "canvasapi>=3.0.0",
    "keyring>=24.0.0",
    "flask>=3.0.0",
    "schedule>=1.2.0",
    "html2text>=2024.2.26",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-playwright>=0.4.0",
    "responses>=0.25.0",
]
```

---

## Task Flow

```
0 (Test Setup) → 1 (Project Structure + DB/Config Module)
                      ↓
              2 (Canvas Auth) → 3 (Course Fetching)
                                      ↓
                              4 (Assignment Sync) → 5 (Calendar Sync)
                                                          ↓
                                                  6 (Web UI) → 7 (Scheduler)
                                                                    ↓
                                                              8 (E2E Tests)
```

**IMPORTANT: Task 1 now includes DB/Config module creation** to resolve dependency ordering. Tasks 2-3 can then import from `db/models.py`.

## Parallelization

| Group | Tasks | Reason |
|-------|-------|--------|
| A | 4, 5 | Independent sync logic after course fetching works |

| Task | Depends On | Reason |
|------|------------|--------|
| 1 | 0 | Need test infra before structure |
| 2 | 1 | Need project structure |
| 3 | 2 | Need auth before fetching |
| 4 | 3 | Need courses before assignments |
| 5 | 3 | Need courses before calendar |
| 6 | 4, 5 | Need sync logic before UI |
| 7 | 6 | Need UI before scheduler |
| 8 | 7 | Need full app before E2E |

---

## TODOs

- [x] 0. Setup Test Infrastructure

  **What to do**:
  - Create `pyproject.toml` with pytest, playwright dependencies
  - Create `pytest.ini` with test discovery settings
  - Install Playwright browsers: `playwright install chromium`
  - Create example test to verify setup works

  **Must NOT do**:
  - Don't add unnecessary test plugins
  - Don't configure coverage yet (add later if needed)

  **Parallelizable**: NO (must be first)

  **References**:
  - pytest docs: https://docs.pytest.org/en/stable/getting-started.html
  - Playwright Python: https://playwright.dev/python/docs/intro

  **Acceptance Criteria**:
  - [ ] `pyproject.toml` exists with `[project]` and `[tool.pytest.ini_options]`
  - [ ] `pytest.ini` exists
  - [ ] `tests/test_example.py` exists with one passing test
  - [ ] `pytest` → 1 passed
  - [ ] `playwright install chromium` → completes without error

  **Commit**: YES
  - Message: `chore: setup pytest and playwright test infrastructure`
  - Files: `pyproject.toml`, `pytest.ini`, `tests/test_example.py`

---

- [x] 1. Create Project Structure + DB/Config Module

  **What to do**:
  - Create Python package structure: `src/canvas_sync/`
  - Create `__init__.py` with `__version__` via `importlib.metadata`
  - Create `__main__.py` for CLI entry
  - Create subdirectories: `api/`, `sync/`, `web/`, `db/`
  - **Create `src/canvas_sync/db/models.py`** with:
    - `init_db()`, `get_db()` functions
    - `get_config()`, `set_config()` functions  
    - `get_vault_path()`, `get_sync_time()` functions
    - SQLite schema creation (all tables)
  - Create `config.py` for constants (default vault path, default sync time)
  - Write test for package import

  **Config Bootstrap Order** (resolves circular dependency):
  ```python
  # src/canvas_sync/config.py - Constants only, no DB access
  from pathlib import Path
  
  DEFAULT_VAULT_PATH = Path(__file__).parent.parent.parent / "Project-obsidian-vault"
  DEFAULT_SYNC_TIME = "06:00"
  DEFAULT_CANVAS_URL = "https://canvas.illinois.edu"
  
  # src/canvas_sync/db/models.py - DB access with fallbacks
  from canvas_sync.config import DEFAULT_VAULT_PATH, DEFAULT_SYNC_TIME
  
  def get_vault_path(conn: sqlite3.Connection | None = None) -> str:
      """Get vault path. Uses default if DB not yet initialized."""
      if conn is None:
          # Bootstrap mode - use default
          return str(DEFAULT_VAULT_PATH)
      row = conn.execute("SELECT value FROM config WHERE key = 'vault_path'").fetchone()
      return row["value"] if row else str(DEFAULT_VAULT_PATH)
  
  def get_db(vault_path: str | None = None) -> sqlite3.Connection:
      """Get DB connection. Creates DB if needed."""
      if vault_path is None:
          vault_path = str(DEFAULT_VAULT_PATH)
      return init_db(vault_path)
  ```

  **Must NOT do**:
  - Don't implement sync logic yet
  - Don't add unnecessary files

  **Parallelizable**: NO (depends on 0)

  **References**:
  - Python packaging: https://packaging.python.org/en/latest/tutorials/packaging-projects/
  - importlib.metadata: https://docs.python.org/3/library/importlib.metadata.html

  **Acceptance Criteria**:
  - [ ] RED: `tests/test_structure.py` - test `from canvas_sync import __version__` fails
  - [ ] GREEN: Create package, test passes
  - [ ] `python -m canvas_sync --help` → shows help (argparse stub)
  - [ ] `from canvas_sync.db.models import get_db, get_config` → imports work
  - [ ] `get_db()` creates `.canvas_sync/sync.db` with all tables
  - [ ] Directory structure matches:
    ```
    src/canvas_sync/
    ├── __init__.py
    ├── __main__.py
    ├── config.py
    ├── api/
    ├── sync/
    ├── web/
    └── db/
        └── models.py
    ```

  **Commit**: YES
  - Message: `feat: create initial project structure with DB/config module`
  - Files: `src/canvas_sync/**`

---

- [x] 2. Implement Canvas Authentication

  **What to do**:
  - Create `src/canvas_sync/api/auth.py`
  - Implement `get_api_token(require=True)` - retrieves from keyring, raises `ConfigError` if missing and `require=True`, returns `None` if missing and `require=False`
  - Implement `set_api_token(token)` - stores token in keyring (called by web UI `/setup`)
  - Implement `get_canvas_client()` - returns authenticated canvasapi.Canvas instance
  - Use `keyring` library for Windows Credential Manager
  - Write tests with mocked keyring
  
  **Note**: This module does NOT prompt for input. Token entry is handled by the web UI `/setup` route. The auth module only retrieves/stores tokens.

  **Must NOT do**:
  - Don't store token in plaintext files
  - Don't hardcode Canvas URL (use config)

  **Parallelizable**: NO (depends on 1)

  **References**:
  
  **canvasapi Authentication Pattern:**
  ```python
  from canvasapi import Canvas
  canvas = Canvas("https://canvas.illinois.edu", "YOUR_API_TOKEN")
  ```
  
  **keyring Storage Pattern:**
  ```python
  import keyring
  keyring.set_password("canvas_sync", "api_token", token)
  token = keyring.get_password("canvas_sync", "api_token")
  ```

  **Acceptance Criteria**:
  - [ ] RED: `tests/test_auth.py` - test token retrieval fails
  - [ ] GREEN: Implement auth module, tests pass
  - [ ] `keyring.get_password("canvas_sync", "api_token")` works after first run
  - [ ] `get_canvas_client()` returns valid Canvas instance
  - [ ] `pytest tests/test_auth.py` → all pass (mocked keyring)

  **Commit**: YES
  - Message: `feat(api): implement Canvas authentication with keyring storage`
  - Files: `src/canvas_sync/api/auth.py`, `tests/test_auth.py`

---

- [x] 3. Implement Course Fetching

  **What to do**:
  - Create `src/canvas_sync/api/courses.py`
  - Implement `get_all_courses()` - fetches all courses for user
  - Implement `get_course_details(course_id)` - fetches single course with syllabus
  - Handle pagination (canvasapi does this automatically)
  - Add rate limit handling with exponential backoff
  - Write tests with mocked Canvas API

  **Must NOT do**:
  - Don't filter courses yet (UI does that)
  - Don't fetch assignments/calendar here

  **Parallelizable**: NO (depends on 2)

  **References**:
  
  **canvasapi Course Fetching:**
  ```python
  canvas = get_canvas_client()
  courses = canvas.get_courses(enrollment_state='active')  # PaginatedList
  course = canvas.get_course(course_id, include=['syllabus_body', 'term'])
  ```
  
  **Rate Limit Exception:**
  ```python
  from canvasapi.exceptions import RateLimitExceeded
  # Catch and retry with exponential backoff (1s, 2s, 4s)
  ```

  **Acceptance Criteria**:
  - [ ] RED: `tests/test_courses.py` fails
  - [ ] GREEN: Implement, tests pass
  - [ ] `get_all_courses()` returns list of course objects
  - [ ] Rate limit backoff: 3 retries with 1s, 2s, 4s delays
  - [ ] `pytest tests/test_courses.py` → all pass

  **Commit**: YES
  - Message: `feat(api): implement course fetching with rate limit handling`
  - Files: `src/canvas_sync/api/courses.py`, `tests/test_courses.py`

---

- [x] 4. Implement Assignment Sync

  **What to do**:
  - Create `src/canvas_sync/sync/assignments.py`
  - Create `src/canvas_sync/db/models.py` with SQLite schema
  - Implement `sync_assignments(course_id, vault_path)`:
    - Fetch assignments from Canvas
    - For each assignment:
      - Generate markdown with YAML frontmatter
      - Check if local file exists and was edited (hash comparison)
      - Skip if edited, write if new or unchanged
      - Update SQLite sync state
  - YAML frontmatter fields: `type`, `course`, `course_id`, `canvas_id`, `due`, `points`, `status`, `url`, `synced_at`, `content_hash`

  **Must NOT do**:
  - Don't download attachments
  - Don't sync submission data
  - Don't delete files when assignments removed

  **Parallelizable**: YES (with task 5, after task 3)

  **References**:
  
  **canvasapi Assignment Fetching:**
  ```python
  course = canvas.get_course(course_id)
  assignments = course.get_assignments(include=['submission'], order_by='due_at')
  # Fields: a.name, a.due_at, a.points_possible, a.html_url, a.description
  ```
  
  **SQLite Schema** (see Technical Specifications section above)
  
  **Content Hash** (see Technical Specifications - SHA256 of full markdown)
  
  **Filename Sanitization** (see Technical Specifications - regex replacement)

  **Acceptance Criteria**:
  - [ ] RED: `tests/test_assignment_sync.py` fails
  - [ ] GREEN: Implement, tests pass
  - [ ] Markdown file created at `{vault}/Courses/{course_name}/Assignments/{assignment_name}.md`
  - [ ] YAML frontmatter contains all required fields
  - [ ] Re-run sync: unchanged files skipped (hash match)
  - [ ] Locally edited file: skipped (hash mismatch logged)
  - [ ] SQLite contains sync record with `content_hash`, `synced_at`
  - [ ] `pytest tests/test_assignment_sync.py` → all pass

  **Commit**: YES
  - Message: `feat(sync): implement assignment sync with edit detection`
  - Files: `src/canvas_sync/sync/assignments.py`, `src/canvas_sync/db/models.py`, `tests/test_assignment_sync.py`

---

- [x] 5. Implement Calendar Event Sync

  **What to do**:
  - Create `src/canvas_sync/sync/calendar.py`
  - Implement `sync_calendar_events(course_ids, vault_path)`:
    - Fetch calendar events for selected courses
    - Filter to course events only (not personal)
    - Generate markdown with time window in frontmatter
    - Same skip-if-edited logic as assignments
  - YAML frontmatter fields: `type`, `course`, `course_id`, `canvas_id`, `start`, `end`, `all_day`, `location`, `synced_at`, `content_hash`

  **Must NOT do**:
  - Don't sync personal calendar events
  - Don't handle recurring events specially (treat as individual)

  **Parallelizable**: YES (with task 4, after task 3)

  **References**:
  
  **canvasapi Calendar Events:**
  ```python
  events = canvas.get_calendar_events(
      context_codes=[f'course_{course_id}'],
      type='event',
      start_date='2026-01-01',
      end_date='2026-12-31'
  )
  # Fields: e.title, e.start_at, e.end_at, e.location_name, e.description
  ```

  **Acceptance Criteria**:
  - [ ] RED: `tests/test_calendar_sync.py` fails
  - [ ] GREEN: Implement, tests pass
  - [ ] Markdown file at `{vault}/Courses/{course_name}/Events/{event_title}.md`
  - [ ] YAML frontmatter contains `start`, `end` in ISO8601 format
  - [ ] Skip-if-edited logic works
  - [ ] `pytest tests/test_calendar_sync.py` → all pass

  **Commit**: YES
  - Message: `feat(sync): implement calendar event sync`
  - Files: `src/canvas_sync/sync/calendar.py`, `tests/test_calendar_sync.py`

---

- [x] 6. Implement Web UI for Course Selection

  **What to do**:
  - Create `src/canvas_sync/web/app.py` with Flask app
  - Create `src/canvas_sync/web/templates/` with Jinja2 templates
  - Implement routes:
    - `GET /` - Home page, redirects to setup or dashboard
    - `GET /setup` - First-run token setup form
    - `POST /setup` - Save token to keyring, URL to SQLite
    - `GET /courses` - List all courses with checkboxes
    - `POST /courses` - Save selected courses to SQLite
    - `GET /sync` - Trigger manual sync, show progress
    - `GET /status` - Show last sync status
    - `GET /settings` - Show current settings (vault path, sync time)
    - `POST /settings` - Update sync time
  - Store selected courses in SQLite

  **Course Selection Persistence Rules:**
  - **Replace, not merge**: Each `POST /courses` submission replaces all previous selections
  - **Deselection**: Unchecking a course removes it from `selected_courses` table
  - **Implementation**:
    ```python
    def set_selected_courses(course_ids: list[int], courses_data: list[dict]):
        """Replace all selected courses with new selection.
        
        Args:
            course_ids: List of selected course IDs
            courses_data: List of {"id": int, "name": str} for selected courses
        """
        conn = get_db()
        conn.execute("DELETE FROM selected_courses")  # Clear all
        for course in courses_data:
            if course["id"] in course_ids:
                conn.execute(
                    "INSERT INTO selected_courses (course_id, course_name, selected_at) VALUES (?, ?, ?)",
                    (course["id"], course["name"], datetime.now().isoformat())
                )
        conn.commit()
    ```
  - **Acceptance criteria**: After saving, only selected courses appear in sync

  **Must NOT do**:
  - Don't over-engineer the UI (simple Bootstrap is fine)
  - Don't add authentication to web UI (local use only)

  **Parallelizable**: NO (depends on 4, 5)

  **References**:
  - Flask: https://flask.palletsprojects.com/
  - Bootstrap 5 CDN for styling

  **Acceptance Criteria**:
  - [ ] RED: `tests/test_web.py` with Flask test client fails
  - [ ] GREEN: Implement routes, tests pass
  - [ ] `python -m canvas_sync` → opens browser to `http://localhost:5000`
  - [ ] First run: shows token setup form
  - [ ] After setup: shows course list with checkboxes
  - [ ] Select courses → triggers sync for selected only
  - [ ] Playwright: Navigate to `/courses`, select 2 courses, click sync, verify status

  **Commit**: YES
  - Message: `feat(web): implement Flask UI for course selection and sync`
  - Files: `src/canvas_sync/web/**`, `tests/test_web.py`

---

- [x] 7. Implement Background Scheduler

  **What to do**:
  - Create `src/canvas_sync/scheduler.py`
  - Use `schedule` library for in-process scheduling
  - Implement daemon mode: `python -m canvas_sync --daemon`
  - Schedule daily sync at configurable time (default: 6:00 AM)
  - Log sync results to file
  - Handle graceful shutdown (SIGTERM/SIGINT)

  **Scheduler Logging:**
  - Log file: `{vault}/.canvas_sync/sync.log`
  - Format: `%(asctime)s - %(levelname)s - %(message)s`
  - Log entries:
    - `INFO: Scheduler started, next sync at {time}`
    - `INFO: Sync started for {n} courses`
    - `INFO: Synced {n} assignments, {m} events`
    - `WARNING: Skipped {file} (locally edited)`
    - `ERROR: Sync failed: {error}`
  
  ```python
  import logging
  from pathlib import Path
  
  def setup_logging(vault_path: str):
      log_path = Path(vault_path) / ".canvas_sync" / "sync.log"
      log_path.parent.mkdir(parents=True, exist_ok=True)
      logging.basicConfig(
          filename=str(log_path),
          level=logging.INFO,
          format='%(asctime)s - %(levelname)s - %(message)s'
      )
  ```

  **Must NOT do**:
  - Don't use Windows Task Scheduler (user chose Python daemon)
  - Don't run sync on startup (wait for scheduled time)

  **Parallelizable**: NO (depends on 6)

  **References**:
  - schedule library: https://schedule.readthedocs.io/

  **Acceptance Criteria**:
  - [ ] RED: `tests/test_scheduler.py` fails
  - [ ] GREEN: Implement, tests pass
  - [ ] `python -m canvas_sync --daemon` → runs in foreground, logs activity
  - [ ] Mock time: verify sync triggers at scheduled time
  - [ ] SIGTERM: graceful shutdown within 5 seconds
  - [ ] `pytest tests/test_scheduler.py` → all pass

  **Commit**: YES
  - Message: `feat: implement background scheduler for daily sync`
  - Files: `src/canvas_sync/scheduler.py`, `tests/test_scheduler.py`

---

- [x] 8. Implement E2E Tests with Playwright

  **What to do**:
  - Create `tests/e2e/test_full_flow.py`
  - Test complete user journey:
    1. Launch app
    2. Enter API token
    3. Select courses
    4. Trigger sync
    5. Verify markdown files created
  - Use mock Canvas API responses with `responses` library

  **Must NOT do**:
  - Don't hit real Canvas API in tests
  - Don't test scheduler in E2E (unit tests cover that)

  **Parallelizable**: NO (final task)

  **References**:
  - Playwright Python: https://playwright.dev/python/

  **Acceptance Criteria**:
  - [ ] `tests/e2e/test_full_flow.py` exists
  - [ ] Mocked Canvas API returns sample courses/assignments
  - [ ] Playwright navigates full flow: setup → courses → sync
  - [ ] Verify: markdown files exist in vault with correct frontmatter
  - [ ] `pytest tests/e2e/` → all pass

  **Commit**: YES
  - Message: `test: add Playwright E2E tests for full sync flow`
  - Files: `tests/e2e/**`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 0 | `chore: setup pytest and playwright test infrastructure` | pyproject.toml, pytest.ini, tests/ | pytest |
| 1 | `feat: create initial project structure` | src/canvas_sync/** | pytest |
| 2 | `feat(api): implement Canvas authentication with keyring storage` | api/auth.py, tests/ | pytest |
| 3 | `feat(api): implement course fetching with rate limit handling` | api/courses.py, tests/ | pytest |
| 4 | `feat(sync): implement assignment sync with edit detection` | sync/assignments.py, db/, tests/ | pytest |
| 5 | `feat(sync): implement calendar event sync` | sync/calendar.py, tests/ | pytest |
| 6 | `feat(web): implement Flask UI for course selection and sync` | web/**, tests/ | pytest + playwright |
| 7 | `feat: implement background scheduler for daily sync` | scheduler.py, tests/ | pytest |
| 8 | `test: add Playwright E2E tests for full sync flow` | tests/e2e/** | playwright test |

---

## Success Criteria

### Verification Commands
```bash
# All unit tests pass
pytest

# Playwright E2E tests pass
pytest tests/e2e/

# App launches
python -m canvas_sync --help

# Web UI accessible
python -m canvas_sync  # Opens http://localhost:5000

# Daemon mode
python -m canvas_sync --daemon
```

### Final Checklist
- [x] All "Must Have" features implemented
- [x] All "Must NOT Have" guardrails respected
- [x] All pytest tests pass (includes Playwright E2E via pytest-playwright)
- [x] Git: Clean commit history with conventional commits

---

## TODOs Appendix: Task 9 - README Documentation

- [x] 9. Create README.md Documentation

  **What to do**:
  - Create `README.md` in project root
  - Include: Project overview, installation, setup (API token), usage, development

  **Must NOT do**:
  - Don't over-document (keep concise)

  **Parallelizable**: YES (can be done alongside task 8)

  **Acceptance Criteria**:
  - [ ] `README.md` exists with sections: Overview, Installation, Setup, Usage, Development
  - [ ] Setup section explains how to get Canvas API token
  - [ ] Usage section shows CLI commands

  **Commit**: YES
  - Message: `docs: add README with setup and usage instructions`
  - Files: `README.md`
