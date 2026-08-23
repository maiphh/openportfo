---
description: Orchestrator intake — create backlog feature entry and assess worktree need.
agent: orchestrator
---

You are orchestrating intake for: $ARGUMENTS

1. Parse `$ARGUMENTS` as `BL-XXX "short description"` or freeform feature note. If no BL id given, peek `docs/backlog/BACKLOG.md` for next free id (last +1).
2. Copy `docs/backlog/features/_TEMPLATE.md` → `docs/backlog/features/BL-XXX-slug.md`, fill Problem/Scope/Behaviour/AC minimally so DoR can be judged. Set priority P0/P1 per note urgency.
3. Decide worktree need:
   - If unrelated to any active `feat/*` branch (check `git worktree list` + `git branch`), recommend new worktree via `scripts/worktree.ps1 -Id BL-XXX -Slug <slug>`.
   - If related batch, note `integration/backlog-batch-*` instead.
4. Return: feature file path, BL id, worktree recommendation, and whether SA can be spawned now or needs clarification questions for BA.
