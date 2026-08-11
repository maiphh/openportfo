# OpenPortfo — Sprint Overview (Multiagent)

**PRD:** `docs/prd/OpenPortfo_PRD.md` (v1.3)  
**Auth:** Cognito — `docs/prd/auth-cognito.md`  
**Architecture:** `docs/architecture-design.md`  
**Plan:** sprint-based TDD, AWS behind ports, backend-first, temp view UI  

---

## Status board

| Sprint | Name | Status | Owner | Blocked by |
|--------|------|--------|-------|------------|
| 00 | Skeleton | `done` | orchestrator | — |
| 01 | Domain | `done` | agent | 00 |
| 02 | Auth | `done` | agent | 01 |
| 03 | Holdings/Watchlist | `done` | agent | 02 |
| 04 | Market + cache | `done` | agent | 03 |
| 05 | Portfolio | `done` | agent | 04 |
| 06 | FX admin | `done` | orchestrator | 05 |
| 07 | History S3 | `done` | orchestrator | 05 |
| 08 | News read | `done` | orchestrator | 02 |
| 09 | Admin | `done` | orchestrator | 02 |
| 10 | Jobs | `done` | orchestrator | 06–09 |
| 11 | Temp frontend | `done` | orchestrator | 05+ (ideal 10) |
| 12 | AWS deploy | `done` | agent | 10–11 |
| 13 | Stretch | `blocked` | — | 12 |

Status values: `pending` | `in_progress` | `blocked` | `done`

---

## Dependency graph

```text
00 → 01 → 02 → 03 → 04 → 05 → 06
                          ├─ 07 ─┐
                          ├─ 08 ─┼→ 10 → 11 → 12 → 13
                          └─ 09 ─┘
```

**Serial:** 00→01→02→03→04→05→06  
**Parallel after 05:** 07 ∥ 08 ∥ 09 (08/09 only need 02; prefer after 05 for less conflict)  
**Then:** 10 → 11 → 12 → 13

---

## Roles

| Role | Duty |
|------|------|
| **Orchestrator** | Assign sprints; update status board; merge; enforce DoD |
| **Sprint agent** | Own one `sprints/sprint-XX-*/`; TDD; fill `handoff.md` |
| **Reviewer** (optional) | Ports not leaked; tests match `tests.md` |

---

## Per-sprint folder contents

```text
docs/implementation/sprints/sprint-XX-*/
  PLAN.md           # DETAILED plan (primary for multiagent) — read first
  README.md         # Short goal / owns / agent prompt
  components.md     # Component checklist
  tests.md          # TDD case list
  handoff.md        # Fill when sprint completes
```

## Global rules (every agent)

1. Read **`PLAN.md` first**, then `README.md`, `components.md`, `tests.md`.  
2. **Do not implement** until orchestrator assigns the sprint and status is `in_progress`.  
3. **TDD:** tests first from `tests.md` / PLAN TDD sequence.  
4. **Ports only** in `api/`, `services/`, `domain/`, `jobs/` — no `boto3` / raw HTTP.  
5. Do not edit paths owned by another active sprint (see PLAN **File ownership**).  
6. Shared files (`core/deps.py`, `main.py`): one agent at a time; list changes in handoff.  
7. PRD: no auto FX; Cognito not custom passwords; portfolio GET never calls ExchangeRate-API.  
8. On finish: update `handoff.md` + ask orchestrator to mark `done`.

---

## Definition of done (every sprint)

- [ ] `components.md` done or deferred in handoff  
- [ ] `tests.md` automated and green  
- [ ] No AWS SDK in services/api  
- [ ] `handoff.md` complete  
- [ ] Status board updated  

---

## Ports catalog (reference)

| Port | Adapter | Fake |
|------|---------|------|
| UserProfileRepo | DynamoDB | InMemory |
| HoldingsRepo | DynamoDB | InMemory |
| WatchlistRepo | DynamoDB | InMemory |
| PriceCacheRepo | DynamoDB | InMemory |
| NewsRepo | DynamoDB | InMemory |
| SettingsRepo | DynamoDB | InMemory |
| RssSourcesRepo | DynamoDB | InMemory |
| ExchangeRateRepo | DynamoDB | InMemory |
| JobRunsRepo | DynamoDB | InMemory |
| SnapshotRepo | DynamoDB | InMemory |
| ObjectStorage | S3 | InMemory |
| TokenVerifier | Cognito JWKS | FakeTokenVerifier |
| CryptoMarketClient | CoinGecko | Fixture |
| StockMarketClient | vnstock | Fixture |
| ExchangeRateClient | ExchangeRate-API | Success/fail fake |
| RssFetcher | feedparser | Fake |
| EmailSender | SES | No-op |

---

## Target code layout

```text
backend/app/{main,api,domain,services,ports,adapters,jobs,core}
backend/tests/{unit,integration,fakes}
frontend-temp/          # Sprint 11
docs/implementation/sprints/sprint-XX-*/
```

---

## Detailed plans index

| Sprint | Detailed plan |
|--------|----------------|
| 00 | [sprint-00-skeleton/PLAN.md](sprints/sprint-00-skeleton/PLAN.md) |
| 01 | [sprint-01-domain/PLAN.md](sprints/sprint-01-domain/PLAN.md) |
| 02 | [sprint-02-auth/PLAN.md](sprints/sprint-02-auth/PLAN.md) |
| 03 | [sprint-03-holdings-watchlist/PLAN.md](sprints/sprint-03-holdings-watchlist/PLAN.md) |
| 04 | [sprint-04-market-cache/PLAN.md](sprints/sprint-04-market-cache/PLAN.md) |
| 05 | [sprint-05-portfolio/PLAN.md](sprints/sprint-05-portfolio/PLAN.md) |
| 06 | [sprint-06-fx/PLAN.md](sprints/sprint-06-fx/PLAN.md) |
| 07 | [sprint-07-history-s3/PLAN.md](sprints/sprint-07-history-s3/PLAN.md) |
| 08 | [sprint-08-news-settings/PLAN.md](sprints/sprint-08-news-settings/PLAN.md) |
| 09 | [sprint-09-admin/PLAN.md](sprints/sprint-09-admin/PLAN.md) |
| 10 | [sprint-10-jobs/PLAN.md](sprints/sprint-10-jobs/PLAN.md) |
| 11 | [sprint-11-temp-frontend/PLAN.md](sprints/sprint-11-temp-frontend/PLAN.md) |
| 12 | [sprint-12-aws-deploy/PLAN.md](sprints/sprint-12-aws-deploy/PLAN.md) |
| 13 | [sprint-13-stretch/PLAN.md](sprints/sprint-13-stretch/PLAN.md) |

## Kickoff (when you choose to implement)

1. Orchestrator sets Sprint 00 → `in_progress`.  
2. Agent reads `PLAN.md` and implements **only** Sprint 00.  
3. After handoff ✅, open Sprint 01 (parallel 07∥08∥09 only after 05 per graph).  
