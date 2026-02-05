# CANVAS-OBSIDIAN-SYNC

**Updated:** 2026-02-02
**Commit:** 2eec5193
**Branch:** master

## OVERVIEW

Sync Canvas LMS assignments/events to Obsidian markdown with YAML frontmatter. Includes CS 225 web scraping (non-Canvas course), daily auto-update with TODO generation, and Windows startup integration.

## STRUCTURE

```
src/canvas_sync/
├── api/              # Canvas API client (auth.py, courses.py)
├── db/               # SQLite models (sync state tracking)
├── sync/
│   ├── assignments.py    # Assignment sync with YAML frontmatter
│   ├── calendar.py       # Calendar event sync
│   ├── daily_update.py   # Daily orchestration + TODO generation
│   └── documents.py      # Document sync (Canvas files + CS 225 scraping)
├── web/              # Flask UI (course selection, manual sync)
├── scheduler.py      # Background daemon (daily sync)
├── config.py         # Constants only - no DB access
└── __main__.py       # CLI entry point

Project-obsidian-vault/UIUC education/
├── TODO.md           # Interactive checklist (auto-generated)
├── CS 225/           # Assignment markdown files
├── STAT 410/         # Homework files
└── SPED 117/         # Weekly task files

stat 410/             # Course materials (PDFs by week)
sped 117/             # Course materials (readings, transcripts)
cs 225/               # Course materials (labs, mps, lectures)

tests/
├── e2e/              # Playwright browser tests
└── test_*.py         # Unit tests (pytest)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| API auth/token | `api/auth.py` | Uses Windows keyring |
| Assignment sync | `sync/assignments.py` | YAML frontmatter generation |
| Document sync | `sync/documents.py` | Canvas files + CS 225 scraping |
| Daily update | `sync/daily_update.py` | Orchestrates full sync + TODO |
| Web routes | `web/app.py` | Flask, port 5000 |
| Database | `db/models.py` | SQLite, sync state |
| CLI modes | `__main__.py` | `--update`, `--docs`, `--daemon` |
| Config constants | `config.py` | Vault path, Canvas URL |
| Windows startup | `startup_sync.bat` | Runs on login |

## COMMANDS

```bash
# Install
pip install -e ".[dev]"
playwright install chromium

# Run
python -m canvas_sync              # Web UI at localhost:5000
python -m canvas_sync --daemon     # Background sync daemon
python -m canvas_sync --update     # Full daily update (assignments + docs + TODO)
python -m canvas_sync --docs       # Document sync only

# Windows Startup (run once as admin)
powershell -ExecutionPolicy Bypass -File setup_startup.ps1

# Test
pytest                             # All tests
pytest tests/ --ignore=tests/e2e   # Unit only
pytest tests/e2e/                  # E2E with Playwright
```

## COURSES

| Course | Source | Sync Method | Output |
|--------|--------|-------------|--------|
| STAT 410 | Canvas (ID: 65270) | Canvas API files | `stat 410/week N/` PDFs |
| SPED 117 | Canvas (ID: 64369) | Canvas API modules | `sped 117/week N/` pages |
| CS 225 | Web scraping | HTTP requests to course site | `cs 225/` labs/mps/lectures |

### SPED 117 Pattern
- User is in **Group D**
- Discussions are group-level, not course-level
- Check "Week N Overview" page for exact weekly tasks
- Each week: Overview → Readings → Discussion (original) → Discussion (replies) → Assignment

## CONVENTIONS

- **Entry point**: `python -m canvas_sync` (web UI) or `--update` (daily sync)
- **Config separation**: `config.py` = constants only, DB access in `db/models.py`
- **Vault path**: `Project-obsidian-vault/` relative to project root
- **Canvas URL**: `https://canvas.illinois.edu` (hardcoded default)
- **CS 225 URL**: `https://courses.grainger.illinois.edu/cs225/sp2026/`
- **Test naming**: `test_*.py`, functions `test_*`

## ANTI-PATTERNS

- **Never** access DB from `config.py` - use `db/models.py`
- **Never** hardcode API tokens - use keyring via `api/auth.py`
- **Never** commit large PDFs (>1MB) - add to `.gitignore`
- **Never** commit `__pycache__/` or `.pyc` files

## STACK

- Python 3.11+
- canvasapi (Canvas LMS client)
- Flask (web UI)
- keyring (secure token storage)
- schedule (daemon timing)
- html2text (HTML→Markdown)
- pytest + pytest-playwright (testing)

## NOTES

- First run prompts for Canvas API token via web UI
- Sync skips locally-modified files (edit detection)
- Default sync time: 06:00 daily (daemon mode)
- Output: YAML frontmatter compatible with Obsidian Dataview
- TODO.md uses interactive checkboxes (`- [ ]`)
- Windows startup runs `--update` and opens TODO.md in Obsidian
