# SA Review — BL-036: One-command Beanstalk update

| Field | Value |
|-------|-------|
| **ID** | `BL-036` |
| **Reviewer (SA)** | SA (same cycle) |
| **Date** | 2026-09-13 |
| **Verdict** | `approve` |

---

## 1. AC verification

| AC | Satisfied? | Evidence | Note |
|----|------------|----------|------|
| AC1 | yes | `scripts/deploy-eb.ps1` defaults `openportfo-api` / `openportfo-api-env`; `.sh` same | |
| AC2 | yes | `create-application-version` + `update-environment`; contract test forbids `create-environment` / `cloudformation deploy` | |
| AC3 | yes | "was not found" throw; Terminated / Updating also refuse | |
| AC4 | yes | `docs/runbooks/eb-single-hosting.md` §3; `http-api-gateway.md` §3 | |

## 2. Architecture checks

- [x] Does not create Beanstalk/Lambda/CFN resources
- [x] Keeps BL-035 bake (`-ApiUrl` execute-api, `-AppUrl` https EB)
- [x] No secrets printed (no `describe-configuration-settings`)

## 3. Issues

None.

## 4. Residual risk

- Defaults are this Learner Lab's hostnames; override via `EB_*` env vars if the env CNAME changes.
- Script was not executed against AWS in this cycle (operator runs it).
- Pre-existing FX unit tests (`stale_ok` vs `fresh`) fail in `verify.ps1 -Profile quick`; unrelated.
