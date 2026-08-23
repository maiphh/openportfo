---
description: SA Review gate — verify walkthrough vs AC and approve or request_changes.
agent: reviewer
---

Review: $ARGUMENTS

1. Read `docs/orchestration/designs/$ARGUMENTS-design.md`, `docs/orchestration/walkthroughs/$ARGUMENTS-walkthrough.md`, and git diff for `feat/$ARGUMENTS-*`.
2. Write `docs/orchestration/reviews/$ARGUMENTS-review.md` per template, with AC table and file:line issues if any.
3. Verdict `approve` or `request_changes`. If request_changes, Implementor loops in same worktree.
4. Return verdict + review path.
