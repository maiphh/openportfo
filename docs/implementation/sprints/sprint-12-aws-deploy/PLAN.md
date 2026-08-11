# Sprint 12 — Detailed Plan: AWS deploy & real adapters

| | |
|--|--|
| **ID** | S12 |
| **Depends on** | S10–S11 |
| **PRD** | M12–M13, architecture hosting map |
| **Environment** | AWS Academy Learner Lab |

---

## 1. Objective

Connect **real adapters** to lab AWS; deploy FastAPI on Elastic Beanstalk; jobs on Lambda + EventBridge; Cognito; S3; Athena sample query. Keep unit tests **fake-default**.

---

## 2. Work packages (strict order)

### WP1 — Data plane
- DynamoDB tables matching settings names (multi-table OK)  
- S3 data bucket + `history/`, `snapshots/` prefixes  
- IAM roles: EB instance profile + Lambda role (least privilege)

### WP2 — Auth
- Cognito User Pool + public app client  
- Optional Google IdP  
- EB env: `AUTH_MODE=cognito`, pool id, client id, region  
- Callback URLs for future real frontend  

### WP3 — Adapters live
- DynamoDB repos for all ports in use  
- S3 ObjectStorage  
- CognitoJwtVerifier  
- Market HTTP clients  
- ExchangeRate client (admin only; still no cron)

### WP4 — Beanstalk
- `Procfile`: `web: uvicorn app.main:app --host 0.0.0.0 --port 8000`  
- Deploy; env vars (secrets not in git)  
- Health check `/health`  

### WP5 — Jobs
- Package `handler` for Lambda  
- EventBridge schedules: news, price, snapshot  
- **No FX schedule**  
- CloudWatch log evidence for demo  

### WP6 — Athena
- DB/table over snapshots prefix  
- Sample SQL file in this sprint folder: `athena-sample.sql`  
- Demo proof notes  

### WP7 — Runbook
- Start Lab → credentials → deploy steps  
- Cost guardrails ($10/$30 alerts if available)  
- Complete `.env.example`  

---

## 3. Out of scope

- Final Next.js on CloudFront (optional stretch)  
- SES unless S13  

---

## 4. Tests / verification

| Type | Requirement |
|------|-------------|
| Unit | Full suite green offline with fakes |
| AWS | Optional `@pytest.mark.aws` skipped by default |
| Manual smoke | health, Cognito me, one write, one job log, Athena note |

---

## 5. Agent prompt

```
Sprint 12 ONLY. Lab AWS deploy + real adapters. Do not break fake unit tests.
No FX cron. Athena sample + runbook in this sprint folder.
```

---

## 6. Exit criteria

- [ ] EB `/health` OK  
- [ ] Authenticated CRUD against DynamoDB  
- [ ] One Lambda run evidenced  
- [ ] Athena sample documented  
- [ ] No secrets committed  
