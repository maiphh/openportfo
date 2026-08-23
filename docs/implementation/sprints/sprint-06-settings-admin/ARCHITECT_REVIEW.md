# Sprint 06 - Solution Architect acceptance review

**Scope:** BL-023, BL-024, BL-025, BL-026  
**Review date:** 2026-08-23  
**Review cycle:** final remediation review 3  
**Overall verdict:** **APPROVED**  
**Required findings:** none open

The Sprint 06 implementation satisfies the authoritative handoff. R1-R8, including the later R4-S2 fresh-singleton defect and R4-S3 provider-omission coverage gap, are closed. BL-023 through BL-026 are architecture-accepted and are authorized to move from `in_progress` to `done` through the normal backlog close-out workflow. This review does not itself change backlog status, commit, or merge.

## Final R4 closure

### R4-S2 - CLOSED - DynamoDB version-zero optimistic creation

`backend/app/adapters/dynamodb/settings.py` now branches its atomic `PutItem` condition by expected version.

For `expected_version == 0`:

```text
attribute_not_exists(#pk) OR attribute_not_exists(#version) OR #version = :expected
```

This correctly accepts only:

- a fresh table with no `SETTINGS/GLOBAL` item;
- a legacy singleton with no `version` attribute; or
- an existing singleton at explicit version 0.

Because the condition is evaluated against the pre-write item, after one creator writes version 1 a concurrent stale version-zero creator no longer satisfies any branch and receives the typed settings conflict.

For `expected_version > 0`:

```text
attribute_exists(#pk) AND attribute_exists(#sk) AND #version = :expected
```

This requires the exact singleton and version. An item deleted between the strong read and conditional put cannot be recreated at an advanced version. A matching existing version increments normally; an absent key, malformed key state, or changed version conflicts.

Only `ConditionalCheckFailedException` is translated to `SettingsConflictError`. AccessDenied and unrelated AWS failures propagate.

**Test evidence**

`backend/tests/unit/adapters/test_settings_repo.py` now covers:

1. fresh version-zero creation to version 1;
2. two stale version-zero creators with exactly one winner;
3. legacy missing-version acceptance;
4. explicit version-zero acceptance;
5. a concurrent newer-version loser conflict;
6. delete-after-positive-read conflict without recreation; and
7. AccessDenied propagation.

The fresh-create test exercises the actual boto3 Table resource with botocore `Stubber`, validates the low-level AttributeValue request against the `PutItem` service model, and asserts the exact document-form resource request. Stateful tests evaluate race/delete semantics instead of raising predetermined outcomes. I also independently exercised the positive-version branch with an existing version 3 (successful version 4 save) and with a missing sort key (conflict).

### R4-S3 - CLOSED - Null runtime parameters are omitted

`backend/tests/unit/adapters/test_llm_openai_compat.py::test_complete_omits_null_runtime_parameters` captures the real `httpx.MockTransport` JSON request and asserts `max_tokens`, `temperature`, and `top_p` are absent when their values are null. The adjacent positive test asserts exact forwarding when values are provided.

## Prior finding disposition

| Finding | Status | Acceptance evidence |
|---|---|---|
| R1 | **CLOSED** | Low-level Dynamo role transaction uses valid AttributeValue serialization, bounded cancellation re-read/retry, strong post-read, and unrelated AWS error propagation. |
| R2 | **CLOSED** | Strong profile reads, conditional first-auth creation/race-loser reload, field-only existing-user mutations, and absent-target conditions prevent clobber/phantom users. |
| R3 | **CLOSED** | EB-only `TransactWriteItems` is separated and scoped to Users plus Settings; Lambda and broad table statements do not receive it. |
| R4 | **CLOSED** | Complete current+patch+env validation, finite bounds, narrow settings errors, fresh/legacy optimistic creation, per-request snapshots, provider forwarding and null omission are covered. |
| R5 | **CLOSED** | Avatar default sends explicit nulls; Revert remains distinct; blank admin keywords normalize to `[]`; focus return is implemented. |
| R6 | **CLOSED** | FX status, retained-data 502 behavior, transport catch/finally, auth reload rules, and obsolete panel removal are complete. |
| R7 | **CLOSED** | Chatbot renders and validates all six raw/default/effective fields, preserves null/empty semantics, handles conflict, and suppresses duplicate saves. |
| R8 | **CLOSED** | Shared 400 field-error shape, required profile controller, ARIA associations, synchronous protected-tab clamp, and real-child zero-fetch boundary are complete. |

## Acceptance verdict by backlog item

| Backlog | Verdict | Accepted scope |
|---|---|---|
| BL-023 | **APPROVED** | Static Settings route, shared profile fetch/replace/reload, General and Avatar behavior, explicit patch/null schema, both adapters, signed-out and accessible tab states. |
| BL-024 | **APPROVED** | Verified-claim grant-only whitelist, opaque pagination, admin user/settings APIs and editor, self/last-admin concurrency guard, strong conditional Dynamo paths, and least-privilege IAM. |
| BL-025 | **APPROVED** | Versioned raw/default/effective settings, fresh/legacy optimistic singleton writes, full candidate validation, per-request runtime snapshot, suffix/model/fallback and LLM parameter behavior, complete admin UI. |
| BL-026 | **APPROVED** | Shared FX tab, user/admin roles, status/error/loading behavior, retained 502 data, refresh ownership, and old panel removal parity. |

**Authorization:** BL-023, BL-024, BL-025, and BL-026 may now be moved to `done`. No architecture remediation remains.

## Verification accepted

- Final backend suite reported: **512 passed, 4 skipped, 5 known warnings**.
- Independent focused R4 run: **27 passed**.
- Frontend suite: **52 files, 346 tests**; TypeScript and production static build passed.
- `/settings` and `/admin` remain statically emitted with their Suspense shells.
- `git diff --check` is clean apart from line-ending notices; lockfiles are unchanged; `backend/AGENTS.md` is absent; no bootstrap/legacy migration or removed `FxRatesPanel` reference was reintroduced.

## Non-blocking manual release smokes

Only deployment/browser follow-up remains:

- static-host `/settings?tab=...` deep links, query canonicalization, Back/Forward history, and Cognito return URLs;
- responsive mobile tabs/admin table, keyboard navigation, editor focus return, and signed-out/non-admin visual states;
- DiceBear network success, deterministic default, and image-failure fallback;
- real AWS first `SETTINGS/GLOBAL` creation, concurrent settings writes, promotion/demotion guard transaction, and deployed EB IAM/CloudTrail evidence;
- multi-worker next-request chat settings visibility with an in-flight request retaining its snapshot; and
- real FX refresh success, retained-data 502, and transport failure.

These smokes are non-blocking for code and backlog acceptance. They remain release/deployment checks rather than further Sprint 06 implementation findings.
