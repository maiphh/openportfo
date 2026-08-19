# Product backlog — tracking

**Owner:** BA (requirements) → Eng (implementation)  
**Related:** `docs/prd/OpenPortfo_PRD.md`, `docs/implementation/SPRINTS.md`

This folder tracks **new and follow-on product work** after the original sprint plan. It is the living queue for features we clarify together, not a replacement for completed sprint folders under `docs/implementation/sprints/`.

---

## How we work

1. Stakeholder describes a feature (rough notes are fine).
2. BA opens an item on the board (`BACKLOG.md`) with status `intake`.
3. BA asks questions until acceptance criteria are clear → status `ready`.
4. Eng implements from the feature file → status `in_progress` → `done`.
5. Out-of-scope or deferred items stay on the board as `wont_do` / `deferred` with a short reason.

**Rule:** do not start implementation until status is `ready` (or stakeholder explicitly overrides).

---

## Folder layout

```text
docs/backlog/
  README.md              # this file
  BACKLOG.md             # master status board
  features/
    _TEMPLATE.md         # copy when adding a feature
    BL-XXX-short-name.md # one file per feature (created when clarified)
```

---

## Status values

| Status | Meaning |
|--------|---------|
| `intake` | Listed; not yet clarified |
| `clarifying` | BA actively gathering requirements |
| `ready` | Spec + acceptance criteria enough to implement |
| `in_progress` | Implementation started |
| `done` | Delivered / verified |
| `blocked` | Waiting on decision, dependency, or external input |
| `deferred` | Intentionally postponed |
| `wont_do` | Explicitly rejected (keep reason) |

---

## Priority

| Priority | Meaning |
|----------|---------|
| `P0` | Must have for next ship / demo |
| `P1` | Should have |
| `P2` | Nice to have |
| `P3` | Idea / park |

---

## ID convention

`BL-XXX` — sequential backlog id (`BL-001`, `BL-002`, …).  
Feature filename: `BL-XXX-short-kebab-name.md`.

---

## Definition of ready (DoR)

An item may move to `ready` only when its feature file has:

- [ ] Problem / user value in one paragraph
- [ ] In scope / out of scope
- [ ] User-facing behaviour (happy path)
- [ ] Acceptance criteria (testable)
- [ ] Data sources / APIs (or “mock only”)
- [ ] Affected surfaces (routes, APIs, jobs)
- [ ] Open questions empty or marked resolved
