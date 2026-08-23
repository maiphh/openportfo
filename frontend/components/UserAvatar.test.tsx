import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import UserAvatar from "@/components/UserAvatar";

const profile = { userId: "sub-1", email: "ada@example.com", name: "Ada Lovelace" };

describe("UserAvatar", () => {
  afterEach(cleanup);
  it("renders a deterministic DiceBear image for a profile", () => {
    render(<UserAvatar profile={profile} />);
    const image = screen.getByRole("img");
    expect(image).toHaveAttribute("src", expect.stringContaining("api.dicebear.com/9.x/notionists/svg"));
    expect(image).toHaveAttribute("alt", "Ada Lovelace");
    expect(screen.queryByText("AL")).not.toBeInTheDocument();
  });

  it("renders the guest icon without an image when signed out", () => {
    render(<UserAvatar profile={null} />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Guest account")).toBeInTheDocument();
  });

  it("falls back to initials after an image error", () => {
    render(<UserAvatar profile={profile} />);
    const image = screen.getByRole("img");
    fireEvent.error(image);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("AL")).toBeInTheDocument();
  });

  it("resets the explicit error state when identity changes", () => {
    const { rerender } = render(<UserAvatar profile={profile} />);
    fireEvent.error(screen.getByRole("img"));
    expect(screen.getByText("AL")).toBeInTheDocument();

    rerender(<UserAvatar profile={{ userId: "sub-2", email: "bob@example.com", name: "Bob Stone" }} />);
    expect(screen.getByRole("img")).toHaveAttribute("src", expect.stringContaining("seed=sub-2"));
    expect(screen.queryByText("AL")).not.toBeInTheDocument();
    expect(screen.queryByText("BS")).not.toBeInTheDocument();
    fireEvent.error(screen.getByRole("img"));
    expect(screen.getByText("BS")).toBeInTheDocument();
  });

  it("supports the approved avatar extension prop names and aliases", () => {
    render(
      <UserAvatar
        profile={profile}
        avatarStyle="shapes"
        avatarSeed="stable-seed"
        avatarColor="#abc"
      />,
    );
    const image = screen.getByRole("img");
    const src = new URL(image.getAttribute("src") || "");
    expect(src.pathname).toContain("/shapes/svg");
    expect(src.searchParams.get("seed")).toBe("stable-seed");
    expect(src.searchParams.get("backgroundColor")).toBe("abc");
  });
});
