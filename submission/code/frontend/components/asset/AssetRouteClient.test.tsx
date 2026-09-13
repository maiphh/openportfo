import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AssetRouteClient from "@/components/asset/AssetRouteClient";

const useSearchParams = vi.fn();

vi.mock("next/navigation", () => ({
  useSearchParams: () => useSearchParams(),
}));

vi.mock("@/components/asset/AssetDetailView", () => ({
  default: ({ assetType, id }: { assetType: string; id: string }) => (
    <div data-testid="asset-detail-route">
      {assetType}:{id}
    </div>
  ),
}));

afterEach(() => cleanup());

describe("AssetRouteClient", () => {
  beforeEach(() => {
    useSearchParams.mockReset();
  });

  it("renders arbitrary non-seed ids from the static query route", () => {
    useSearchParams.mockReturnValue(new URLSearchParams("type=crypto&id=brand-new-token-999"));

    render(<AssetRouteClient />);

    expect(screen.getByTestId("asset-detail-route")).toHaveTextContent("crypto:brand-new-token-999");
  });

  it("does not render the detail API for invalid route parameters", () => {
    useSearchParams.mockReturnValue(new URLSearchParams("type=unknown&id=VNM"));

    render(<AssetRouteClient />);

    expect(screen.getByText("Invalid asset link")).toBeInTheDocument();
    expect(screen.queryByTestId("asset-detail-route")).not.toBeInTheDocument();
  });
});
