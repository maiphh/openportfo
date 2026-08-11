# Sprint 13 — Detailed Plan: Stretch features

| | |
|--|--|
| **ID** | S13 |
| **Depends on** | S12 + MVP demo-ready |
| **PRD** | Stretch S1–S5 |

---

## 1. Objective

Optional features **only after** sprints 00–12 support a full demo. Do not block assessment delivery.

---

## 2. Priority order

| Prio | Feature | Implementation notes |
|------|---------|----------------------|
| 1 | SES daily email | `EmailSender` port; SES adapter; job respects email time window + opt-in; sandbox limits |
| 2 | Cognito Google IdP polish | Hosted UI / federated button; document Google redirect to Cognito |
| 3 | CSV export holdings | `GET /api/holdings/export` auth user |
| 4 | Asset-class allocation | API field + temp UI |
| 5 | Sparklines | temp UI only |

---

## 3. Rules

- One feature at a time  
- TDD with fakes for any new port  
- Must not change FX “admin on-demand only” or break portfolio math  
- SES never required for core demo path  

---

## 4. SES job sketch (if chosen)

1. Lambda/email job reads settings.email_time + timezone  
2. Run on hourly EventBridge; send only in matching window, once per user per day  
3. Only `email_opt_in` users  
4. Body: simple portfolio totals from latest snapshot  

---

## 5. Agent prompt

```
Sprint 13 ONLY if orchestrator confirms MVP done.
Implement one stretch feature with tests. Prefer SES or Google IdP.
Do not regress S00–S12 behavior.
```

---

## 6. Exit criteria

- [ ] Chosen feature demos cleanly  
- [ ] Unit tests for new logic  
- [ ] handoff + SPRINTS.md note  
