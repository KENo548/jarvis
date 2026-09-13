# Proven Patterns

## Pattern: Lazy Initialization

**Context**: Resource-heavy components that may not be needed on every startup.

**Solution**: Initialize on first use, not at import time.

**Evidence**: Meridian SQLite DB opens on first query, not at server boot. Reduces cold start from 30-50s to <1s.

```
let db = null;
function getDb() {
  if (!db) db = openDatabase();
  return db;
}
```

## Pattern: Non-Blocking Auth

**Context**: Auth check blocking page render on slow/cold server.

**Solution**: Cache user in sessionStorage, show app immediately, revalidate in background.

**Evidence**: Meridian login appears instantly; getCurrentUser() runs in background on warm server.

## Pattern: Instant Logout

**Context**: Logout waiting for server response on slow connection.

**Solution**: Clear local state immediately, fire server call in background.

**Evidence**: Meridian logout is instant; cookie cleared client-side, server session cleanup is async.

## Pattern: Auto-Retry for Cold Starts

**Context**: Render free tier cold starts cause 503 errors.

**Solution**: Retry with backoff (15s/20s/25s timeout, 3 attempts).

**Evidence**: Meridian login shows "server waking up" with spinner, retries automatically.

## Pattern: Protected Self-Modification

**Context**: Agent improving itself could weaken security boundaries.

**Solution**: Protected paths require user approval for material changes; inspection is autonomous.

**Evidence**: JARVIS architecture — agents, instructions, security config are protected.

## Pattern: Git as Sync Layer

**Context**: Multiple machines need synchronized state.

**Solution**: Git push/pull via GitHub; no filesystem sync.

**Evidence**: JARVIS PC ↔ Oracle sync uses Git only; no rsync, no auto-merge.
