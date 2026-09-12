# BL-032 — Daily SES portfolio balance-change email

| Field | Value |
|-------|--------|
| **ID** | `BL-032` |
| **Title** | User opt-in daily email of portfolio balance change (EventBridge → Lambda → SES) |
| **Priority** | `P1` |
| **Status** | `ready` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | FR-J5, FR-J7, S1; sprint-13-stretch; snapshot job FR-J4 / BL-030 |
| **Created** | 2026-09-12 |
| **Ready date** | 2026-09-12 |
| **Done date** | |

---

## 1. Problem / user value

Users can already snapshot holdings daily and toggle `emailOptIn`, but nothing sends mail. They need a **daily AWS email** that reports **portfolio balance vs yesterday**, with a switch to opt in or out. Snapshot and email must not race: jobs at **00:00 ICT**, email **15 minutes later**.

---

## 2. User story

As a **signed-in investor**, I want **to turn daily portfolio emails on or off**, so that **I get one SES summary at 00:15 ICT with today’s value and the change vs yesterday — or I get none**.

---

## 3. Scope

### In scope

- Settings checkbox already persisted as `emailOptIn` (default **off**). Clarify copy + helper that this is the **daily portfolio email**.
- Admin global enable: `jobs.email` **and** `emailEnabled` must both be true (single admin checkbox writes both).
- New Lambda job `{"job":"email"}` via `EmailSender` port + SES adapter.
- EventBridge (UTC, Vietnam has no DST):
  - **00:00 ICT** = `cron(0 17 * * ? *)` → `price` and `snapshot`
  - **00:15 ICT** = `cron(15 17 * * ? *)` → `email`
- Email body: today’s snapshot totals vs yesterday’s, in the user’s preferred currency (fallback USD).
- Snapshot **calendar date** for omitted `date` becomes **Asia/Ho_Chi_Minh today** (required at 17:00 UTC so we do not overwrite yesterday’s UTC-dated row).
- If today’s snapshot is missing, **skip that user** (second race guard after the 15-minute delay).
- IAM `ses:SendEmail` on the jobs Lambda role (full CFN). Lab: document attach to LabRole.
- Unit tests with a recording fake sender. Playwright: settings opt-in round-trip only.

### Out of scope

- HTTP `POST /api/admin/jobs/email/run` or a “Send now” UI.
- Hourly Lambda + `emailTime` window matching (PRD **D4** superseded by this locked cron).
- HTML marketing templates, attachments, CSV, push/SMS, unsubscribe links beyond Settings.
- Moving the **news** job (stays `cron(0 1 * * ? *)` = 08:00 ICT).
- Leaving SES sandbox; verifying tutor inboxes in this ticket (runbook only).
- Changing FX to a scheduled fetch.
- Real AWS deploy/push unless a later instruction authorizes it.

---

## 4. Behaviour

### Happy path

1. User opens Settings → General, checks **Receive daily portfolio email**, saves. Profile `emailOptIn=true`.
2. Admin enables **Daily portfolio email** (`jobs.email` + `emailEnabled`).
3. 00:00 ICT: EventBridge invokes `{"job":"price"}` and `{"job":"snapshot"}`. Snapshot date = ICT today.
4. 00:15 ICT: EventBridge invokes `{"job":"email"}`.
5. Job iterates users; for each opt-in user with a valid email and today’s snapshot, SES sends one mail:
   - subject: `OpenPortfo daily update — YYYY-MM-DD`
   - today’s market value, yesterday’s value, absolute + percent change, PnL vs cost
6. User unchecks the setting and saves → later runs skip that user.

### Edge cases / errors

| Case | Behaviour |
|------|-----------|
| `emailOptIn=false` (default) | Skip user; count `skipped_opt_out` |
| Missing / invalid profile email | Skip user; count `skipped_no_email` |
| No snapshot for ICT today | Skip user; count `skipped_no_snapshot` (do not live-recompute) |
| No snapshot for yesterday | Still send; change fields `n/a` / omitted; count `first_snapshot` |
| `jobs.email=false` or `emailEnabled=false` | Whole job `skipped`; no SES calls |
| SES send fails for one user | Isolate; continue; user counts as failed; aggregate `partial`/`error` |
| Lambda retry same day | Best-effort: skip user if `counts`/`JobRun` already recorded success for `userId+date` **or** accept rare duplicate in sandbox (see design D9) |
| `SES_FROM_EMAIL` unset | Job `error`, no sends |

### UX notes

- Screens / routes: `/settings` General tab (existing checkbox); `/admin` job controls (new email toggle). No new page.
- Empty / loading / error: reuse settings save/error; admin conflict reload (same as news toggle).
- Helper text: emails go to the Cognito account email at **00:15 Asia/Ho_Chi_Minh**.

---

## 5. Acceptance criteria

- [ ] **AC1** Settings checkbox round-trips `emailOptIn` (default false). Copy states daily portfolio email. Off users never receive SES in the job.
- [ ] **AC2** EventBridge: price + snapshot at `cron(0 17 * * ? *)`; email at `cron(15 17 * * ? *)`. News cron unchanged.
- [ ] **AC3** Omitted snapshot `date` uses **ICT today** (`Asia/Ho_Chi_Minh`), not UTC. At 17:00 UTC on 2026-09-12 that is `2026-09-13`.
- [ ] **AC4** `handler({"job":"email"})` sends only when admin flags are on **and** user `emailOptIn` is true, using today’s vs yesterday’s snapshots for the delta.
- [ ] **AC5** Missing today’s snapshot → no send for that user (`skipped_no_snapshot`).
- [ ] **AC6** Jobs stay ports-only (`boto3` only in SES adapter). Lambda IAM includes SES. Fake sender in unit tests.
- [ ] **AC7** Focused pytest + full backend suite; frontend Vitest for copy/toggle; Playwright settings save; LocalStack probe **not** used as SES proof.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | DynamoDB profiles (`email`, `emailOptIn`) + snapshots; SES for delivery |
| New / changed APIs | No new FastAPI routes. Lambda event `{"job":"email"}` |
| Auth required? | Settings: signed-in user. Admin toggle: admin. Job: IAM |
| Caching / freshness | Email **reads snapshots only** (`force_refresh` unused) |
| Jobs / schedules | Price+snapshot 17:00 UTC; email 17:15 UTC |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `GeneralTab`, i18n, `JobControlsPanel`, Vitest, Playwright settings |
| Backend API | Admin settings PUT already has `jobs.email` / `emailEnabled` — wire UI only |
| Domain / services | Optional small helper to format snapshot delta (or keep in job) |
| Adapters | `ports/email.py`, `adapters/ses/`, recording fake |
| Infra / jobs | `email_job.py`, `handler.py`, `JobContext`, CFN EventBridge + SES IAM |
| Docs / tests | `infra/lambda/README.md`, arch schedule note, job unit tests |

---

## 8. Dependencies & risks

- Depends on: existing snapshot job, `emailOptIn` persistence, EventBridge rules pattern.
- Risks: SES sandbox (verified recipients only); same-minute price vs snapshot race (email still waits 15 min); ICT vs UTC date (mitigated by AC3).

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Fixed midnight cron vs PRD D4 hourly `emailTime` window? | resolved | Fixed 00:00 / 00:15 ICT. `emailTime` stored but unused for send. |
| 2 | Move news to midnight too? | resolved | No. News stays 08:00 ICT. |
| 3 | First-day email without yesterday? | resolved | Send; delta n/a. |
| 4 | Email language? | resolved | English body (profile has no language field). |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-09-12 | Daily SES balance email + opt-in + 00:00 ICT jobs + email +15 min | Allocated BL-032; locked schedule and skip-if-no-snapshot |

---

## 11. Implementation notes (Eng fills after `ready`)

- Approach: see `docs/orchestration/designs/BL-032-daily-ses-balance-email-design.md`
- PR / branch:
- Verification:
