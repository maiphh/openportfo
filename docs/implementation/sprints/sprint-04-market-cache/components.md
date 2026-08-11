# Sprint 04 — Components

## CryptoMarketClient
search(q), get_prices(ids/symbols), get_history(id, range)

## StockMarketClient
search(q), get_prices(symbols), get_history(symbol, range)

## PriceCacheRepo
get(asset_type, symbol), put(...), respect ttl_minutes from settings

## MarketService
search by type; get_quotes cache-first; batch where possible

## API
GET /api/assets/search?q=&type=crypto|stock

Browser must never call CoinGecko/vnstock.
