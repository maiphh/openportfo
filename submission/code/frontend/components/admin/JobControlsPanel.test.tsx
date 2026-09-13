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
  runAdminNewsJob: vi.fn(),
}));

vi.mock("@/lib/admin-api", () => ({
  fetchAdminSettings: mocks.fetchAdminSettings,
  updateAdminSettings: mocks.updateAdminSettings,
  runAdminNewsJob: mocks.runAdminNewsJob,
}));

const translate = (key: string) =>
  ({
    "admin.jobs.title": "Job controls",
    "admin.jobs.subtitle": "Enable jobs",
    "admin.jobs.news": "News ingest",
    "admin.jobs.email": "Daily portfolio email",
    "admin.jobs.fetchNow": "Fetch news now",
    "admin.jobs.fetching": "Fetching news…",
    "admin.jobs.fetchDone": "News run {status} (written={written}). Duplicates upserted.",
    "admin.jobs.fetchError": "Could not fetch news.",
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
    mocks.runAdminNewsJob.mockReset();
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

  it("runs news fetch and notifies parent", async () => {
    const onNewsFetched = vi.fn();
    mocks.runAdminNewsJob.mockResolvedValue({
      runId: "r1",
      jobType: "news",
      status: "success",
      startedAt: null,
      finishedAt: null,
      message: null,
      counts: { written: 3 },
    });
    mocks.fetchAdminSettings.mockResolvedValue({ ...settings, jobs: { ...settings.jobs } });

    render(<JobControlsPanel token="admin-token" onNewsFetched={onNewsFetched} />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Fetch news now" })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Fetch news now" }));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        "News run success (written=3). Duplicates upserted.",
      ),
    );
    expect(mocks.runAdminNewsJob).toHaveBeenCalledWith("admin-token");
    expect(onNewsFetched).toHaveBeenCalledWith(
      expect.objectContaining({ status: "success", counts: { written: 3 } }),
    );
  });

  it("toggles daily portfolio email with jobs.email and emailEnabled", async () => {
    mocks.updateAdminSettings.mockResolvedValue({
      ...settings,
      version: 2,
      emailEnabled: true,
      jobs: { ...settings.jobs, email: true },
    });
    render(<JobControlsPanel token="admin-token" />);
    await waitFor(() => expect(screen.getByLabelText("Daily portfolio email")).toBeInTheDocument());
    expect(screen.getByLabelText("Daily portfolio email")).not.toBeChecked();
    fireEvent.click(screen.getByLabelText("Daily portfolio email"));
    await waitFor(() =>
      expect(mocks.updateAdminSettings).toHaveBeenCalledWith("admin-token", 1, {
        emailEnabled: true,
        jobs: { email: true },
      }),
    );
    await waitFor(() => expect(screen.getByLabelText("Daily portfolio email")).toBeChecked());
  });
});
