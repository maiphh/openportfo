import AssetDetailView from "@/components/asset/AssetDetailView";

export default async function CryptoAssetPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AssetDetailView assetType="crypto" id={id} />;
}
