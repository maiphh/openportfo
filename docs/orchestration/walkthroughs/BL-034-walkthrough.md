# Walkthrough — BL-034: Gmail SMTP demo email

| Field | Value |
|-------|-------|
| **ID** | `BL-034` |
| **Branch** | `feat/BL-032-daily-ses-email` |
| **Date** | 2026-09-13 |

## Summary

Academy SES is blocked. Daily mail can use **Gmail SMTP** when `SMTP_USERNAME` + `SMTP_PASSWORD` (App Password) are set. Job code unchanged.

## Files

| File | Change |
|------|--------|
| `backend/app/adapters/smtp/sender.py` | STARTTLS SMTP adapter |
| `backend/app/core/config.py` | SMTP_* fields |
| `backend/app/core/deps.py` | `build_email_sender` prefers SMTP |
| `backend/tests/unit/adapters/test_smtp_sender.py` | mock SMTP + selection |
| `backend/.env.example`, `infra/lambda/README.md` | App Password steps |

## Verify

`pytest tests/unit/adapters/test_smtp_sender.py` — 5 passed.

Full `verify.ps1 -Profile full`: ports-isolation pass; backend 585 passed + **4 pre-existing** FX `stale_ok` vs `fresh`; frontend/Playwright/LocalStack pass.

## Limitations

Real Gmail send still needs a Google App Password in `SMTP_PASSWORD` (not committed).
