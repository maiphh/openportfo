---
description: Spawn Implementor in worktree to TDD implement, test, and write walkthrough.
agent: implementor
---

Implement: $ARGUMENTS

Worktree is assumed at `D:\rmit\cloud\a3-wt-bl<NUM>` (or `../a3-wt-bl<NUM>`). If not exists, create via `scripts/worktree.ps1 -Id $ARGUMENTS -Slug <slug>` first.

1. Read `docs/orchestration/designs/$ARGUMENTS-design.md` (+ research if exists).
2. In worktree (`workdir`), TDD per AC, run `pytest -q`, check ports isolation, write `docs/orchestration/walkthroughs/$ARGUMENTS-walkthrough.md` per template with file:line refs.
3. Return branch + test summary + walkthrough path.
