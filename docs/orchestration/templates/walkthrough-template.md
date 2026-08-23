# Walkthrough — BL-XXX: <title>

| Field | Value |
|-------|-------|
| **ID** | `BL-XXX` |
| **Branch** | `feat/BL-XXX-slug` |
| **Worktree** | `D:\rmit\cloud\a3-wt-blXXX` |
| **Implementor** | |
| **Date** | YYYY-MM-DD |
| **SA design** | `docs/orchestration/designs/BL-XXX-design.md` |
| **Research** | `docs/orchestration/research/BL-XXX-research.md` (if any) |

---

## 1. Summary (what was built)

One paragraph.

## 2. Files changed (path:line)

| File | Change | Lines |
|------|--------|-------|
| `backend/app/api/...:42` | Added ... | |
| `backend/tests/...:10` | Added test ... | |

## 3. Decisions & deviations from SA design

| # | SA said | Did | Reason |
|---|---------|-----|--------|
| 1 | | | |

## 4. How to verify

```powershell
# backend
cd backend
.\.venv\Scripts\Activate.ps1
pytest -q

# frontend (if touched)
cd ../frontend
npm run lint
npm run test
```

Expected output:

```
...
```

## 5. Test evidence (paste)

```
pytest output
```

- Unit tests added: ...
- Coverage of AC: ...

## 6. API / UX verification

- Curl / browser steps:
- Screenshots / curl output:

## 7. Ports isolation check

```powershell
# should be empty outside adapters/
Select-String -Pattern "boto3|httpx|requests" -Path "backend/app/services","backend/app/api" -Recurse
```

Result: ...

## 8. Known limitations / follow-ons

- ...

## 9. Handoff to SA Review

- Walkthrough ready for SA review: yes/no
- AC checklist self-assessed: ...

