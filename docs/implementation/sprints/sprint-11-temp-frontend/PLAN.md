# Sprint 11 — Detailed Plan: Temp view-only frontend

| | |
|--|--|
| **ID** | S11 |
| **Depends on** | Minimum S05+S06; ideal APIs through S10 |
| **Owns** | `frontend-temp/**` only |
| **PRD** | Dev/demo viewer (not final Next.js / CloudFront) |

---

## 1. Objective

Temporary browser UI to exercise the backend. Optimized for verification, not assessment UI polish.

---

## 2. Stack (locked)

| Choice | Value |
|--------|--------|
| Tooling | Vite |
| UI | Vanilla JS **or** minimal React (pick one; vanilla preferred for speed) |
| API base | `VITE_API_URL=http://127.0.0.1:8000` |
| Auth | Paste Bearer token → `sessionStorage` |

---

## 3. Screens

| Screen | Backend calls | Notes |
|--------|---------------|--------|
| Health | GET /health | |
| Auth bar | — | paste fake/Cognito token |
| Me | GET /api/auth/me | |
| Holdings | CRUD /api/holdings | simple forms |
| Watchlist | CRUD /api/watchlist | |
| Portfolio | GET + POST refresh | table + totals |
| FX admin | GET /fx/rates, POST admin refresh | show error; keep old rates |
| News | GET /api/news | titles + links |
| History | GET history | JSON dump or Chart.js CDN |
| Admin settings | optional | if S09 available |

---

## 4. Out of scope

- Full Cognito Hosted UI (optional external link OK)  
- Next.js SSR / app router  
- Design system / production styling  
- S3 + CloudFront deploy  

---

## 5. Multiagent rule

**Do not modify backend.** File bugs to orchestrator if API broken.

---

## 6. Manual QA checklist (acceptance)

- [ ] Health OK  
- [ ] Me with fake token from S02 handoff  
- [ ] Create holding → visible in portfolio  
- [ ] Price refresh works  
- [ ] Admin FX refresh success  
- [ ] FX fail path: error shown, previous rates remain  
- [ ] News list loads  

---

## 7. Agent prompt

```
Sprint 11 ONLY. Build frontend-temp against existing API.
VITE_API_URL + token paste. No backend refactors.
Document manual QA results in handoff.
```

---

## 8. Exit criteria

- [ ] All checklist items pass against local API  
- [ ] README in frontend-temp: how to run  
