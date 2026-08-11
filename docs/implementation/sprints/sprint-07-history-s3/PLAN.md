# Sprint 07 — Detailed Plan: History + ObjectStorage (S3 port)

| | |
|--|--|
| **ID** | S07 |
| **Depends on** | S04, S05 |
| **Parallel with** | S08, S09 |
| **PRD** | M7, FR-C1–C3 |

---

## 1. Objective

Historical price series via **cache-aside**: ObjectStorage port (S3 later) then market client. Chart-ready API.

---

## 2. Port ObjectStorage

```
get_json(key: str) -> dict | None
put_json(key: str, data: dict) -> None
```

**Key format (locked):**  
`history/{asset_type}/{asset_id}/{range}.json`

**Ranges:** `7d` | `30d` | `90d` | `1y`

---

## 3. API

`GET /api/assets/{asset_id}/history?range=30d&type=crypto|stock`

| Status | When |
|--------|------|
| 200 | `{ assetId, range, points: [{t, price}], source: "cache"|"live" }` |
| 400 | invalid range/type |
| 401 | no auth |

---

## 4. Service flow

```
key = build_key(type, asset_id, range)
if cached := storage.get_json(key):
    return cached + source=cache
series = market.get_history(...)
payload = normalize(series)
storage.put_json(key, payload)
return payload + source=live
```

---

## 5. TDD sequence

1. Miss → market called + put  
2. Hit → market not called  
3. Invalid range 400  
4. Unauthorized 401  

Fake: `InMemoryObjectStorage`

---

## 6. S3 adapter notes

- boto3 **only** in `adapters/s3/`  
- Bucket: `settings.data_bucket`  
- Real bucket wiring: S12  

---

## 7. Multiagent caution

If S08/S09 also edit `deps.py`, orchestrator serializes merges. Prefer minimal deps touch: register `get_object_storage` only.

---

## 8. Agent prompt

```
Sprint 07 ONLY. ObjectStorage port + history API cache-aside.
Parallel-safe: do not edit FX/admin/news feature modules.
TDD hit/miss. Fill handoff key layout.
```

---

## 9. Exit criteria

- [ ] History tests green  
- [ ] handoff key layout + range enum  
