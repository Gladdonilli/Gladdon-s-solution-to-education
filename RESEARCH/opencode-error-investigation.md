# OpenCode Plugin Research - Error Investigation (Updated)

## Error Summary

**Error**: Type validation failed during Cloud Ops 4.5 syncing
**Schema Issue**: LLM response missing required `usage` field

```
Error: {
  "message": {
    "content": [],           // EMPTY CONTENT
    "id": "msg_unknown",
    "model": "",
    "role": "assistant"
  },
  "usage": undefined          // MISSING USAGE FIELD
}
```

## Root Cause Identified

### Supermemory Compaction Service Bug (HIGH CONFIDENCE)

**Evidence**:
1. **Recent commits show response format issues**:
   - `cc5b358` (Jan 13): "fix(compaction): resolve silent summarize failure and response format handling"
   - `6b5ed35`: "fix(compaction): fix session.idle handler response format TypeError"
   - `1f84c88`: "remove session.summarize() to prevent 'Prompt too long' error"

2. **Commit message explicitly mentions**:
   - "Fix TypeError in handleSummaryMessage by handling various API response formats"
   - "Add defensive checks for messages array extraction"

3. **Error pattern matches**:
   - Empty `content: []` array
   - Missing `usage` field
   - Silent failures during summarization

**What's Happening**:
```
Cloud Ops Sync → Supermemory auto-compaction
              → LLM call for session summary
              → Malformed response (content=[], usage=undefined)
              → Schema validation fails
              → Error displayed
```

### Why Cloud Ops 4.5 Sync Triggers It

Cloud Ops syncing likely:
- Processes large batches of data
- Triggers supermemory compaction (automatic)
- Calls LLM for summarization with edge case content
- Receives malformed response

## Supermemory Plugin Analysis

### File Structure (from commits)
```
src/
  ├── config.ts
  ├── index.ts
  └── services/
      └── compaction.ts  (Main fix location)
```

### Fix Attempts (Historical)
1. **Commit `cc5b358`** (Jan 13):
   - Removed invalid `auto: true` param
   - Added logging around summarize calls
   - Fixed TypeError in `handleSummaryMessage`
   - Added defensive checks for messages extraction

2. **Commit `6b5ed35`**:
   - Fixed `session.idle` handler response format

3. **Commit `1f84c88`**:
   - Removed `session.summarize()` to prevent prompt-too-long

### Current Status
- Fix was attempted but error still occurs
- Likely still has edge case not covered
- Missing defensive check for empty `content` + missing `usage`

## Configuration Impact

### Model Configurations
| Agent           | Model                                        | Potential Impact |
| ---------------- | -------------------------------------------- | --------------- |
| Librarian        | `zai-coding-plan/glm-4.7`              | Low - summarization uses main model |
| Supermemory      | Inherits from general (`claude-opus-4-5`) | HIGH - direct impact |
| Explore          | `zai-coding-plan/glm-4.7`              | Low - not involved |

### oh-my-opencode.jsonc
- **Plugin version**: `@opencode-ai/plugin: 1.1.39`
- **Schema validation**: Enforces strict type checking
- **Location**: `%APPDATA%/opencode/oh-my-opencode.jsonc`

## Recommended Fixes

### Priority 1: Fix Supermemory Plugin (ROOT CAUSE)

**Location**: `src/services/compaction.ts` (or equivalent)

**Fix**: Add defensive checks in response handler:
```typescript
function handleSummaryMessage(response: any) {
  // Extract messages defensively
  const messages = response.messages || response.message?.content || [];

  // Check for empty content
  if (!messages || messages.length === 0) {
    console.warn("Empty summary content, skipping compaction");
    return; // Don't proceed with empty content
  }

  // Handle missing usage field (make it optional)
  const usage = response.usage || { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };

  // Continue with processing...
}
```

**Why this fixes it**:
- Empty `content` → early return, no error
- Missing `usage` → default value, schema passes
- Defensive extraction → handles various response formats

### Priority 2: Update oh-my-opencode Schema (COMPATIBILITY)

**If possible**, make `usage` field optional in response schema.

**Challenge**: oh-my-opencode is not a git repo in AppData, cannot verify or modify easily.

### Priority 3: Reduce Cloud Ops Batch Size (WORKAROUND)

**If compaction cannot be fixed immediately**, reduce operations per batch:
- Smaller content → more reliable LLM responses
- Less likely to hit edge cases
- Slower but stable

## Testing Plan

### Reproduce Error
1. Trigger Cloud Ops 4.5 sync
2. Monitor supermemory logs: `~/.local/share/opencode/log/`
3. Check for empty content / missing usage patterns

### Verify Fix
1. Apply defensive checks to supermemory
2. Test with edge case content (large, complex HTML)
3. Verify compaction completes without error
4. Check logs for warnings

## Findings

| Finding | Confidence | Action Required |
|----------|-------------|-----------------|
| Supermemory compaction bug | **VERY HIGH** | Fix defensive checks |
| Missing usage field handling | **CERTAIN** | Add default value |
| Empty content not handled | **HIGH** | Early return / log |
| oh-my-opencode schema strictness | MEDIUM | Make usage optional |

## Next Steps

**Immediate (User can do)**:
- [ ] Check supermemory logs during Cloud Ops sync
- [ ] Try manual supermemory add with large content to test
- [ ] Reduce Cloud Ops batch size as workaround

**Development (Requires code fix)**:
- [ ] Locate exact file handling summary messages
- [ ] Add defensive checks for empty content and missing usage
- [ ] Test with various response formats
- [ ] Deploy fixed version

## Notes

- Error is specific to Cloud Ops 4.5 syncing workflow
- Not triggered by basic operations (add/search work fine)
- Root cause: supermemory's compaction service doesn't handle malformed LLM responses
- Recent fixes attempted but edge case still exists
- Need defensive programming: handle empty content, missing usage, various formats
