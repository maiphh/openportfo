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

Static export (`output: "export"`) is enabled for later S3 + CloudFront.

```powershell
npm run build
```

Output is written to `out/`.
