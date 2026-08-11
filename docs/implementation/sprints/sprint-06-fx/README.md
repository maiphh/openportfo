# Sprint 06 — FX on-demand (admin)

**Depends:** 02, 05  
**PRD:** M10b, FR-FX*, FR-AD6–9, D3  
Provider: https://www.exchangerate-api.com/docs/overview

## Owns
ExchangeRateClient, ExchangeRateRepo, FxService, GET /api/fx/rates, POST /api/admin/fx/refresh

## Exit
Fail keeps old rates; admin-only refresh; portfolio converts with store.
