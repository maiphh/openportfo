import AssetDetailView from "@/components/asset/AssetDetailView";
import { staticAssetParams } from "@/lib/static-asset-params";

/** Seeded compatibility paths; canonical links use `/asset?type=crypto&id=...`. */
export function generateStaticParams() {
  return staticAssetParams("crypto");
}

export default async function CryptoAssetPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AssetDetailView assetType="crypto" id={id} />;
}
