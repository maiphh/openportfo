import { Suspense } from "react";
import AssetRouteClient from "@/components/asset/AssetRouteClient";

function AssetRouteFallback() {
  return <div className="py-16 text-center text-sm text-gray-500">Loading asset…</div>;
}

/**
 * Universal static-export-safe asset entry point. The query string is parsed
 * in the browser, so arbitrary searched/held assets do not need to be known
 * during `next build`.
 */
export default function AssetPage() {
  return (
    <Suspense fallback={<AssetRouteFallback />}>
      <AssetRouteClient />
    </Suspense>
  );
}
