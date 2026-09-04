import path from "node:path";
import type { NextConfig } from "next";

// BL-031 single-EB hosting: always `output: "export"` so the EB bundle is
// deterministic (no NODE_ENV-conditional packaging). Asset detail uses the
// static `/asset?type=...&id=...` entry point so arbitrary search/portfolio
// ids do not need per-symbol HTML at build time.
// `next dev` ignores `output: "export"`, so local development is unaffected.
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  devIndicators: false,
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
