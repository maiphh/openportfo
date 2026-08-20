"use client";

import { useSearchParams } from "next/navigation";
import AssetDetailView from "@/components/asset/AssetDetailView";
import { parseAssetRouteParams } from "@/lib/asset";

/** Client-side query parsing for the static `/asset` export. */
export default function AssetRouteClient() {
  const searchParams = useSearchParams();
  const route = parseAssetRouteParams(searchParams);

  if (!route) {
    return (
      <div className="mx-auto max-w-lg rounded-xl border border-amber-500/30 bg-amber-500/5 px-6 py-10 text-center">
        <p className="text-sm uppercase tracking-wide text-amber-400">Invalid asset link</p>
        <h1 className="mt-2 text-xl font-semibold text-gray-100">Asset details unavailable</h1>
        <p className="mt-2 text-sm text-gray-400">
          This link needs a valid stock or crypto type and an asset id.
        </p>
      </div>
    );
  }

  return <AssetDetailView assetType={route.assetType} id={route.id} />;
}
