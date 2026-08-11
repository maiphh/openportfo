# Handoff — Sprint 07 — History S3

## Status
- [x] Done

## Ports / modules
- `app/ports/storage.py` — ObjectStorage
- `tests/fakes/storage.py` — InMemoryObjectStorage
- `app/services/history_service.py` — cache-aside
- `app/api/history.py` — GET history

## Key layout (locked)
`history/{asset_type}/{asset_id}/{range}.json`  
Ranges: `7d` | `30d` | `90d` | `1y`

## API
`GET /api/assets/{asset_id}/history?range=30d&type=crypto|stock`  
Response: `{ assetId, range, type, points:[{t,price}], source: cache|live }`

## Tests
141 suite green including history hit/miss/400/401
