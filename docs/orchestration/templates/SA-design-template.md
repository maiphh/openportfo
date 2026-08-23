# SA Design — BL-XXX: <title>

| Field | Value |
|-------|-------|
| **ID** | `BL-XXX` |
| **Title** | |
| **Status** | `draft` / `research_needed` / `ready_for_implementation` |
| **Author (SA)** | |
| **Date** | YYYY-MM-DD |
| **Complexity** | `simple` / `complex` (triggers Researcher if complex) |
| **Related PRD** | `docs/prd/OpenPortfo_PRD.md#...` |
| **Related Arch** | `docs/architecture-design.md#...` |
| **Feature file** | `docs/backlog/features/BL-XXX-*.md` |

---

## 1. Context & constraints

- Problem / user value (1 paragraph, from feature file):
- Locked stack constraints:
  - No API Gateway for user APIs (Beanstalk FastAPI only)
  - No Next.js SSR (CSR/static export → S3+CloudFront)
  - No browser-direct market APIs (server-side only)
  - Cache-first pricing, on-demand FX only (admin refresh)
  - Cognito JWT verification via JWKS

## 2. Affected surfaces

| Layer | Paths / components | Change type |
|-------|--------------------|-------------|
| Frontend | `frontend/src/...` | |
| Backend API | `backend/app/api/...` | |
| Domain / services | `backend/app/services/...`, `domain/...` | |
| Ports | `backend/app/ports/...` | |
| Adapters | `backend/app/adapters/...` | |
| Infra / jobs | `infra/...`, `backend/app/jobs/...` | |
| Docs / tests | `docs/...`, `backend/tests/...` | |

## 3. API & data model deltas

### 3.1 API

| Method & path | Auth | Request | Response | Notes |
|---------------|------|---------|----------|-------|
|  |  |  |  |  |

### 3.2 Data model

```
Entity: PK / SK / attrs
```

- DynamoDB:
- S3 layout:
- Schemas (`app/api/schemas.py`):

## 4. Sequence (happy path)

```
User → Frontend → FastAPI (Beanstalk) → Ports → Adapters → DynamoDB/S3 → External
```

ASCII sequence:

```
1. ...
2. ...
```

## 5. Decisions (ADR style)

| # | Context | Decision | Consequence | Alternatives rejected |
|---|---------|----------|-------------|-----------------------|
| D1 | | | | |

## 6. Complexity assessment

- [ ] Requires choosing between ≥2 libs/patterns → Researcher needed
- [ ] Security / auth / cost-critical AWS path
- [ ] No prior port/adapter pattern to reuse
- [ ] Risk to locked decisions

**Verdict:** `simple` | `complex`

**If complex, research questions:**

1. ...
2. ...

## 7. Handoff to Implementor

### File ownership

- Allowed to edit:
- Must NOT edit (owned by other active sprint/BL):

### TDD order

1. Test: ...
2. Implement: ...
3. ...

### Out-of-scope guardrails

- ...

## 8. Acceptance criteria checklist (copy from feature file)

- [ ] AC-1: ...
- [ ] AC-2: ...

## 9. Risks & mitigations

| Risk | Mitigation |
|------|------------|
|  |  |

## 10. Research linkage (if any)

- Research doc: `docs/orchestration/research/BL-XXX-research.md`
- Research recommendation adopted: ...

---

**SA sign-off:** _ready_for_implementation_ when checklist + TDD order complete.
