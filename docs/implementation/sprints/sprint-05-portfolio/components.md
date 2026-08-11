# Sprint 05 — Components

## PortfolioService
1. load holdings for user
2. resolve prices via PriceCache / MarketService
3. domain compute native
4. optional apply_fx from stored rates
5. return JSON DTO

## API
- GET /api/portfolio
- POST /api/portfolio/refresh  # force market fetch for user symbols only
