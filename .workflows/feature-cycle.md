# OpenPortfo autonomous feature cycle

This file is the durable SDLC contract for feature requests. A request may be informal; the agent owns turning it into testable work and carrying it to a review-ready result.

## Invocation

Give the agent a feature instruction and say `run the feature cycle`, or start a long-running goal that points here. The request is the source of product intent; this workflow supplies the engineering process.

## Cycle

1. **Orient and intake**
   - Read `AGENTS.md`, the matching backlog item, PRD, architecture, and relevant code.
   - Inspect git status and preserve unrelated user changes.
   - Resolve or allocate a `BL-XXX` id. Create the feature artifact from `docs/backlog/features/_TEMPLATE.md` when one does not exist.
   - Turn the request into explicit acceptance criteria, non-goals, affected surfaces, and risk. Ask only when a missing product choice would materially change the result.

2. **Establish the baseline**
   - Run `.workflows/verify.ps1 -Profile quick` before feature edits.
   - Record pre-existing failures separately from regressions. Do not hide or relabel a failure.
   - For UI work, invoke `$playwright-verification`. For AWS persistence or infrastructure work, invoke `$localstack-verification`.

3. **Design and isolate**
   - Write or update `docs/orchestration/designs/BL-XXX-<slug>-design.md` with concrete paths, API/data changes, decisions, TDD order, and copied acceptance criteria.
   - Use the current feature branch/worktree when it is already isolated. If on the shared main branch and the work is substantial, create a feature worktree with `scripts/worktree.ps1` or `scripts/worktree.sh`.
   - Research only decisions that are genuinely unresolved or time-sensitive. Cite fetched primary sources in `docs/orchestration/research/`.

4. **Implement test-first**
   - Add or update the narrowest failing test for one acceptance criterion.
   - Make one focused implementation change and rerun the relevant test.
   - Preserve ports/adapters isolation and existing data contracts. Do not broaden scope to opportunistic refactors.
   - Repeat until every acceptance criterion has executable evidence.

5. **Verify in layers**
   - Run focused tests during iteration.
   - Run `.workflows/verify.ps1 -Profile full` before review. The runner continues through all gates and writes JSON evidence under `.workflows/runs/`.
   - Browser-visible changes require Playwright evidence. AWS adapter/infra changes require the LocalStack contract probe plus affected integration evidence.
   - Inspect artifacts directly when a test produces screenshots, traces, exports, or stored objects.

6. **Review and repair**
   - Compare the diff and test evidence against every acceptance criterion and architecture constraint.
   - When independent agent review is available and authorized, use it for non-trivial changes; otherwise perform a separate review pass after implementation.
   - Write `docs/orchestration/reviews/BL-XXX-review.md` with an unambiguous `approve` or `request_changes` verdict and exact file/line evidence.
   - On `request_changes` or any failed gate, return to the smallest responsible stage, fix, and rerun all affected gates. Continue until approved or genuinely blocked.

7. **Handoff**
   - Update the backlog only after acceptance criteria, full verification, and review pass.
   - Report changed files, acceptance evidence, exact commands and results, known limitations, and the branch/worktree.
   - Leave the result review-ready. Commit, merge, push, deploy, or mutate real AWS only when the user's instruction authorizes that step.

## Gate selection

| Change surface | Required evidence |
| --- | --- |
| Backend/domain/API | focused pytest + full backend suite |
| Frontend logic/component | focused Vitest + lint + production build |
| Page, navigation, form, auth, responsive UX | frontend gates + Playwright |
| DynamoDB/S3 adapter or CloudFormation | backend gates + LocalStack probe + affected integration test |
| Cross-stack feature | all gates |
| Docs/workflow only | workflow contract check; run code gates only when commands/config changed |

## Definition of done

Done means all acceptance criteria have observable evidence, required gates pass, no new architecture violation exists, review says `approve`, and the handoff states residual risk. Passing unit tests alone is never sufficient for a browser or AWS integration change.
