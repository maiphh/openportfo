# SA Design — BL-034: Gmail SMTP demo email

| Field | Value |
|-------|-------|
| **ID** | `BL-034` |
| **Title** | Gmail SMTP adapter when Academy SES is blocked |
| **Status** | `implemented` |
| **Author (SA)** | SA |
| **Date** | 2026-09-13 |
| **Complexity** | `simple` |
| **Related PRD** | FR-J5 / D5 stretch email |
| **Related Arch** | SES remains the AWS target; SMTP is lab/demo only |
| **Feature file** | `docs/backlog/features/BL-034-gmail-smtp-demo-email.md` |

## 1. Context

BL-032 email job is ports-only. Learner Lab blocks `ses:*`. Stakeholder asked for the **simplest free inbox demo**. Choice: **Gmail SMTP + App Password** (no domain, no third-party signup).

## 2. Affected surfaces

| Layer | Paths | Change |
|-------|-------|--------|
| Ports | `ports/email.py` | reuse |
| Adapters | `adapters/smtp/sender.py` **NEW** | stdlib SMTP |
| Core | `config.py`, `deps.py` `build_email_sender` | SMTP fields; prefer SMTP if creds set |
| Jobs | `email_job.py` | **none** |
| Docs / tests | `.env.example`, `infra/lambda/README.md`, `tests/unit/adapters/test_smtp_sender.py` | new |

## 3. Config

| Env | Default | Required to send |
|-----|---------|------------------|
| `SMTP_HOST` | `smtp.gmail.com` | no |
| `SMTP_PORT` | `587` | no |
| `SMTP_USERNAME` | empty | yes |
| `SMTP_PASSWORD` | empty | yes (Gmail App Password) |
| `SMTP_FROM` | empty → username | no |
| `SES_FROM_EMAIL` | unused if SMTP_FROM/username present | no |

Selection: SMTP creds → `SmtpEmailSender`; else BL-032 SES/memory.

## 4. Decisions

| # | Decision |
|---|----------|
| D1 | Gmail SMTP over Brevo/Resend — zero extra account, From can be the student’s Gmail |
| D2 | STARTTLS 587, stdlib only |
| D3 | SMTP wins over SES when creds set so local `STORAGE_BACKEND=aws` still delivers |

## 5. TDD order

1. Failing SMTP mock test.
2. Adapter + config + `build_email_sender`.
3. Docs.

## 6. AC copy

AC1 mock send; AC2 sender selection; AC3 isolation; AC4 pytest, no secrets.
