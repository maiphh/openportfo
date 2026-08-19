import path from "node:path";
import type { NextConfig } from "next";

// `output: "export"` forces dynamicParams=false, so /stock/[id] only works for
// IDs returned by generateStaticParams. That breaks `next dev` for tickers not
// in the seed list when the markets API is slow. Keep export for production
// builds only (S3/CloudFront); allow any id in development.
const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  ...(isProd ? { output: "export" as const } : {}),
  images: { unoptimized: true },
  trailingSlash: true,
  devIndicators: false,
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
