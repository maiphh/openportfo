# SA Design — BL-032: Daily SES portfolio balance-change email

| Field | Value |
|-------|-------|
| **ID** | `BL-032` |
| **Title** | User opt-in daily email of portfolio balance change |
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
2. **Daily crons at 00:00 UTC+7** for the portfolio pipeline.
3. **Email 15 minutes later** so it cannot run before snapshots exist.

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
| price | 00:00 | `cron(0 17 * * ? *)` | `{"job":"price"}` |
| snapshot | 00:00 | `cron(0 17 * * ? *)` | `{"job":"snapshot"}` |
| email | 00:15 | `cron(15 17 * * ? *)` | `{"job":"email"}` |
| news | 08:00 (unchanged) | `cron(0 1 * * ? *)` | `{"job":"news"}` |

Do **not** sleep 15 minutes inside Lambda. The delay is a **second rule**.

Same-minute price vs snapshot may overlap (cache-first snapshot). That is accepted; the stakeholder race is **email vs snapshot**, not price vs snapshot.

### 3.4 Config

| Env | Required when | Notes |
|-----|---------------|-------|
| `SES_FROM_EMAIL` | email job actually sending | Verified SES identity. **Not** part of `validate_job_runtime()` so news/price/snapshot still start without SES. |
| `AWS_REGION` | already | SES client region; default `us-east-1` |

### 3.5 Data (no new tables)

```
Users: email, emailOptIn (existing)
Snapshots: PK userId  SK SNAP#YYYY-MM-DD  payload.totalsByCurrency / lines (existing)
JobRuns: job_type=email  counts={users_*, sent, skipped_opt_out, skipped_no_email, skipped_no_snapshot, first_snapshot, failed}
```

Email **does not** write snapshots. It `get(userId, today)` and `get(userId, yesterday)`.

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
                EmailSender.send(...)
              JobRuns.put(email)
```

ASCII:

```
1. User saves emailOptIn=true (Cognito email already on profile).
2. Admin enables daily email (jobs.email + emailEnabled).
3. Midnight ICT: price warm-cache + snapshot for ICT calendar date.
4. 00:15 ICT: email job reads snapshots only; SES to opt-in users.
5. User sets emailOptIn=false → later crons skip (no SES).
```

---

## 5. Decisions (ADR style)

| # | Context | Decision | Consequence | Alternatives rejected |
|---|---------|----------|-------------|-----------------------|
| D1 | Opt-in storage | Reuse `UserProfile.email_opt_in` / `emailOptIn`; default **false** | No schema change; Settings checkbox is the switch | New table / Cognito custom attr |
| D2 | Clock | Fixed EventBridge crons in **UTC** for ICT midnight / +15 min | Simple, no hourly poll, matches stakeholder | PRD D4 hourly + `emailTime` window; `time.sleep(900)` in Lambda |
| D3 | Snapshot date at 17:00 UTC | Default omitted date = **`Asia/Ho_Chi_Minh` today** (`zoneinfo`) | Avoids writing `SNAP#UTC-yesterday` and clobbering the previous ICT day. BL-030 literal `date` override unchanged | Keep UTC today (wrong at 00:00 ICT) |
| D4 | Race | 15 min EventBridge gap **plus** skip if today’s snapshot missing | Email never live-recomputes portfolio | Wait/retry loop; email calling `get_portfolio` |
| D5 | Delta | `today.totalsByCurrency[ccy].marketValue` − yesterday same key; `%` = delta/yesterday when yesterday ≠ 0 | “Balance change” without new math module | Athena query; 24h price API |
| D6 | Currency | `profile.preferred_currency` or settings default or `USD`; if that key missing, first totals key | Matches dashboard preference | Always USD |
| D7 | Admin flags | Send only if `jobs_email` **and** `email_enabled`; one checkbox sets both | Matches existing fields without two confusing switches | Ignore `emailEnabled` |
| D8 | News cron | Leave 08:00 ICT | Smaller blast radius | Move all jobs to midnight |
| D9 | Idempotency | Per-user isolate; do not add a new sent-log table. Document rare SES duplicate on Lambda retry | Fits student scale | Dynamo `EMAIL#{user}#{date}` conditional put (can add later) |
| D10 | From address | `SES_FROM_EMAIL` env on Lambda | Fail email job if empty when flags are on | Hardcoded address in repo |

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

**Must NOT:** API Gateway; FastAPI route that sends email; FX job; news ingest rewrite; commit secrets; deploy/mutate real AWS without a later explicit instruction.

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
Change: {delta} ({pct}%)   # or "n/a" on first day
PnL vs cost: {pnl}

Turn this off any time in Settings → Receive daily portfolio email.
```

Keep HTML as a simple `<pre>`/`<p>` mirror of the same fields. No holdings dump (size / SES sandbox).

### TDD order

1. **Failing:** `handler({"job":"email"})` with `jobs.email=True`, `emailEnabled=True`, user `email_opt_in=True`, snapshots for today+yesterday → fake sender has 1 message with delta; opt-out user has 0.
2. Implement `EmailSender` fake + `run_email_job` + handler branch (no boto3).
3. **Failing:** no today snapshot → 0 sends, `skipped_no_snapshot`.
4. **Failing:** flags off → `status=skipped`, 0 sends.
5. **Failing:** snapshot omitted date at 17:00 UTC is ICT tomorrow/today as §7 table (update existing UTC-today tests).
6. SES adapter unit test with stubbed boto3 client (or botocore stub).
7. CFN: crons + `EmailScheduleRule` + `ses:SendEmail` on `LambdaExecutionRole`.
8. Frontend copy + admin toggle + Vitest; Playwright settings checkbox save.
9. Docs: lambda README invoke `{"job":"email"}`; SES sandbox verify-from/to runbook note.

### Out-of-scope guardrails

- No `time.sleep` for the 15-minute gap.
- No `get_portfolio` inside the email job.
- No SES in `validate_job_runtime`.
- Do not use LocalStack as proof SES works.

---

## 8. Acceptance criteria checklist (copy from feature file)

- [ ] AC1: `emailOptIn` switch; default off; off users never sent.
- [ ] AC2: price+snapshot `cron(0 17 * * ? *)`; email `cron(15 17 * * ? *)`; news unchanged.
- [ ] AC3: omitted snapshot date = ICT today.
- [ ] AC4: email job uses snapshots for balance change; respects admin flags + opt-in.
- [ ] AC5: missing today snapshot → skip user, no send.
- [ ] AC6: ports isolation; SES IAM; fake in unit tests.
- [ ] AC7: backend suite + frontend tests + Playwright settings; no LocalStack-as-SES.

---

## 9. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| SES sandbox rejects unverified `To` | Runbook: verify `SES_FROM_EMAIL` and demo recipient; JobRun `failed` + message, other users continue |
| 00:00 price/snapshot overlap → slightly stale print | Accepted; email still 15 min later |
| UTC snapshot date clobber | D3 ICT calendar date |
| Lab CFN cannot create IAM/EventBridge | Document LabRole SES attach + console rules; full `cloudformation.yml` has the IaC |
| Assignment marks | SES is 0 rubric marks; still a demo-strong stretch |
| Lambda retry duplicate mail | D9; acceptable for demo volume |

---

## 10. Research linkage (if any)

- No separate research doc. Primary: AWS SES `SendEmail`; EventBridge cron UTC; `zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")` on Python 3.12.

---

**SA sign-off:** `_ready_for_implementation_` when Eng follows TDD order and AC1–AC7 have executable evidence. Do not implement until the stakeholder says to build it (this request was plan-only).
