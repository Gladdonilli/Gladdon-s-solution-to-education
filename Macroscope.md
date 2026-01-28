# Macroscope Configuration

> Single source of truth for AI PR review bots (Macroscope + Greptile).
> Both bots read this file to understand project conventions.

---

## Project Context

- **Stack**: Python + Flask + canvasapi + SQLite
- **Developer**: Solo developer, high-velocity workflow
- **Philosophy**: "Silent Sentinel" - only alert on high-confidence issues

---

## Python Trust Rules

Python's type hints and runtime behavior are well-understood. Do NOT flag:

- Missing type hints on internal/private functions
- Optional types with proper `if x is not None` guards
- Dynamic attribute access that is intentional (e.g., `getattr()`)

**Only flag type issues when**:
- Public API exports use overly loose types (`Any` everywhere)
- Type assertions hide actual mismatches
- `# type: ignore` suppresses real errors

---

## Focus Areas (DO Flag)

### Critical (Always Report)
- **Security vulnerabilities**: SQL injection, exposed API tokens, path traversal
- **Runtime crashes**: Unhandled exceptions, None access without guards
- **Data corruption**: Race conditions, incorrect state mutations
- **Infinite loops**: Unbounded recursion, missing loop termination

### Important (Report if High Confidence)
- **Canvas API patterns**:
  - Missing error handling for API calls
  - Unvalidated user input to Canvas API
  - Token exposure in logs or error messages
- **Async safety**:
  - Blocking I/O in async context
  - Unhandled errors in async functions
- **File operations**:
  - Missing file existence checks
  - Unclosed file handles
  - Path injection vulnerabilities

---

## Ignore Rules (Do NOT Flag)

### Style & Formatting
- Indentation, quotes (handled by Black/Ruff)
- Line length, trailing commas
- Import ordering (handled by isort)
- Naming conventions debates

### Low-Value Suggestions
- "Consider using X instead of Y" without clear benefit
- Refactoring suggestions that don't fix bugs
- Adding comments to self-documenting code
- Splitting functions that are already readable

### Intentional Patterns
- Empty except blocks with explicit `# intentionally empty` comment
- print() in CLI/debug code
- TODO/FIXME comments (tracked separately)

---

## File-Specific Rules

### `src/canvas_sync/api/**/*.py` (Canvas API)
- All API calls MUST have try/except error handling
- API tokens must never be logged or exposed
- Rate limiting considerations for batch operations

### `src/canvas_sync/sync/**/*.py` (Sync Logic)
- File operations must check for existence before write
- Database operations must use transactions where appropriate
- Web scraping must handle HTTP errors gracefully

### `src/canvas_sync/web/**/*.py` (Flask Routes)
- All routes must validate input
- Error responses must not leak internal details
- Session/auth handling must be secure

### `tests/**/*.py` (Tests)
- Do NOT review test files for code quality
- Only flag if tests have obvious logic errors

### `*.json`, `*.toml`, `*.yaml` (Config)
- Only flag security issues (exposed secrets)
- Do NOT suggest config restructuring

---

## Severity Mapping

| Bot Severity | Action |
|--------------|--------|
| Critical/High | MUST address before merge |
| Medium | SHOULD address, can defer with reason |
| Low/Info | OPTIONAL, author decides |

---

## False Positive Patterns

If the bot flags these, it's misconfigured:

| Pattern | Why It's Intentional |
|---------|---------------------|
| `getattr()` with default | Dynamic attribute access with fallback |
| `# type: ignore` with comment | Documented type system limitation |
| `Any` in test mocks | Test flexibility, not production code |
| `eval()` in build scripts | Build-time only, not runtime |
| Empty `except Exception` with logging | Catch-all with proper logging |

---

## Learning Log

> Update this section when bots catch real issues or produce false positives.

### Bot Caught Real Issue
<!-- Example:
- 2026-02-02: Greptile caught missing error handling in Canvas API call
  - Added to API handler rules above
-->

### False Positives Fixed
<!-- Example:
- 2026-02-02: Macroscope flagged intentional empty except
  - Added "intentionally empty" comment pattern to Ignore Rules
-->
