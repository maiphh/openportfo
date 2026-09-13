import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiBase } from "@/lib/api";
import { AuthApiError } from "@/lib/auth";
import {
  createAdminRssSource,
  deleteAdminRssSource,
  fetchAdminJobRuns,
  fetchAdminRssSources,
  runAdminNewsJob,
  updateAdminRssSource,
  updateAdminSettings,
} from "@/lib/admin-api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("admin-api RSS and jobs helpers", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("lists, creates, updates, and deletes RSS sources", async () => {
    const source = {
      sourceId: "s1",
      name: "Feed",
      url: "https://example.com/rss",
      enabled: true,
    };
    vi.mocked(global.fetch)
      .mockResolvedValueOnce(jsonResponse([source]))
      .mockResolvedValueOnce(jsonResponse(source, 201))
      .mockResolvedValueOnce(jsonResponse({ ...source, enabled: false }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(fetchAdminRssSources("tok")).resolves.toEqual([source]);
    await expect(
      createAdminRssSource("tok", { name: "Feed", url: "https://example.com/rss" }),
    ).resolves.toEqual(source);
    await expect(updateAdminRssSource("tok", "s1", { enabled: false })).resolves.toEqual({
      ...source,
      enabled: false,
    });
    await expect(deleteAdminRssSource("tok", "s1")).resolves.toBeUndefined();

    expect(vi.mocked(global.fetch).mock.calls[0]?.[0]).toBe(`${apiBase()}/api/admin/rss-sources`);
    expect(vi.mocked(global.fetch).mock.calls[3]?.[0]).toBe(
      `${apiBase()}/api/admin/rss-sources/s1`,
    );
  });

  it("maps validation and forbidden RSS failures", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      jsonResponse({ detail: "URL host is not allowed" }, 400),
    );
    await expect(
      createAdminRssSource("tok", { name: "x", url: "https://127.0.0.1/x" }),
    ).rejects.toBeInstanceOf(AuthApiError);

    vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse({ detail: "forbidden" }, 403));
    await expect(fetchAdminRssSources("tok")).rejects.toMatchObject({ status: 403 });
  });

  it("lists job runs and surfaces settings conflict code", async () => {
    vi.mocked(global.fetch)
      .mockResolvedValueOnce(
        jsonResponse([
          {
            runId: "r1",
            jobType: "news",
            status: "success",
            startedAt: null,
            finishedAt: null,
            message: null,
            counts: {},
          },
        ]),
      )
      .mockResolvedValueOnce(jsonResponse({ detail: { code: "settings_conflict" } }, 409));

    await expect(fetchAdminJobRuns("tok", { jobType: "news" })).resolves.toHaveLength(1);
    expect(vi.mocked(global.fetch).mock.calls[0]?.[0]).toContain("jobType=news");
    await expect(updateAdminSettings("tok", 1, { jobs: { news: true } })).rejects.toMatchObject({
      message: "settings_conflict",
      status: 409,
    });
  });

  it("posts news job run", async () => {
    const run = {
      runId: "r2",
      jobType: "news",
      status: "success",
      startedAt: null,
      finishedAt: null,
      message: null,
      counts: { written: 1 },
    };
    vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse(run));
    await expect(runAdminNewsJob("tok")).resolves.toEqual(run);
    expect(vi.mocked(global.fetch).mock.calls[0]?.[0]).toBe(`${apiBase()}/api/admin/jobs/news/run`);
    expect(vi.mocked(global.fetch).mock.calls[0]?.[1]).toMatchObject({ method: "POST" });
  });
});
