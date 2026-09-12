# SA Review — BL-034: Gmail SMTP demo email

| Field | Value |
|-------|-------|
| **ID** | `BL-034` |
| **Date** | 2026-09-13 |
| **Walkthrough** | `docs/orchestration/walkthroughs/BL-034-walkthrough.md` |
| **Verdict** | `approve` |

## AC

| AC | Satisfied? | Evidence |
|----|------------|----------|
| AC1 mock SMTP | yes | `test_smtp_sender_starttls_login_and_send` |
| AC2 prefers SMTP | yes | `test_build_email_sender_prefers_smtp_over_ses` |
| AC3 isolation | yes | `smtplib` only in `adapters/smtp/sender.py`; jobs unchanged |
| AC4 pytest / no secrets | yes | 5 new tests; App Password not in git |

## Architecture

- [x] Email still via `EmailSender` port
- [x] SES remains AWS path; SMTP is lab/demo only
- [x] No `boto3`/`smtplib` in jobs/services

## Decision

**approve.** Residual: user must create a Google App Password before a real inbox send.
