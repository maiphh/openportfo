import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  fetchAdminJobRuns: vi.fn(),
}));

vi.mock("@/lib/admin-api", () => ({
  fetchAdminJobRuns: mocks.fetchAdminJobRuns,
}));

const translate = (key: string) =>
  ({
    "admin.runs.title": "Recent job runs",
    "admin.runs.subtitle": "Latest outcomes",
    "admin.runs.empty": "No job runs recorded yet.",
    "admin.runs.loading": "Loading job runs…",
    "admin.runs.loadError": "Could not load job runs.",
    "admin.runs.status": "Status",
    "admin.runs.started": "Started",
    "admin.runs.message": "Message",
    "admin.runs.counts": "Counts",
    "admin.runs.refresh": "Refresh",
  })[key] ?? key;

vi.mock("@/components/LanguageProvider", () => ({
  useT: () => translate,
}));

import JobRunsPanel from "@/components/admin/JobRunsPanel";

describe("JobRunsPanel", () => {
  beforeEach(() => {
    mocks.fetchAdminJobRuns.mockReset();
  });

  afterEach(cleanup);

  it("shows empty state", async () => {
    mocks.fetchAdminJobRuns.mockResolvedValue([]);
    render(<JobRunsPanel token="admin-token" />);
    expect(screen.getByText("Loading job runs…")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("No job runs recorded yet.")).toBeInTheDocument());
  });

  it("shows load error with role=alert", async () => {
    mocks.fetchAdminJobRuns.mockRejectedValue(new Error("offline"));
    render(<JobRunsPanel token="admin-token" />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Could not load job runs."));
  });

  it("renders sanitized run message and counts", async () => {
    mocks.fetchAdminJobRuns.mockResolvedValue([
      {
        runId: "r1",
        jobType: "news",
        status: "partial",
        startedAt: "2026-08-28T00:00:00Z",
        finishedAt: "2026-08-28T00:01:00Z",
        message: "1 of 2 RSS sources failed",
        counts: { written: 1, fetched: 2, sources_succeeded: 1, sources_failed: 1 },
      },
    ]);
    render(<JobRunsPanel token="admin-token" />);
    await waitFor(() => expect(screen.getByText("partial")).toBeInTheDocument());
    expect(screen.getByText("1 of 2 RSS sources failed")).toBeInTheDocument();
    expect(screen.getByText(/written=1/)).toBeInTheDocument();
  });
});
