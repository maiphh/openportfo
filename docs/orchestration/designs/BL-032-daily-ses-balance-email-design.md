# SA Design — BL-032: Daily SES portfolio balance-change email

| Field | Value |
|-------|-------|
| **ID** | `BL-032` |
| **Title** | User opt-in daily SES email: PnL, per-asset performance, holdings/watchlist news |
| **Status** | `ready_for_implementation` |
| **Author (SA)** | SA |
| **Date** | 2026-09-12 |
| **Complexity** | `simple` |
| **Related PRD** | `docs/prd/OpenPortfo_PRD.md` FR-J5, FR-J7, S1, D4/D5 |
| **Related Arch** | `docs/architecture-design.md` §3 Path B, §5 scheduled pipelines, SES stretch |
| **Feature file** | `docs/backlog/features/BL-032-daily-ses-balance-email.md` |

---

## 1. Context & constraints

Users already persist `emailOptIn` and admins already store `emailEnabled` / `jobs.email`, but Lambda only dispatches `news|price|snapshot`. Stakeholder wants:

1. A **user switch** for receiving the daily update (reuse `emailOptIn`, default off).
2. **Daily crons at 00:00 UTC+7** for **news, price, and snapshot**.
3. **Email 15 minutes later** so it cannot run before snapshot **and** news writes exist.
4. Email content: **portfolio PnL**, **each holding’s performance**, **news related to holdings and watchlists**.

Locked stack constraints:

- No API Gateway for user APIs; **no** browser → Lambda; email is EventBridge → Lambda only.
- No Next.js SSR. Settings stay CSR `/settings`.
- No `boto3`/`httpx` in `jobs/` or `services/` — SES lives in `adapters/`.
- FX remains admin on-demand; email must **not** call ExchangeRate-API.
- Jobs read `JobContext` ports only.
- LocalStack proves DynamoDB/S3, **not** SES (use a recording fake in pytest).
- Do not deploy, push, or mutate real AWS in this ticket unless a later user instruction says so.

**PRD override (document in PRD when implementing):** D4 (hourly Lambda + `emailTime` window) is replaced by **fixed EventBridge crons**. D5 stretch SES is the feature being built.

---

## 2. Affected surfaces

| Layer | Paths / components | Change type |
|-------|--------------------|-------------|
| Frontend | `frontend/components/settings/GeneralTab.tsx`, `frontend/lib/i18n.ts` | copy + helper; existing checkbox |
| Frontend | `frontend/components/admin/JobControlsPanel.tsx` (+ test) | add Daily email toggle |
| Frontend | Playwright settings spec (extend or add) | opt-in save round-trip |
| Backend API | `backend/app/api/admin.py` settings | **reuse** (`jobs.email`, `emailEnabled`) |
| Backend API | `PUT /api/settings` `emailOptIn` | **reuse** |
| Ports | `backend/app/ports/email.py` **NEW** `EmailSender` | new |
| Adapters | `backend/app/adapters/ses/sender.py` **NEW**; tests/fakes recording sender | new |
| Jobs | `backend/app/jobs/email_job.py` **NEW**; `handler.py`; `context.py`; `lambda_entry.py` | new/modify |
| Jobs | `backend/app/jobs/snapshot_job.py` default date → ICT today | modify |
| Jobs | `backend/app/jobs/news_job.py` | **reuse** (cron only; no ingest rewrite) |
| Core | `backend/app/core/config.py` `SES_FROM_EMAIL`; `deps.py` `build_job_context` + `get_email_sender` | modify |
| Infra | `infra/cloudformation.yml` EventBridge email rule, SES IAM, cron times | modify |
| Infra | `infra/cloudformation-lab.yml` | **no IAM/EventBridge** (lab cannot CreateRole); runbook note only |
| Docs | `infra/lambda/README.md`, arch §5 schedule, PRD D4 note | modify |
| Tests | `backend/tests/unit/jobs/test_jobs.py` (or `test_email_job.py`); config tests | new/modify |

---

## 3. API & data model deltas

### 3.1 HTTP (no new routes)

| Method & path | Auth | Change |
|---------------|------|--------|
| `PUT /api/settings` `{ emailOptIn }` | signed-in | Unchanged contract; checkbox copy only |
| `PUT /api/admin/settings` `{ version, emailEnabled?, jobs: { email? } }` | admin | UI writes **both** `emailEnabled` and `jobs.email` together |

### 3.2 Lambda event

```
{"job":"email"}
```

Unknown jobs still `ValueError`. Snapshot override `{"job":"snapshot","date":"YYYY-MM-DD"}` unchanged (literal date, no TZ conversion).

### 3.3 Schedule (EventBridge `AWS::Events::Rule`, UTC)

Vietnam (`Asia/Ho_Chi_Minh`) has **no DST**. 00:00 ICT = 17:00 UTC every day.

| Job | ICT | UTC cron | Input |
|-----|-----|----------|-------|
| news | 00:00 | `cron(0 17 * * ? *)` | `{"job":"news"}` |
| price | 00:00 | `cron(0 17 * * ? *)` | `{"job":"price"}` |
| snapshot | 00:00 | `cron(0 17 * * ? *)` | `{"job":"snapshot"}` |
| email | 00:15 | `cron(15 17 * * ? *)` | `{"job":"email"}` |

Remove the current news rule `cron(0 1 * * ? *)` (08:00 ICT) from `infra/cloudformation.yml`. Do **not** leave two news schedules.

Do **not** sleep 15 minutes inside Lambda. The delay is a **second rule**.

Same-minute news/price/snapshot may overlap. Accepted: email waits 15 minutes. Extra guard: skip user if today’s **snapshot** is missing. Missing news is **not** a skip — the news section is empty.

### 3.4 Config

| Env | Required when | Notes |
|-----|---------------|-------|
| `SES_FROM_EMAIL` | email job actually sending | Verified SES identity. **Not** part of `validate_job_runtime()` so news/price/snapshot still start without SES. |
| `AWS_REGION` | already | SES client region; default `us-east-1` |

### 3.5 Data (no new tables)

```
Users: email, emailOptIn (existing)
Holdings / Watchlist: symbols for news needles (existing)
Snapshots: PK userId  SK SNAP#YYYY-MM-DD
  payload.totalsByCurrency.{ccy}.{marketValue,costBasis,pnl}
  payload.lines[].{symbol,assetType,qty,currency,marketValue,costBasis,pnl,missingPrice}
News: existing items with title, url, source, symbols[], date
JobRuns: job_type=email  counts={users_*, sent, skipped_opt_out, skipped_no_email, skipped_no_snapshot, first_snapshot, news_attached, failed}
```

Email **does not** write snapshots or news. It:

1. `snapshot_repo.get(userId, today)` / `get(userId, yesterday)`
2. `holdings_repo.list` + `watchlist_repo.list` → symbol needles
3. `news_repo.list_recent` → filter to those needles → cap **5** newest

Do **not** call `NewsService.list_for_user`: that falls back to the full market board when nothing matches, which would dump unrelated headlines into SES.

### 3.6 `EmailSender` port

```python
@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text_body: str
    html_body: str | None = None

class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None:
        ...
```

SES adapter: `boto3` `ses.send_email` (Source=`SES_FROM_EMAIL`, ToAddresses=`[to]`). Raise a small `EmailSendError` on `ClientError`; job isolates per user.

Recording fake: append messages to `sent: list[EmailMessage]`; optional `fail_for: set[str]`.

---

## 4. Sequence (happy path)

```
00:00 ICT  EventBridge ──► Lambda {"job":"news"}
00:00 ICT  EventBridge ──► Lambda {"job":"price"}
00:00 ICT  EventBridge ──► Lambda {"job":"snapshot"}
              snapshot date = ICT today
              S3 + Dynamo SNAP#{ict_today}

00:15 ICT  EventBridge ──► Lambda {"job":"email"}
              settings.jobs_email && settings.email_enabled?
              for profile in iter_all:
                skip unless email_opt_in
                skip unless valid email
                today = snapshot_repo.get(id, ict_today)
                skip if today is None
                yesterday = snapshot_repo.get(id, ict_today - 1 day)
                needles = holding symbols ∪ watchlist symbols
                news = list_recent filtered by needles, max 5
                EmailSender.send(totals + per-line PnL + news)
              JobRuns.put(email)
```

ASCII:

```
1. User saves emailOptIn=true (Cognito email already on profile).
2. Admin enables daily email (jobs.email + emailEnabled).
3. Midnight ICT: news ingest + price warm-cache + snapshot for ICT calendar date.
4. 00:15 ICT: email job reads snapshots + News table; SES to opt-in users.
5. User sets emailOptIn=false → later crons skip (no SES).
```

---

## 5. Decisions (ADR style)

| # | Context | Decision | Consequence | Alternatives rejected |
|---|---------|----------|-------------|-----------------------|
| D1 | Opt-in storage | Reuse `UserProfile.email_opt_in` / `emailOptIn`; default **false** | No schema change; Settings checkbox is the switch | New table / Cognito custom attr |
| D2 | Clock | Fixed EventBridge crons in **UTC** for ICT midnight / +15 min | Simple, no hourly poll, matches stakeholder | PRD D4 hourly + `emailTime` window; `time.sleep(900)` in Lambda |
| D3 | Snapshot date at 17:00 UTC | Default omitted date = **`Asia/Ho_Chi_Minh` today** (`zoneinfo`) | Avoids writing `SNAP#UTC-yesterday` and clobbering the previous ICT day. BL-030 literal `date` override unchanged | Keep UTC today (wrong at 00:00 ICT) |
| D4 | Race | 15 min EventBridge gap **plus** skip if today’s snapshot missing | Email never live-recomputes portfolio or re-fetches RSS | Wait/retry loop; email calling `get_portfolio` |
| D5 | Totals delta | `today.totalsByCurrency[ccy].marketValue` − yesterday same key; `%` when yesterday ≠ 0. PnL = `totals.pnl` (vs cost) | Balance + PnL from stored snapshot | Athena; live quotes |
| D6 | Currency | `profile.preferred_currency` or settings default or `USD`; if that key missing, first totals key. Per-line keep native `line.currency` | Totals in display ccy; lines stay as snapshotted | Convert every line in the job (needs FX) |
| D7 | Admin flags | Send only if `jobs_email` **and** `email_enabled`; one checkbox sets both | Matches existing fields without two confusing switches | Ignore `emailEnabled` |
| D8 | News cron | **Move news to 00:00 ICT** with price+snapshot; delete 08:00 ICT rule | Email at 00:15 can include tonight’s ingest | Keep 08:00 ICT (rejected by stakeholder) |
| D9 | Idempotency | Per-user isolate; no sent-log table. Rare SES duplicate on retry OK for demo | Fits student scale | Dynamo `EMAIL#{user}#{date}` |
| D10 | From address | `SES_FROM_EMAIL` env on Lambda | Fail email job if empty when flags are on | Hardcoded address in repo |
| D11 | Per-asset performance | Every `payload.lines[]` row: PnL vs cost, PnL%, day Δ marketValue vs yesterday line keyed by `(assetType, symbol)` | Holdings only (snapshot scope) | Watchlist quotes from PriceCache |
| D12 | Related news | Needles = holding symbols ∪ watchlist symbols. Match title or `item.symbols` (same `_matches` idea as news_service). Cap 5, newest first. **No** `newsKeywords`. **No** market-board fallback | Empty section if none | `NewsService.list_for_user` (dumps market news) |
| D13 | Caps | Holdings: all lines up to **30**, then “and N more”. News: **5** | Keeps SES small | Full dump |

---

## 6. Complexity assessment

- [ ] Requires choosing between ≥2 libs/patterns → Researcher needed
- [x] Security / auth / cost-critical AWS path (SES IAM + sandbox) — **known pattern**, no extra research ticket
- [ ] No prior port/adapter pattern to reuse (EmailSender is new but identical to other ports)
- [x] Touches locked D4 — **explicitly superseded** in this design

**Verdict:** `simple`

SES: [SendEmail](https://docs.aws.amazon.com/ses/latest/APIReference/API_SendEmail.html). EventBridge cron is UTC for `AWS::Events::Rule`.

---

## 7. Handoff to Implementor

### File ownership

**Allowed:** listed surfaces in §2; `docs/prd/OpenPortfo_PRD.md` D4 one-line update; `docs/architecture-design.md` §5 schedule times.

**Must NOT:** API Gateway; FastAPI route that sends email; FX job; RSS ingest/NLP rewrite; `NewsService.list_for_user` fallback in the email path; commit secrets; deploy/mutate real AWS without a later explicit instruction.

### Snapshot date helper

Share a tiny `ict_today() -> str` (ISO date) used by snapshot (when override is None) and email (today/yesterday). Tests freeze time with a known instant:

- `2026-09-12T17:00:00+00:00` → ICT date `2026-09-13`
- `2026-09-12T01:30:00+00:00` → ICT date `2026-09-12` (old 08:30 ICT cron still consistent)

### Email body (locked MVP)

Subject: `OpenPortfo daily update — {ict_today}`

Text (English):

```
Portfolio ({ccy}) on {ict_today}

Value: {today_value}
Yesterday: {yesterday_value or "n/a"}
Day change: {delta} ({pct}%)   # or "n/a" on first day
PnL vs cost: {pnl} ({pnl_pct}%)

Holdings
SYMBOL  TYPE    VALUE     PnL vs cost      Day change
BTC     crypto  12,000    +800 (+7.1%)     +120 (+1.0%)
VNM     stock   5,000,000 -200,000 (-3.8%) n/a
… up to 30 lines, then "and N more"

Related news
- {title} ({source}) — {url}
  matched: BTC
… up to 5 items, or "No related news today."

Turn this off any time in Settings → Receive daily portfolio email.
```

HTML: simple tables for holdings + an `<ul>` of news links. Same fields. No CSV/PDF attachment.

**Per-asset math (from snapshot lines only):**

- Key: `(assetType, symbol)` case-insensitive.
- PnL vs cost = `line.pnl`; `%` = `pnl / costBasis` when `costBasis != 0`.
- Day change = today’s `marketValue` − yesterday’s same key; `%` vs yesterday value when ≠ 0.
- `missingPrice=true` → show `n/a` for value/PnL/day change on that row.

**News match:** `needle.casefold()` in `title.casefold()` **or** in `item.symbols` (casefold). Needles from current holdings ∪ watchlist, not from yesterday’s snapshot and not from `newsKeywords`.

### TDD order

1. **Failing:** `handler({"job":"email"})` with flags on, opt-in user, today+yesterday snapshots → fake sender 1 message containing **portfolio PnL** and **each holding line**; opt-out user 0.
2. Implement `EmailSender` fake + `run_email_job` + handler branch (no boto3).
3. **Failing:** no today snapshot → 0 sends, `skipped_no_snapshot`.
4. **Failing:** flags off → `status=skipped`, 0 sends.
5. **Failing:** snapshot omitted date at 17:00 UTC is ICT date per §7 table (update existing UTC-today tests).
6. **Failing:** news item matching holding/watchlist symbol appears in body; market-only / keywords-only item does **not**; zero matches still sends with empty news line.
7. SES adapter unit test with stubbed boto3 client (or botocore stub).
8. CFN: news+price+snapshot `cron(0 17 * * ? *)`; email `cron(15 17 * * ? *)`; delete `cron(0 1 * * ? *)` news rule; `ses:SendEmail` on `LambdaExecutionRole`.
9. Frontend copy + admin toggle + Vitest; Playwright settings checkbox save.
10. Docs: lambda README invoke `{"job":"email"}`; SES sandbox verify-from/to runbook note.

### Out-of-scope guardrails

- No `time.sleep` for the 15-minute gap.
- No `get_portfolio` or RSS fetch inside the email job.
- No SES in `validate_job_runtime`.
- Do not use LocalStack as proof SES works.
- Do not use `NewsService.list_for_user` (market fallback).

---

## 8. Acceptance criteria checklist (copy from feature file)

- [ ] AC1: `emailOptIn` switch; default off; off users never sent.
- [ ] AC2: news+price+snapshot `cron(0 17 * * ? *)`; email `cron(15 17 * * ? *)`; old 08:00 ICT news rule gone.
- [ ] AC3: omitted snapshot date = ICT today.
- [ ] AC4: email job uses snapshots; respects admin flags + opt-in.
- [ ] AC5: missing today snapshot → skip user, no send.
- [ ] AC6: body has portfolio PnL + per-holding performance.
- [ ] AC7: news section = holdings/watchlist matches only, max 5; empty news still sends.
- [ ] AC8: ports isolation; SES IAM; fake in unit tests.
- [ ] AC9: backend suite + frontend tests + Playwright settings; no LocalStack-as-SES.

---

## 9. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| SES sandbox rejects unverified `To` | Runbook: verify `SES_FROM_EMAIL` and demo recipient; JobRun `failed` + message, other users continue |
| 00:00 news/price/snapshot overlap | Accepted; email still 15 min later |
| RSS slow → empty news section | Accepted; do not block send |
| UTC snapshot date clobber | D3 ICT calendar date |
| `list_for_user` dumping market news | D12 dedicated filter |
| Lab CFN cannot create IAM/EventBridge | Document LabRole SES attach + console rules; full `cloudformation.yml` has the IaC |
| Assignment marks | SES is 0 rubric marks; still a demo-strong stretch |
| Lambda retry duplicate mail | D9; acceptable for demo volume |

---

## 10. Research linkage (if any)

- No separate research doc. Primary: AWS SES `SendEmail`; EventBridge cron UTC; `zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")` on Python 3.12.

---

**SA sign-off:** `_ready_for_implementation_` when Eng follows TDD order and AC1–AC9 have executable evidence. Do not implement until the stakeholder says to build it (this request was plan-only).
