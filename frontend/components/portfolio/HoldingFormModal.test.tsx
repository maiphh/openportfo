import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import HoldingFormModal, { holdingFormCanSubmit } from "@/components/portfolio/HoldingFormModal";
import { toPrefillHit } from "@/lib/asset";
import type { AssetSearchHit } from "@/lib/portfolio";

const prefill: AssetSearchHit = {
  symbol: "BTC",
  name: "Bitcoin",
  assetId: "bitcoin",
  assetType: "crypto",
};

afterEach(() => {
  cleanup();
});

describe("holdingFormCanSubmit / toPrefillHit", () => {
  it("requires selected asset plus positive qty and non-negative cost", () => {
    expect(holdingFormCanSubmit(null, "1", "10")).toBe(false);
    expect(holdingFormCanSubmit(prefill, "", "10")).toBe(false);
    expect(holdingFormCanSubmit(prefill, "1", "")).toBe(false);
    expect(holdingFormCanSubmit(prefill, "0", "10")).toBe(false);
    expect(holdingFormCanSubmit(prefill, "1", "-1")).toBe(false);
    expect(holdingFormCanSubmit(prefill, "1", "10")).toBe(true);
  });

  it("toPrefillHit keeps catalog identity fields", () => {
    expect(
      toPrefillHit({
        assetType: "crypto",
        symbol: "BTC",
        assetId: "bitcoin",
        name: "Bitcoin",
        nativeCurrency: "USD",
        displayCurrency: "VND",
        profile: {},
        quote: null,
      }),
    ).toEqual({
      symbol: "BTC",
      name: "Bitcoin",
      assetId: "bitcoin",
      assetType: "crypto",
      currency: "USD",
    });
  });
});

describe("HoldingFormModal prefill", () => {
  it("locks asset, leaves qty blank, and disables submit until qty+cost entered", () => {
    const onSubmit = vi.fn();
    render(
      <HoldingFormModal
        open
        mode="create"
        displayCurrency="USD"
        prefill={prefill}
        onClose={() => undefined}
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByText(/BTC\s*·/i)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/e\.g\. BTC/i)).not.toBeInTheDocument();

    const qty = screen.getByLabelText(/^Quantity$/i) as HTMLInputElement;
    const cost = screen.getByLabelText(/Avg cost \(USD\)/i) as HTMLInputElement;
    expect(qty.value).toBe("");
    expect(cost.value).toBe("");

    const submit = screen.getByRole("button", { name: /^Add holding$/i });
    expect(submit).toBeDisabled();
  });
});
