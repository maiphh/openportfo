# Sprint 14 — Logic-error fixes (multi-agent)

Orchestrator-owned. Implementers edit only their file list.

## Wave 1 (parallel, no shared files)

| Agent | Scope | Errors |
|-------|--------|--------|
| A | Domain + market + history | 5, 6, 7, 8, 4 (vnstock live) |
| B | Jobs + ports | 9, 10, 11, 12 |
| C | Persist + FX + lab News schema | 1, 13, 15 |
| D | Test isolation + security | 16, 17, 18, 20, 21, 22 |

## Wave 2 (after Wave 1)

| Agent | Scope | Errors |
|-------|--------|--------|
| E | `deps.py` wiring | 2, 3, 14, 19 (prod fake-auth refuse) |

## Wave 3

Orchestrator runs `pytest`. Then one reviewer on the full diff. PC shutdown only if tests green and review has **zero bugs**.
