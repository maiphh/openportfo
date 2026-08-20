# Artryx

Next.js frontend for the market dashboard, cloned from the [OpenStock](https://github.com/Open-Dev-Society/OpenStock) Dashboard tab and rebranded as **Artryx**.

This first slice is **Dashboard only**, backed by **mock data** (no TradingView, Finnhub, or backend).

## Run

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

- Dashboard `/` — Market Overview, Stock Heatmap, Market Quotes, Top Stories
- Markets `/markets` — stub
- Search — mock symbol palette from the header

Static export (`output: "export"`) is enabled on **`next build` only** (for S3 + CloudFront).
`next dev` omits it so `/stock/[id]` and `/crypto/[id]` work for any ticker without pre-listing.

```powershell
npm run build
```

Output is written to `out/`. Asset detail links use the universal static
`/asset?type=...&id=...` route, which resolves arbitrary ids in the browser.
The legacy `/stock/[id]` and `/crypto/[id]` paths remain available for seeded
compatibility links and no longer require a live markets API during the build.

## Auth (Cognito Hosted UI)

Public env in `frontend/.env.local` (no client secret — SPA public client):

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_COGNITO_DOMAIN=your-prefix.auth.us-east-1.amazoncognito.com
NEXT_PUBLIC_COGNITO_CLIENT_ID=xxxxxxxx
NEXT_PUBLIC_COGNITO_REGION=us-east-1
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

Register these exact Hosted UI URLs (trailing slash required for static export):

- Callback: `http://localhost:3000/auth/callback/`
- Sign-out: `http://localhost:3000/`

The app stores the **ID token** in `artryx.accessToken` and sends `Authorization: Bearer <id_token>` to FastAPI. PKCE `code_verifier` stays in `sessionStorage` only.

If the Cognito public env vars are omitted, `/portfolio` keeps the local token-paste fallback (`fake:alice`).
