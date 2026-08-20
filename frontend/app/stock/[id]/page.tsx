import AssetDetailView from "@/components/asset/AssetDetailView";
import { staticAssetParams } from "@/lib/static-asset-params";

/** Seeded compatibility paths; canonical links use `/asset?type=stock&id=...`. */
export function generateStaticParams() {
  return staticAssetParams("stock");
}

export default async function StockAssetPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AssetDetailView assetType="stock" id={id} />;
}
