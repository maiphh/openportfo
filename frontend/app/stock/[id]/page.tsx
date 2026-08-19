import AssetDetailView from "@/components/asset/AssetDetailView";
import { buildStaticAssetParams } from "@/lib/static-asset-params";

/** Required for `output: "export"` dynamic routes. */
export async function generateStaticParams() {
  return buildStaticAssetParams("stock");
}

export default async function StockAssetPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AssetDetailView assetType="stock" id={id} />;
}
