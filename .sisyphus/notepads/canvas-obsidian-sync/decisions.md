# Decisions - Canvas-Obsidian-Sync

## 2026-01-20 Implementation Session

### Architecture Decisions

1. **SQLite for sync state** - Single-user app doesn't need Postgres. SQLite file lives in vault's `.canvas_sync/` directory.

2. **keyring for token storage** - Uses Windows Credential Manager via `keyring` library. Secure, no plaintext files.

3. **Flask over FastAPI** - Simpler for basic web UI with forms. No async complexity needed.

4. **schedule library over Windows Task Scheduler** - User chose Python daemon, keeps everything in Python ecosystem.

5. **Content hash for edit detection** - SHA256 of full markdown (frontmatter + body). Comparing disk hash vs stored hash detects local edits.

6. **No deletion policy** - Orphaned notes kept when Canvas items removed. User explicitly requested this.

7. **Module structure** - `api/` for Canvas client, `db/` for SQLite, `sync/` for sync logic, `web/` for Flask UI.
