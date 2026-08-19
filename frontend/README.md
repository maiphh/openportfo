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

Output is written to `out/`. Asset detail HTML is generated from `generateStaticParams()` (markets API + seed fallbacks).
