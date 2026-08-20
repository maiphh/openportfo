import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SafeMarkdown from "@/components/chat/SafeMarkdown";

describe("SafeMarkdown", () => {
  it("renders common GFM as React nodes and never injects raw HTML", () => {
    const { container } = render(
      <SafeMarkdown content={'# Hello\n\n**bold** and `code`\n\n<script>alert("x")</script>\n\n- [x] done'} />,
    );
    expect(screen.getByRole("heading", { name: "Hello" })).toBeInTheDocument();
    expect(screen.getByText("bold")).toBeInTheDocument();
    expect(screen.getByText("code")).toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();
    expect(container.textContent).toContain("<script>alert(\"x\")</script>");
  });

  it("rejects javascript links", () => {
    const { container } = render(<SafeMarkdown content="[bad](javascript:alert(1)) [good](https://example.com)" />);
    expect(container.querySelector('a[href^="javascript:"]')).toBeNull();
    expect(screen.getByRole("link", { name: "good" })).toHaveAttribute("href", "https://example.com");
  });

  it("normalizes protocol-relative links to safe external HTTPS links", () => {
    const { container } = render(<SafeMarkdown content="[external](//example.com/path)" />);
    expect(screen.getByRole("link", { name: "external" })).toHaveAttribute("href", "https://example.com/path");
    expect(container.querySelector('a[target="_blank"]')).toBeTruthy();
  });
});
