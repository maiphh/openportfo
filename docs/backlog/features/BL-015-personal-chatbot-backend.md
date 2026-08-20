# BL-015 — Personal chatbot backend and safe streaming contract

| Field | Value |
|-------|-------|
| **ID** | `BL-015` |
| **Title** | Authenticated personal chatbot backend with safe progress events |
| **Priority** | `P0` |
| **Status** | `done` |
| **Owner (Eng)** | Eng |
| **Related** | Existing `POST /api/chat` orchestrator and user-scoped tools |

## Scope

- Preserve `POST /api/chat` for existing callers.
- Add `POST /api/chat/stream` using SSE events for safe status, allow-listed
  tool activity, final message, and bounded error states.
- Keep authentication and all tool execution scoped to the resolved user.
- Do not publish system prompts, hidden reasoning, bearer tokens, user IDs,
  tool arguments/results, provider token usage, or tried-model internals.
- Strip common hidden-reasoning tags and sensitive fields before provider
  messages are serialized.
- Require `clientRequestId` on the SSE path and fence every mutating tool with
  a per-user DynamoDB idempotency claim (`in_progress` → `mutation_started` →
  `completed`/`ambiguous`). Ownership tokens and conditional writes prevent a
  stale worker from finalizing or releasing a newer claim. Legacy POST calls
  without a request ID remain valid for read-only tools but reject mutations.
- A durable ledger transition is intentionally separate from the domain write
  because the existing holding/watchlist repositories do not share a DynamoDB
  transaction boundary. If the process crashes after `mutation_started` and
  before either side completes, the request remains `ambiguous` and clients
  must verify state; the UI never retries it automatically. Claims are bounded
  by `CHAT_IDEMPOTENCY_TTL_SECONDS`, after which a deliberately expired key may
  be reclaimed.
- `POST /api/chat` keeps its original `reply`, `model`, `toolCalls`,
  `triedModels`, and `rounds` keys. Its versioned `responseVersion: 2` contract
  makes `usage: {available: false, redacted: true}` explicit because provider
  token/cost details are not a browser-safe API surface.

## Verification

- `backend/tests/unit/api/test_chat.py` covers compatibility redaction and
  SSE activity redaction, request-id enforcement, and ambiguous write errors.
- `backend/tests/unit/adapters/test_chat_idempotency.py` and
  `test_dynamodb_chat_idempotency.py` cover simultaneous first/expired claims
  and stale save/release attempts.
