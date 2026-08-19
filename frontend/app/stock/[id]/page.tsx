import AssetDetailView from "@/components/asset/AssetDetailView";

export default async function StockAssetPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AssetDetailView assetType="stock" id={id} />;
}
