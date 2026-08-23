# Orchestration — SA → Research → Implementor → Test → Review Cycle

**Status:** active  
**Owner:** Orchestrator (primary agent)  
**Related:** `docs/architecture-design.md`, `docs/prd/OpenPortfo_PRD.md`, `docs/implementation/SPRINTS.md`, `docs/backlog/README.md`

---

## 1. Goal

Turn every incoming feature / bug / tech-debt item into a **closed loop**:

```
Intake → SA Design → (Research if complex) → Implementor (worktree) → Tests → Walkthrough → SA Review → Done | Loop back
```

- **Single owner at a time.** Only one agent owns the item in each phase.
- **Isolation.** Unrelated features never share a branch/worktree — no cross-contamination.
- **Review gate.** SA must approve walkthrough + decisions before `done`.

---

## 2. Roles

| Role | Mode | Responsibility | Input | Output |
|------|------|----------------|-------|--------|
| **Orchestrator** | `primary` | Triage intake, assign SA, create worktree per unrelated feature, schedule agents, enforce DoD, merge | Backlog `intake` item or stakeholder request | Worktree + assigned SA task |
| **Solution Architect (SA)** | `subagent` | Detailed implementation design within locked stack (FastAPI/Next.js/DynamoDB/S3/Lambda). Decides complexity → triggers Researcher | Intake description + PRD + arch | `docs/orchestration/designs/BL-XXX-design.md` + `AC-checklist.md` |
| **Researcher** | `subagent` | Web research for **complex / high-risk** problems only. Finds 2-3 viable patterns, tradeoffs, source URLs | SA question + complexity flag | `docs/orchestration/research/BL-XXX-research.md` (options table + recommendation) |
| **Implementor** | `subagent` | Implements from SA design (+ research), TDD, writes code in worktree, runs unit tests, writes walkthrough | SA design (+ research) | Code + tests green + `docs/orchestration/walkthroughs/BL-XXX-walkthrough.md` |
| **Reviewer (SA re-review)** | `subagent` (SA) | Verifies walkthrough vs AC, checks ports isolation, cost/budget, security. Either `approve` or `request_changes` with exact file:line | Walkthrough + diff | `approved` or new loop with `CHANGES.md` |

No agent writes outside its phase artifacts. Orchestrator is the only one that creates/deletes worktrees and merges to `integration/*` or `main`.

---

## 3. When to trigger Research

SA marks a problem **complex** if any true:

- Requires choosing between ≥2 external libs / patterns (e.g., SSE vs polling, JWT lib comparison, S3 presigned vs proxy).
- Touches security / auth (Cognito JWT, presigned URLs, CORS) or cost-critical AWS path.
- No prior pattern in `backend/app/ports/*` or `adapters/*` to reuse.
- Risk of breaking locked decisions (no API GW, no SSR, no browser-direct market APIs, cache-first pricing).

If **not complex** → SA skips Researcher and hands design directly to Implementor (faster cycle).

Researcher **must** use `websearch`/`webfetch` and cite URLs. No hallucinated links.

---

## 4. Worktree rule — one per unrelated feature

> **Rule:** Every unrelated feature/bug gets its own `git worktree` + `feat/BL-XXX-...` branch. Related follow-ons may share a worktree only if Orchestrator explicitly groups them in `integration/backlog-batch-*`.

```
main
 ├─ feat/BL-027-portfolio-csv  → worktree: ../a3-wt-bl027
 ├─ feat/BL-028-notifications  → worktree: ../a3-wt-bl028
 └─ integration/backlog-batch-xxx (batch of related BLs)
```

### Helper

```powershell
# PowerShell (from repo root)
.\scripts\worktree.ps1 -Id BL-027 -Slug portfolio-csv -Base main
# creates branch feat/BL-027-portfolio-csv and worktree D:\rmit\cloud\a3-wt-bl027
```

See `scripts/worktree.ps1` and `scripts/worktree.sh`.

Orchestrator **must** `git worktree list` before creating to avoid collisions. Never `git checkout` on main for feature work — use worktree.

---

## 5. Full cycle (step-by-step)

### Phase 0 — Intake (Orchestrator)

1. Stakeholder describes feature (rough text ok).
2. Orchestrator creates `docs/backlog/features/BL-XXX-*.md` from `_TEMPLATE.md`, fills Problem/Scope/Behaviour/Acceptance, sets `intake`.
3. BA clarifies until DoR → `ready`.
4. Orchestrator decides grouping: if unrelated → **new worktree**, else batch.

### Phase 1 — Solution Architect

Spawned as subagent via `task(subagent_type="general", prompt="You are Solution Architect...")`.

Must produce:

- `docs/orchestration/designs/BL-XXX-design.md` containing:
  - Context & constraints (PRD sections, arch diagram refs)
  - Affected surfaces table (frontend/backend/ports/adapters/infra/docs/tests)
  - API / data model deltas (DynamoDB entities, S3 layout, schemas)
  - Sequence diagram (ASCII) for happy path
  - Decision log (ADR-style: Context → Decision → Consequence)
  - Complexity flag + research questions (if needed)
  - AC checklist (copy from feature file)
  - Handoff to Implementor: file ownership, TDD order, out-of-scope guardrails

Template: `docs/orchestration/templates/SA-design-template.md`

If `complex = true` → Orchestrator spawns Researcher next; else skip to Implementor.

### Phase 2 — Research (conditional)

Researcher runs `websearch` + `webfetch`, returns:

- `docs/orchestration/research/BL-XXX-research.md`:
  - Problem restatement
  - 2-3 options (Pros/Cons/Cost/Security/Complexity)
  - Recommendation + rationale + source URLs
  - What SA should lock in design

SA then **revises** design doc with research citation (`Research → Decision`).

### Phase 3 — Implementor

Spawned in worktree (`workdir = worktree path`).

1. Reads SA design (+ research).
2. TDD per `tests.md` or AC checklist: write failing tests → implement → green.
3. Respects **ports-only** rule: no `boto3` in `services/api/domain/jobs`.
4. Runs:
   ```powershell
   cd backend; pytest -q
   cd ../frontend; npm run lint; npm run test  # if applicable
   ```
5. Writes `docs/orchestration/walkthroughs/BL-XXX-walkthrough.md`:
   - Files changed (path:line)
   - Decisions made (incl. deviations from SA design with reason)
   - How to verify (commands + expected output)
   - Test evidence (paste pytest summary)
   - Known limitations

### Phase 4 — SA Review

Orchestrator spawns SA reviewer (same SA agent, review mode).

Reviewer checks:

- [ ] AC satisfied (each Given/When/Then)?
- [ ] Ports isolation (grep `boto3`/`httpx` outside adapters)?
- [ ] Locked decisions intact (no API GW, no SSR, cache-first, Cognito JWT)?
- [ ] Tests green + meaningful?
- [ ] Walkthrough accurate?

Outcome:

- `approve` → Orchestrator merges worktree branch → `integration/*` or `main` per release plan, marks backlog `done`.
- `request_changes` → writes `docs/orchestration/reviews/BL-XXX-review.md` with file:line fixes → loop back to Implementor (same worktree).

---

## 6. Artifacts & where they live

```
docs/orchestration/
  README.md                # this file
  templates/
    SA-design-template.md
    research-template.md
    walkthrough-template.md
    review-template.md
  designs/BL-XXX-design.md
  research/BL-XXX-research.md
  walkthroughs/BL-XXX-walkthrough.md
  reviews/BL-XXX-review.md
docs/backlog/features/BL-XXX-*.md  # source of truth for AC
```

Branch: `feat/BL-XXX-slug`  
Worktree: `../a3-wt-blXXX` (or `D:\rmit\cloud\a3-wt-blXXX` on Windows)

---

## 7. Definition of Done (cycle)

- [ ] SA design approved (or revised after research)
- [ ] Implementor tests green (`pytest -q` + frontend tests if touched)
- [ ] No AWS SDK outside `adapters/` / `ports/` wrappers
- [ ] Walkthrough filed with file:line refs + verification steps
- [ ] SA review = `approve`
- [ ] Backlog `BACKLOG.md` moved to `done` with date + branch
- [ ] Worktree cleaned or kept per Orchestrator retention policy

---

## 8. Quick start (Orchestrator commands)

| Intent | Command |
|--------|---------|
| Triage new intake | `/orchestrate-intake BL-027 "brief description"` |
| Spawn SA | `/sa-design BL-027` |
| Research if flagged | `/research BL-027` |
| Spawn Implementor | `/implement BL-027` |
| SA Review | `/sa-review BL-027` |

Or via Task tool programmatically (see `.opencode/agents/*.md`).

---

## 9. Anti-patterns

- No direct edits on `main` for feature work.
- No skipping SA design ("just code it") — even trivial items need 1-paragraph SA note.
- No hallucinated URLs in research — cite real fetched pages.
- No shared worktree for unrelated features.
- No `edit` permission for SA/Researcher on `backend/app/**` — they are doc-only.
