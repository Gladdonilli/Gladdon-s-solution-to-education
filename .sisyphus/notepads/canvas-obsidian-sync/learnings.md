# Learnings - Canvas-Obsidian-Sync

## 2026-01-20 Implementation Session

### Patterns Discovered
- `importlib.metadata.version()` for single-sourced `__version__` from pyproject.toml
- Flask test client works well with `patch()` for mocking external dependencies
- `schedule` library with `freezegun` requires manually setting `job.next_run` to past time for testing
- YAML serialization quotes ISO8601 date strings - test assertions should use `in content` not exact match

### Successful Approaches
- TDD workflow (RED→GREEN→REFACTOR) ensured all features were testable
- Mocking `keyring` for auth tests avoids Windows Credential Manager in CI
- Using `sqlite3.Row` factory enables dict-style access to query results
- `html2text` library handles Canvas HTML→Markdown conversion cleanly

### Technical Gotchas
- Playwright `get_by_text()` can match multiple elements - use specific locators like `#id` or `to_have_value()`
- Flask's `url_for()` needs app context - use `redirect(url_for("route_name"))`
- SQLite connections should be closed after use in web routes (not pooled for single-user app)
- `canvasapi` returns `PaginatedList` - wrap with `list()` for immediate evaluation

### Conventions Used
- All DB functions take explicit `vault_path` or `conn` parameter to avoid circular imports
- Config constants in `config.py`, DB-backed config functions in `db/models.py`
- Test classes grouped by function/route being tested
- E2E tests use module-scoped Flask server fixture for performance
