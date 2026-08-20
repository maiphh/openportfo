# BL-016 — Personal chatbot client and Markdown UI

| Field | Value |
|-------|-------|
| **ID** | `BL-016` |
| **Title** | Production chat client with safe Markdown and activity states |
| **Priority** | `P0` |
| **Status** | `done` |
| **Owner (Eng)** | Eng |
| **Related** | `BL-015` |

## Scope

- Consume the SSE endpoint with a JSON POST fallback for rolling deploys.
- Render headings, emphasis, code, lists, quotes, tables, task lists, and
  links as React nodes; raw HTML is never injected and unsafe URL schemes are
  rejected.
- Show only safe progress/tool labels and user-friendly auth/provider errors.
- Keep the panel usable for guests with a sign-in prompt.

## Verification

- `frontend/lib/chat.test.ts`
- `frontend/components/chat/SafeMarkdown.test.tsx`
- Existing frontend typecheck, lint, and Vitest suite.
