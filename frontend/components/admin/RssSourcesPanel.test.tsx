import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthApiError } from "@/lib/auth";

const mocks = vi.hoisted(() => ({
  fetchAdminRssSources: vi.fn(),
  createAdminRssSource: vi.fn(),
  updateAdminRssSource: vi.fn(),
  deleteAdminRssSource: vi.fn(),
}));

vi.mock("@/lib/admin-api", () => ({
  fetchAdminRssSources: mocks.fetchAdminRssSources,
  createAdminRssSource: mocks.createAdminRssSource,
  updateAdminRssSource: mocks.updateAdminRssSource,
  deleteAdminRssSource: mocks.deleteAdminRssSource,
}));

const translate = (key: string) =>
  ({
    "admin.rss.title": "RSS sources",
    "admin.rss.subtitle": "Configure feeds",
    "admin.rss.name": "Name",
    "admin.rss.url": "Feed URL",
    "admin.rss.enabled": "Enabled",
    "admin.rss.add": "Add source",
    "admin.rss.delete": "Delete",
    "admin.rss.empty": "No RSS sources yet.",
    "admin.rss.loading": "Loading RSS sources…",
    "admin.rss.loadError": "Could not load RSS sources.",
    "admin.rss.saveError": "Could not save RSS source.",
    "admin.rss.validationError": "Enter a name and a public http(s) feed URL.",
    "admin.rss.forbidden": "Administrator access is required for RSS sources.",
  })[key] ?? key;

vi.mock("@/components/LanguageProvider", () => ({
  useT: () => translate,
}));

import RssSourcesPanel from "@/components/admin/RssSourcesPanel";

describe("RssSourcesPanel", () => {
  beforeEach(() => {
    mocks.fetchAdminRssSources.mockReset().mockResolvedValue([]);
    mocks.createAdminRssSource.mockReset();
    mocks.updateAdminRssSource.mockReset();
    mocks.deleteAdminRssSource.mockReset();
  });

  afterEach(cleanup);

  it("creates, toggles, and deletes sources", async () => {
    mocks.createAdminRssSource.mockResolvedValue({
      sourceId: "s1",
      name: "CoinDesk",
      url: "https://example.com/feed.xml",
      enabled: true,
    });
    mocks.updateAdminRssSource.mockResolvedValue({
      sourceId: "s1",
      name: "CoinDesk",
      url: "https://example.com/feed.xml",
      enabled: false,
    });
    mocks.deleteAdminRssSource.mockResolvedValue(undefined);

    render(<RssSourcesPanel token="admin-token" />);
    await waitFor(() => expect(screen.getByText("No RSS sources yet.")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "CoinDesk" } });
    fireEvent.change(screen.getByLabelText("Feed URL"), {
      target: { value: "https://example.com/feed.xml" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add source" }));

    await waitFor(() => expect(screen.getByText("CoinDesk")).toBeInTheDocument());
    expect(mocks.createAdminRssSource).toHaveBeenCalledWith("admin-token", {
      name: "CoinDesk",
      url: "https://example.com/feed.xml",
      enabled: true,
    });

    fireEvent.click(screen.getByLabelText("Enabled CoinDesk"));
    await waitFor(() =>
      expect(mocks.updateAdminRssSource).toHaveBeenCalledWith("admin-token", "s1", {
        enabled: false,
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(mocks.deleteAdminRssSource).toHaveBeenCalledWith("admin-token", "s1"));
    await waitFor(() => expect(screen.getByText("No RSS sources yet.")).toBeInTheDocument());
  });

  it("maps validation and forbidden errors", async () => {
    render(<RssSourcesPanel token="admin-token" />);
    await waitFor(() => expect(screen.getByText("No RSS sources yet.")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Add source" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a name and a public http(s) feed URL.");

    mocks.createAdminRssSource.mockRejectedValueOnce(new AuthApiError(403, "forbidden"));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Bad" } });
    fireEvent.change(screen.getByLabelText("Feed URL"), {
      target: { value: "https://example.com/x" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add source" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Administrator access is required for RSS sources.",
      ),
    );
  });
});
