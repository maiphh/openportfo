# BL-034 — Gmail SMTP demo email (SES lab fallback)

| Field | Value |
|-------|--------|
| **ID** | `BL-034` |
| **Title** | Gmail SMTP adapter for daily email when Academy SES is blocked |
| **Priority** | `P1` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Eng |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | FR-J5, D5; BL-032 |
| **Created** | 2026-09-13 |
| **Ready date** | 2026-09-13 |
| **Done date** | 2026-09-13 |

---

## 1. Problem / user value

AWS Academy Learner Lab **denies SES** (org SCP). The daily email job works but cannot reach Gmail. Demo needs a **free, low-setup** sender that delivers to the student’s inbox.

## 2. User story

As a **demo presenter**, I want **daily portfolio mail via Gmail SMTP**, so that **I receive the BL-032 email without a personal AWS account or a custom domain**.

## 3. Scope

### In scope

- `SmtpEmailSender` behind existing `EmailSender` port (stdlib `smtplib`).
- Prefer SMTP when `SMTP_USERNAME` + `SMTP_PASSWORD` are set (even if `STORAGE_BACKEND=aws`).
- Defaults: `smtp.gmail.com:587` STARTTLS. From-address = username unless `SMTP_FROM` / `SES_FROM_EMAIL` set.
- Unit tests with a mocked SMTP client. `.env.example` + lambda README App Password steps.

### Out of scope

- Changing job content, crons, or Settings UI.
- Resend/SendGrid/Brevo. Personal AWS SES.
- Deploying Lambda env or committing the App Password.
- Leaving Gmail sandbox / workspace admin policies.

## 4. Behaviour

1. If SMTP user+password present → Gmail SMTP send.
2. Else existing SES / in-memory selection (BL-032).
3. Per-user `EmailSendError` isolation unchanged.
4. App Password spaces stripped.

## 5. Acceptance criteria

- [ ] **AC1** Mocked SMTP: STARTTLS, login, send; From/To/Subject/body match.
- [ ] **AC2** `build_email_sender` chooses SMTP when credentials set, else SES/memory as today.
- [ ] **AC3** `smtplib` only under `adapters/`. Jobs unchanged except using the port.
- [ ] **AC4** Focused pytest pass. No secrets in git.

## 6. Implementation notes (Eng fills after `ready`)

- Approach: `SmtpEmailSender` + Gmail STARTTLS; SMTP creds beat SES in `build_email_sender`
- PR / branch: `feat/BL-032-daily-ses-email`
- Verification: `test_smtp_sender.py` 5 passed; full verify — 4 pre-existing FX failures only
