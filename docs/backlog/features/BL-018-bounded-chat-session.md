# BL-018 — Bounded user-scoped chat session

| Field | Value |
|-------|-------|
| **ID** | `BL-018` |
| **Title** | Per-account browser session persistence and auth-change handling |
| **Priority** | `P1` |
| **Status** | `done` |
| **Owner (Eng)** | Eng |
| **Related** | `BL-006`, `BL-016` |

## Scope

- Persist at most 50 sanitized user/assistant messages per authenticated
  profile, with per-message and total storage bounds.
- Namespace storage by encoded profile ID; never send the storage key to the
  backend.
- Reload the matching account history after authentication and clear in-memory
  state/abort active work on token or profile changes.
- Fail closed on malformed, unavailable, or quota-limited browser storage.

## Verification

- `frontend/lib/chat-session.test.ts` covers isolation, malformed data, and
  bounded content.
