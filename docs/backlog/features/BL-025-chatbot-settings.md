# BL-025 — Chatbot settings (models, params) — Settings tab + backend config

| Field | Value |
|-------|--------|
| **ID** | `BL-025` |
| **Title** | Chatbot control tab: model selection, params (temperature, max tokens, …) |
| **Priority** | `P1` |
| **Status** | `ready` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | |
| **Requested by** | Product |
| **Related PRD / sprint** | sprint-06; logic ref: Open WebUI model params (temperature/top_p/etc.) |
| **Created** | 2026-08-23 |
| **Ready date** | 2026-08-23 |
| **Done date** | |

---

## 1. Problem / user value

Chatbot behavior is configured **only via env** (`LLM_DEFAULT_MODEL`, `LLM_FALLBACK_MODELS`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS`, …). Product wants a **Chatbot tab in Settings** where an admin can control the model and inference params at runtime (Open WebUI exposes temperature / top_p / max tokens / etc. per model).

---

## 2. User story

As an **admin**, I want **to pick the chatbot model and tune params from the Settings page**, so that **I can adjust the assistant without redeploying**.

---

## 3. Scope

### In scope

**Backend:**
- Extend **SystemSettings** (`SettingsRepo`, both adapters) with chat overrides, e.g. `chat_model`, `chat_fallback_models`, `chat_temperature`, `chat_top_p`, `chat_max_tokens`, `chat_system_prompt_extra` — **null = use env default** (exact field list SA decides; DB overrides env).
- Resolution: `get_chat_service()`/LLM call path merges env Settings with DB SystemSettings (DB wins when set); invalid/blank values fall back to env. Cache invalidation when saved (follow `set_market_service(None)` pattern).
- `GET/PUT /api/admin/settings` extended to expose the chat section; validation (ranges for temperature/top_p, non-empty model ids).
- Optional: `GET /api/admin/chat/models` — list selectable models derived from `LLM_FALLBACK_MODELS` env (+ current default). No live provider enumeration required.

**Frontend:**
- **Chatbot tab** in `/settings` (admin-only visibility): current model selector (from models list), params form (sliders/number inputs per param), system prompt textarea, Save → `PUT /api/admin/settings`, shows effective-vs-default values.

### Out of scope

- Per-user chat params; live provider model listing API; prompt playground/testing UI; multiple named model profiles.

---

## 4. Behaviour

### Happy path

1. Admin opens Settings → Chatbot tab → loads current effective config (DB override or env default, labeled).
2. Changes model + temperature → Save → subsequent chat requests use new values.
3. Clearing a field → falls back to env default.

### Edge cases / errors

- Out-of-range values → 400 with field errors.
- Chat stream in flight during change → next request picks up new config.

---

## 5. Acceptance criteria

- [ ] SystemSettings carries chat fields; both adapters persist them (pytest).
- [ ] Chat request path honors DB overrides over env defaults (pytest with fake provider asserting received params).
- [ ] Admin API validates ranges; FE tab saves + shows effective values.
- [ ] Unit tests green both sides.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | SystemSettings (DB) overriding env `Settings` |
| New / changed APIs | extended `/api/admin/settings`; optional `/api/admin/chat/models` |
| Auth required? | admin |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `components/settings/ChatbotTab.tsx` |
| Backend API | `app/api/admin.py`, `app/core/deps.py` (chat service wiring), `app/adapters/llm/*` (param pass-through), `app/services/llm/chat_service.py` |
| Docs / tests | pytest: settings repo + merge logic + API; vitest: chatbot tab |

---

## 8. Dependencies & risks

- Depends on: BL-023 (tab shell).
- Risks: FallbackProvider/openai_compat currently read model from env at build time — must thread overrides through without breaking fallback behavior.

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Exact param set exposed | open | SA decision (temperature, top_p, max_tokens, fallback models, system prompt extra recommended) |
| 2 | Models list source | open | SA decision (env-derived recommended) |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-23 | Batch created | — |
