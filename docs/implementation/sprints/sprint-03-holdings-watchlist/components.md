# Sprint 03 — Components

## HoldingsRepo
list(user_id), get, create, update, delete  
Keys conceptually: userId + HOLD#assetType#symbol

## WatchlistRepo
list, add, remove  
Keys: userId + WATCH#assetType#symbol

## Validation
qty > 0, avg_cost >= 0, required fields → 400

## API (PRD)
GET/POST/PUT/DELETE /api/holdings  
GET/POST/DELETE /api/watchlist
