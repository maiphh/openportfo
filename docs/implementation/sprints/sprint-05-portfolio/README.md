# Sprint 05 — Portfolio + price refresh

**Depends:** 01, 03, 04  
**PRD:** M5, M6, FR-P* (FX read only)

## Owns
PortfolioService, GET/POST portfolio routes

## Critical
GET /portfolio and refresh must NOT call ExchangeRateClient (only ExchangeRateRepo.get if present).

## Exit
Portfolio + refresh tests green.
