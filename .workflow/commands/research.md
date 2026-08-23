---
description: Spawn Researcher for complex BL (websearch + recommendation).
agent: researcher
---

Research for: $ARGUMENTS

1. Read `docs/orchestration/designs/$ARGUMENTS-design.md` → extract research questions.
2. Run `websearch` (with 2026 year) and `webfetch` 3-5 URLs.
3. Write `docs/orchestration/research/$ARGUMENTS-research.md` per template with cited sources (no hallucinated links).
4. Return recommendation + citations.
