import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthApiError } from "@/lib/auth";

const settings = {
  version: 1,
  emailTime: "08:00",
  timezone: "UTC",
  emailEnabled: false,
  priceCacheTtlMinutes: 10,
  jobs: { news: false, snapshot: true, email: false, price: true },
  defaultDisplayCurrency: "USD",
  chat: {
    overrides: { model: null, fallbackModels: null, temperature: null, topP: null, maxTokens: null, systemPromptExtra: null },
    defaults: { model: null, fallbackModels: null, temperature: null, topP: null, maxTokens: null, systemPromptExtra: null },
    effective: { model: null, fallbackModels: null, temperature: null, topP: null, maxTokens: null, systemPromptExtra: null },
    availableModels: [],
  },
};

const mocks = vi.hoisted(() => ({
  fetchAdminSettings: vi.fn(),
  updateAdminSettings: vi.fn(),
}));

vi.mock("@/lib/admin-api", () => ({
  fetchAdminSettings: mocks.fetchAdminSettings,
  updateAdminSettings: mocks.updateAdminSettings,
}));

const translate = (key: string) =>
  ({
    "admin.jobs.title": "Job controls",
    "admin.jobs.subtitle": "Enable jobs",
    "admin.jobs.news": "News ingest",
    "admin.jobs.loading": "Loading job settings…",
    "admin.jobs.loadError": "Could not load job settings.",
    "admin.jobs.saveError": "Could not update job settings.",
    "admin.jobs.conflict": "Settings changed elsewhere. Reloaded the latest version.",
  })[key] ?? key;

vi.mock("@/components/LanguageProvider", () => ({
  useT: () => translate,
}));

import JobControlsPanel from "@/components/admin/JobControlsPanel";

describe("JobControlsPanel", () => {
  beforeEach(() => {
    mocks.fetchAdminSettings.mockReset().mockResolvedValue({ ...settings, jobs: { ...settings.jobs } });
    mocks.updateAdminSettings.mockReset();
  });

  afterEach(cleanup);

  it("toggles news job and reloads on settings conflict", async () => {
    mocks.updateAdminSettings
      .mockRejectedValueOnce(new AuthApiError(409, "settings_conflict"))
      .mockResolvedValueOnce({
        ...settings,
        version: 3,
        jobs: { ...settings.jobs, news: true },
      });
    mocks.fetchAdminSettings
      .mockResolvedValueOnce({ ...settings, jobs: { ...settings.jobs, news: false } })
      .mockResolvedValueOnce({
        ...settings,
        version: 2,
        jobs: { ...settings.jobs, news: true },
      });

    render(<JobControlsPanel token="admin-token" />);
    await waitFor(() => expect(screen.getByLabelText("News ingest")).toBeInTheDocument());
    expect(screen.getByLabelText("News ingest")).not.toBeChecked();

    fireEvent.click(screen.getByLabelText("News ingest"));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        "Settings changed elsewhere. Reloaded the latest version.",
      ),
    );
    expect(mocks.fetchAdminSettings).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(screen.getByLabelText("News ingest")).toBeChecked());
  });
});
