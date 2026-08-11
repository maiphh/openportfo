# Sprint 07 — Components

## ObjectStorage
get_json(key), put_json(key, data)

## HistoryService
key pattern history/{assetType}/{id}/{range}.json  
cache-aside: storage else market client then put

## API
GET /api/assets/{id}/history?range=7d|30d|90d|1y&type=crypto|stock
