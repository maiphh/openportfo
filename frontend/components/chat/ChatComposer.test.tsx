import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ChatComposer from "@/components/chat/ChatComposer";

describe("ChatComposer", () => {
  afterEach(cleanup);

  it("keeps Enter inside an IME composition and submits after composition ends", () => {
    const onSubmit = vi.fn();
    render(<ChatComposer value="hello" onChange={vi.fn()} onSubmit={onSubmit} signedIn />);
    const input = screen.getByLabelText("Message the personal assistant");

    fireEvent.compositionStart(input);
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });
    expect(onSubmit).not.toHaveBeenCalled();

    fireEvent.compositionEnd(input);
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("keeps the composer controls touch-sized and grows from a compact base", () => {
    render(<ChatComposer value="hello" onChange={vi.fn()} onSubmit={vi.fn()} signedIn />);
    const input = screen.getByLabelText("Message the personal assistant");
    const send = screen.getByRole("button", { name: "Send message" });
    expect(input).toHaveStyle({ height: "44px" });
    expect(send).toHaveClass("size-11");
  });

  it("shows a bounded character counter near the request limit", () => {
    render(<ChatComposer value={"a".repeat(7_901)} onChange={vi.fn()} onSubmit={vi.fn()} signedIn />);
    expect(screen.getByLabelText("7,901 of 8,000 characters")).toBeInTheDocument();
    expect(screen.getByText("7,901/8,000")).toBeInTheDocument();
  });

  it("keeps the sending progress indicator animated", () => {
    render(<ChatComposer value="hello" onChange={vi.fn()} onSubmit={vi.fn()} signedIn sending />);
    const spinner = screen.getByRole("button", { name: "Sending message" }).querySelector("svg");

    expect(spinner).toHaveClass("animate-spin");
    expect(spinner).not.toHaveClass("motion-reduce:animate-none");
  });
});
