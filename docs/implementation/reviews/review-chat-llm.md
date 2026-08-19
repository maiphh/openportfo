## Summary
Server-side isolation holds: both chat routes require Bearer auth, tools always key holdings/watchlist/portfolio by `ctx.user.user_id` from `get_current_user`, and the user token is never placed in LLM messages (it is only copied onto unused `ToolContext.user_token`). Amount/price → qty (`10 / 50000 = 0.0002`) and weighted-average increases are correct on the happy path; partial reduce works for positive qty, but negative `qty` on `remove_holding` increases the position and mixed-currency upserts silently corrupt avg cost. `FallbackProvider` re-raises `LlmAuthError` immediately, retries 429s up to `retry_max`, then walks remaining models (not forever); `AnalystAgent` sharing the same provider is safe in production because each `complete()` is an independent HTTP call (tests must queue an extra scripted completion). Auth is present and the OpenAI-compat factory can swap OpenRouter/xAI/OpenAI, but `LLM_FREE_ONLY` is not actually server-enforced when the client sends `freeOnly: false`, and the temp UI aborts at 120s while an `analyze_*` turn can run several 90s completions.

## Issues

### Issue 1 -- Severity: bug
- File: backend/app/services/llm/chat_service.py:101
- Description: `LLM_FREE_ONLY=true` is documented as a server cost policy, but `want_free` uses the request body whenever `free_only` is not `None`. Any authenticated client can POST `{"freeOnly": false, "model": "openai/gpt-4o"}` and the paid-model check is skipped. The temp UI always sends `freeOnly` from the checkbox (`frontend-temp/src/main.js:1000`), so unchecking "free only" bills the operator key. `GET /api/chat/models` has the same hole: `free` is a required-in-practice query default (`backend/app/api/chat.py:65`) passed through as `free_only=free` (`backend/app/api/chat.py:73`), so `?free=false` lists paid ids even when settings say free-only.
- Suggestion: Treat settings as a floor: `want_free = settings.llm_free_only or bool(free_only)`. If `llm_free_only` is true, ignore client `freeOnly: false` and do not list paid models. Keep the query param as a further restriction only when the server allows paid.
- Status: open

### Issue 2 -- Severity: bug
- File: backend/app/services/llm/tools.py:342
- Description: `remove_holding` parses `qty` and subtracts with no sign check. `remaining = record.qty - reduce_by`; if `remaining > 0` it upserts. A model (or user) passing `qty: "-1"` therefore *increases* the position via the sell tool. `qty: "0"` is a no-op "reduced". `qty` greater than the position falls through to `delete_holding` (`tools.py:361`) and silently closes the whole lot.
- Suggestion: Reject `reduce_by <= 0` with `ToolError`. For `reduce_by > record.qty`, either error or document the close-all behavior and return `action: "deleted"` with an explicit `requestedQty` so the model cannot treat an oversell as a partial reduce.
- Status: open

### Issue 3 -- Severity: bug
- File: backend/app/services/llm/tools.py:278
- Description: Weighted-average upsert mixes `existing.qty * existing.avg_cost` with the new lot and then overwrites `currency` (`tools.py:228` default USD/VND, passed into `update_holding` at `tools.py:285`) with no FX conversion and no mismatch check. One share at `100000 VND` plus one share at `4 USD` becomes two shares at avg `50002` labeled USD. Cost basis and later PnL are wrong, and the old currency is dropped.
- Suggestion: If `existing.currency != currency`, refuse the increase (ask the model to use the position currency) or convert the new lot through `FxService` before `weighted_avg_cost`. Do not change currency on an in-place avg-cost update unless qty is being replaced, not added.
- Status: open

### Issue 4 -- Severity: bug
- File: frontend-temp/src/main.js:1005
- Description: The Chat tab aborts `fetch` at 120s. One `complete()` is allowed 90s (`LLM_TIMEOUT_SECONDS`), `analyze_asset` / `analyze_portfolio` nest a second `AnalystAgent.complete()` (`backend/app/services/llm/analyst.py:40`) inside the orchestrator loop (`backend/app/services/llm/orchestrator.py:62`), then the orchestrator calls `complete()` again. Worst case is multiple 90s calls plus 429 sleeps (`llm_retry_max_sleep` default 8s, up to `retry_max+1` per model, then fallbacks). The route is a sync FastAPI handler, so client abort does **not** cancel tool execution. `add_holding` is not idempotent: user sees "Request timed out.", retries, and can double the position.
- Suggestion: Raise the UI timeout to cover `max_rounds * timeout + analyst timeout + retry sleeps`, or use a single server-side deadline. Make add/increase idempotent for retries (client request id, or treat identical notional within a short window as no-op). Optionally check `request.is_disconnected` between tool rounds.
- Status: open

### Issue 5 -- Severity: suggestion
- File: backend/app/adapters/llm/openai_compat.py:178
- Description: HTTP 401 *and* 403 become `LlmAuthError`; `FallbackProvider` re-raises without trying the next model (`backend/app/adapters/llm/fallback.py:94`). That is correct for a bad API key (and it does not loop). It is too broad for OpenRouter, where 403 is also used for a single model being unavailable / origin / moderation, and 402 (payment) is a `LlmProviderError` that *does* walk the whole fallback list even when the account is out of credits. 429 mapping and bounded retry (`fallback.py:96-103`, tested in `backend/tests/unit/services/test_llm_fallback.py`) are correct: retry same model, then next candidate, finite list.
- Suggestion: Treat only 401 (and maybe 402) as fatal. Let 403 with a model-specific message fall through to the next candidate. Do not walk fallbacks on 402. Optionally parse string `"429"` as well as int `429` in the HTTP 200 error body (`openai_compat.py:247`).
- Status: open

### Issue 6 -- Severity: suggestion
- File: backend/app/adapters/llm/openai_compat.py:121
- Description: `_is_free_model` uses `float(pricing.get("prompt") or "1")`. Numeric `0` / `0.0` is falsy, so `or "1"` marks a zero-priced model as paid. Catalog tests use string `"0"`, which is truthy, so unit tests do not catch this. False negatives: unsuffixed free models when the catalog uses numbers. False positives: `_looks_free` (`backend/app/services/llm/chat_service.py:162`) allows any id ending in `:free` or starting with `openrouter/free` without consulting pricing. Combined with Issue 1, a client can also skip the check entirely.
- Suggestion: Use explicit `None` checks (`raw is None or raw === ""`) before `float()`. Keep `:free` / `openrouter/free` as allow-list aliases. When `llm_free_only` is on, require catalog `free=True` *or* the suffix, and never trust the client flag (Issue 1).
- Status: open

### Issue 7 -- Severity: suggestion
- File: backend/app/adapters/llm/factory.py:76
- Description: Swapping `LLM_PROVIDER` + `LLM_BASE_URL` + key does build `OpenRouterProvider` vs `OpenAiCompatProvider` correctly (`factory.py:46-73`). It is not a three-variable swap in practice: default `LLM_DEFAULT_MODEL` / `LLM_FALLBACK_MODELS` are OpenRouter ids, and default `LLM_FREE_ONLY=true` plus `_looks_free` will 400 xAI/OpenAI ids such as `grok-3` (no `:free` suffix, no OpenRouter pricing). Unknown `LLM_PROVIDER` values still default the URL to OpenRouter (`factory.py:43`).
- Suggestion: Document the full set: provider, base URL, key, default model, fallback list, and `LLM_FREE_ONLY`. When provider is `xai` or `openai`, default `llm_free_only` to false (or map a per-provider free allow-list). Fail fast at startup if `llm_free_only` is true and the default model does not look free.
- Status: open

### Issue 8 -- Severity: suggestion
- File: backend/app/services/llm/chat_service.py:77
- Description: Several `except Exception` paths hide real failures. `list_models` swallows provider errors and returns the static OpenRouter-shaped catalog, so `GET /api/chat/models` can look healthy with a bad key. `_is_allowed_free_model` swallows catalog errors and returns `False` (`chat_service.py:157`). `analyze_asset` / `analyze_portfolio` catch analyst failures, set `analysis=None`, stash `analystError` on the payload, and still return `ok: True` (`backend/app/services/llm/tools.py:475`, `tools.py:501`), so the orchestrator may invent a narrative. Quote lookup failures in `add_holding` become `quote=None` (`tools.py:235`); that is OK when price was supplied, but it also masks market-client bugs. `resolve_asset` catalog fallback swallows `list_assets` errors (`tools.py:74`). `registry.execute` converting every handler exception to `{"ok": false}` (`backend/app/services/llm/registry.py:105`) is appropriate for the tool loop, but it will also swallow programmer errors.
- Suggestion: Let `list_models` surface `LlmAuthError` / `LlmProviderError` as 503/502. Return `ok: false` from analyze_* when the specialist call fails (data can still be attached). Log swallowed market/news errors. Keep the registry catch for `ToolError`/`QtyError`/`ValidationError` only, or log the traceback for unexpected exceptions.
- Status: open

### Issue 9 -- Severity: suggestion
- File: backend/app/services/llm/tools.py:216
- Description: `search_assets` returns immediately on the first `market.search` exception, so a CoinGecko outage prevents a VN-stock search in the same call. `resolve_asset` continues to the next type, so behavior is inconsistent.
- Suggestion: Match `resolve_asset`: record `last_error`, continue the other asset type, and only fail if both miss.
- Status: open

### Issue 10 -- Severity: suggestion
- File: backend/app/api/chat.py:27
- Description: `ChatRequest.history` has no max length. The orchestrator later keeps 16 messages of 4000 chars (`backend/app/services/llm/orchestrator.py:144`), but FastAPI still parses the full body. A large history is an easy request-size DoS on the chat worker (which also `time.sleep`s on 429 in-process, `backend/app/adapters/llm/fallback.py:103`).
- Suggestion: `Field(max_length=32)` on `history` and `max_length=4000` on each content. Cap `llm_retry_max`. Move 429 waits off the ASGI worker if chat is deployed on a small EB instance.
- Status: open

### Issue 11 -- Severity: suggestion
- File: backend/app/core/deps.py:710
- Description: `get_llm_provider` treats `_llm_provider is None` as "not yet built". `set_llm_provider(None)` therefore cannot mean "disabled": the next request rebuilds from env. Unit test `test_chat_unconfigured_is_503` is correct only when no `OPENROUTER_API_KEY`/`LLM_API_KEY` is exported; a developer key in the process environment can turn that test into a live call. Live tests rely on this rebuild, so the overload is easy to miss.
- Suggestion: Use a sentinel (or a dedicated `_llm_provider_initialized` flag) so `None` means unconfigured after an explicit set. In unit tests, monkeypatch `build_llm_provider` to return `None` when asserting 503.
- Status: open

### Issue 12 -- Severity: nit
- File: backend/app/services/llm/registry.py:37
- Description: The caller's Bearer token is parsed again in `post_chat` (`backend/app/api/chat.py:100`) and stored on `ToolContext.user_token` "for future HTTP-style tools". Nothing reads it, and it is not serialized today — but it sits on the same object as handlers and is one accidental `json.dumps(ctx)` / debug log away from the model. Tool JSON *does* send `userId` (`backend/app/services/llm/tools.py:123`, `tools.py:493`) to the third-party LLM; that is the signed-in user only, not another tenant.
- Suggestion: Drop `user_token` from `ToolContext` until a tool needs to call the app over HTTP (prefer passing `user_id` into services, which is already the case). Strip `userId` from tool payloads sent to the provider if the model does not need it.
- Status: open

### Issue 13 -- Severity: nit
- File: backend/app/services/llm/qty.py:63
- Description: If the model sends both `qty` and `amount`, `qty` wins and `amount` is ignored. A confused call `qty=10, amount=10, price=50000` adds 10 BTC instead of 0.0002. The schema allows both fields (`backend/app/services/llm/tools.py:610-616`). Comma-as-decimal (`0,0002` → `replace(",", "")` → `00002` → 2) is also unhandled; the specified `10` / `50000` US-format path is fine.
- Suggestion: If both `qty` and `amount` are present and disagree, return `ToolError` asking for one. Do not strip commas unless the remainder is still a valid decimal.
- Status: open

### Issue 14 -- Severity: nit
- File: frontend-temp/src/main.js:919
- Description: Chat history is in-memory only and is not cleared when the Bearer token changes. Switching `fake:alice` → `fake:bob` without Clear resends Alice's assistant text (including holding numbers) as `history` under Bob's auth. Tools still run as Bob (`ctx.user.user_id`); this is conversation leakage in the temp UI, not a server IDOR. Token and history encoding on send are otherwise correct: `Authorization: Bearer`, last 16 user/assistant messages, current user text only in `message` (`main.js:989-1009`).
- Suggestion: Clear `chatHistory` in `saveAuth` / token change. Harmless for a single-user demo.
- Status: open
