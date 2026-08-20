import path from "node:path";
import type { NextConfig } from "next";

// `output: "export"` forces dynamicParams=false for the legacy dynamic detail
// routes. Internal links use the static `/asset?type=...&id=...` entry point,
// so arbitrary search/portfolio ids do not depend on generateStaticParams.
// Keep export for production builds only (S3/CloudFront); allow any id in
// development as well.
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
