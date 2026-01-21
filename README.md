# Canvas-Obsidian Sync

Sync Canvas LMS data (assignments, calendar events) to Obsidian markdown notes with YAML frontmatter.

## Features

- 🔐 Secure API token storage via Windows Credential Manager
- 📚 Web UI for course selection
- 📝 Assignment sync with Dataview-compatible frontmatter
- 📅 Calendar event sync with time windows
- 🔄 Edit detection - skips locally modified files
- ⏰ Daily scheduled sync via background daemon

## Installation

```bash
# Clone repository
git clone https://github.com/Gladdonilli/Gladdon-s-solution-to-education.git
cd canvas-obsidian-sync

# Install with dev dependencies
pip install -e ".[dev]"

# Install Playwright browsers (for E2E tests)
playwright install chromium
```

## Setup

### Get Canvas API Token

1. Log into Canvas at https://canvas.illinois.edu
2. Go to **Account** → **Settings**
3. Scroll to **Approved Integrations**
4. Click **+ New Access Token**
5. Enter a purpose (e.g., "Obsidian Sync") and generate
6. Copy the token (you won't see it again)

### First Run

```bash
python -m canvas_sync
```

This opens the web UI at http://localhost:5000 where you can:
1. Enter your Canvas API token
2. Select courses to sync
3. Trigger manual sync

## Usage

### Web UI Mode (default)
```bash
python -m canvas_sync
```
Opens browser to http://localhost:5000

### Daemon Mode (background sync)
```bash
python -m canvas_sync --daemon
```
Runs daily sync at configured time (default: 6:00 AM)

### Show Version
```bash
python -m canvas_sync --version
```

## Synced Files

Files are created in your Obsidian vault:
```
Project-obsidian-vault/
└── Courses/
    └── CS 101 - Intro to Programming/
        ├── Assignments/
        │   └── Homework 1.md
        └── Events/
            └── Midterm Exam.md
```

### YAML Frontmatter

Assignments include:
```yaml
type: assignment
course: CS 101
due: 2026-02-15T23:59:00Z
points: 100
status: pending  # pending | submitted | graded
```

Calendar events include:
```yaml
type: calendar_event
course: CS 101
start: 2026-03-01T14:00:00Z
end: 2026-03-01T16:00:00Z
location: Room 100
```

## Development

### Run Tests
```bash
# All tests
pytest

# Unit tests only
pytest tests/ --ignore=tests/e2e

# E2E tests with Playwright
pytest tests/e2e/
```

### Project Structure
```
src/canvas_sync/
├── api/          # Canvas API client
├── db/           # SQLite models
├── sync/         # Sync logic
├── web/          # Flask UI
└── scheduler.py  # Background daemon
```

## License

MIT
