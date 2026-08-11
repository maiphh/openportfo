# Sprint 06 — Components

## ExchangeRateClient
fetch rates (USD base including VND, or pair USD/VND)

## ExchangeRateRepo
get_latest(); save_success(snapshot); NEVER delete on failure

## FxService.refresh(admin)
try client; on success save; on failure return error + previous unchanged

## API
GET /api/fx/rates — no external call  
POST /api/admin/fx/refresh — admin only

## Env
EXCHANGE_RATE_API_KEY server-only
