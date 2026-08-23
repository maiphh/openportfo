# SA Review — BL-XXX: <title>

| Field | Value |
|-------|-------|
| **ID** | `BL-XXX` |
| **Reviewer (SA)** | |
| **Date** | YYYY-MM-DD |
| **Walkthrough** | `docs/orchestration/walkthroughs/BL-XXX-walkthrough.md` |
| **Verdict** | `approve` / `request_changes` |

---

## 1. AC verification

| AC | Satisfied? | Evidence (file:line or test) | Note |
|----|------------|------------------------------|------|
| AC-1 | yes/no | | |
| AC-2 | yes/no | | |

## 2. Architecture checks

- [ ] Ports isolation (`boto3`/`httpx` only in `adapters/`)? `backend/app/services:line` ?
- [ ] Locked decisions intact (no API GW, no SSR, cache-first, Cognito JWKS)?
- [ ] Cost/budget impact ≤$50 narrative respected?
- [ ] Security (no secrets in frontend/Git, no presigned leak)?

## 3. Code quality

- [ ] Tests green + meaningful (not just `assert True`)?
- [ ] File ownership respected (no edit of other BL's files)?
- [ ] Error model `{detail: ...}` + correct HTTP codes?

## 4. Issues (if request_changes)

| # | File:line | Issue | Required fix |
|---|-----------|-------|--------------|
| 1 | | | |

## 5. Decision

- **If approve:** Orchestrator may merge branch `feat/BL-XXX-*` → `integration/*` or `main`, mark backlog `done`.
- **If request_changes:** Implementor to address issues in same worktree, re-run tests, update walkthrough, re-request review. No new worktree.

## 6. Notes for Orchestrator

- ...

