import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import TopStories from "@/components/dashboard/TopStories";
import { NewsApiError } from "@/lib/news";

const fetchNews = vi.fn();

vi.mock("next/link", () => ({
  default({
    href,
    children,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
    return (
      <a href={href} {...props}>
        {children}
      </a>
    );
  },
}));

vi.mock("@/lib/news", async () => {
  const actual = await vi.importActual<typeof import("@/lib/news")>("@/lib/news");
  return {
    ...actual,
    fetchNews: (...args: unknown[]) => fetchNews(...args),
  };
});

const liveItems = [
  {
    id: "1",
    title: "Vinamilk expands distribution",
    url: "https://cafef.vn/vnm",
    source: "CafeF",
    publishedAt: "2026-08-19T10:00:00Z",
    symbols: ["VNM", "UNKNOWN"],
  },
  {
    id: "2",
    title: "Bitcoin rallies",
    url: "https://coindesk.com/btc",
    source: "CoinDesk",
    publishedAt: "2026-08-19T11:00:00Z",
    symbols: ["BTC"],
  },
  {
    id: "3",
    title: "Headline without a URL",
    url: "",
    source: "Reuters",
    publishedAt: "2026-08-18T00:00:00Z",
    symbols: [],
  },
];

function expectNoMockHeadlines() {
  expect(screen.queryByText(/UNTREE/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Robot Maker/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Legal Nightmare/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/SpaceX Stock Jumps/i)).not.toBeInTheDocument();
}

describe("TopStories", () => {
  beforeEach(() => {
    fetchNews.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("shows a skeleton while loading and never seeds mock headlines", async () => {
    let resolveFetch: (value: unknown) => void = () => {};
    fetchNews.mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve;
      }),
    );

    render(<TopStories />);

    expect(screen.getByTestId("top-stories-skeleton")).toBeInTheDocument();
    expectNoMockHeadlines();
    expect(fetchNews).toHaveBeenCalledWith(
      expect.objectContaining({ limit: 20, signal: expect.any(AbortSignal) }),
    );

    resolveFetch(liveItems);
    await waitFor(() => {
      expect(screen.getByText("Vinamilk expands distribution")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("top-stories-skeleton")).not.toBeInTheDocument();
  });

  it("401 empty path shows sign-in state and never mock headlines", async () => {
    fetchNews.mockRejectedValue(new NewsApiError(401, "Missing authorization header"));

    render(<TopStories />);

    await waitFor(() => {
      expect(screen.getByTestId("top-stories-auth")).toBeInTheDocument();
    });
    expect(screen.getByText("Sign in to see news")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("top-stories-list")).not.toBeInTheDocument();
    expectNoMockHeadlines();
  });

  it("shows No stories yet on an empty authenticated list", async () => {
    fetchNews.mockResolvedValue([]);

    render(<TopStories />);

    await waitFor(() => {
      expect(screen.getByTestId("top-stories-empty")).toBeInTheDocument();
    });
    expect(screen.getByText("No stories yet")).toBeInTheDocument();
    expectNoMockHeadlines();
  });

  it("shows error + Retry and recovers", async () => {
    fetchNews
      .mockRejectedValueOnce(new NewsApiError(503, "News HTTP 503"))
      .mockResolvedValueOnce(liveItems);

    render(<TopStories />);

    await waitFor(() => {
      expect(screen.getByTestId("top-stories-error")).toBeInTheDocument();
    });
    expect(screen.getByText(/News HTTP 503/i)).toBeInTheDocument();
    expectNoMockHeadlines();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => {
      expect(screen.getByText("Bitcoin rallies")).toBeInTheDocument();
    });
    expect(fetchNews).toHaveBeenCalledTimes(2);
  });

  it("links inferable symbols and opens headlines in a new tab", async () => {
    fetchNews.mockResolvedValue(liveItems);

    render(<TopStories />);

    await waitFor(() => {
      expect(screen.getByTestId("top-stories-list")).toBeInTheDocument();
    });

    const vnm = screen.getByRole("link", { name: "VNM" });
    expect(vnm).toHaveAttribute("href", "/asset?type=stock&id=VNM");

    const btc = screen.getByRole("link", { name: "BTC" });
    expect(btc).toHaveAttribute("href", "/asset?type=crypto&id=btc");

    expect(screen.queryByRole("link", { name: "UNKNOWN" })).not.toBeInTheDocument();

    const headline = screen.getByRole("link", { name: "Vinamilk expands distribution" });
    expect(headline).toHaveAttribute("href", "https://cafef.vn/vnm");
    expect(headline).toHaveAttribute("target", "_blank");
    expect(headline).toHaveAttribute("rel", "noopener noreferrer");

    const plain = screen.getByText("Headline without a URL");
    expect(plain.tagName).toBe("P");
    expect(plain.closest("a")).toBeNull();
  });
});
