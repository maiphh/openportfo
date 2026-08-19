import AssetDetailView from "@/components/asset/AssetDetailView";
import { buildStaticAssetParams } from "@/lib/static-asset-params";

/** Required for `output: "export"` dynamic routes. */
export async function generateStaticParams() {
  return buildStaticAssetParams("crypto");
}

export default async function CryptoAssetPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AssetDetailView assetType="crypto" id={id} />;
}
