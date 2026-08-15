import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getBillingStatus: vi.fn(),
  authorizeRepair: vi.fn(),
  createCheckout: vi.fn(),
}));

import { AuthorizationCard } from "@/components/AuthorizationCard";
import { RepairCreditsCard } from "@/components/RepairCreditsCard";
import { authorizeRepair, getBillingStatus } from "@/lib/api";


describe("Repair Credits", () => {
  it("renders plan usage and remaining repairs", async () => {
    vi.mocked(getBillingStatus).mockResolvedValue({
      user_id: "demo",
      plan: "pro",
      subscription_status: "active",
      credits_remaining: 147,
      credits_used: 3,
      credits_total: 150,
      period_end: "2026-09-01T00:00:00Z",
    });

    render(<RepairCreditsCard userId="demo" />);

    expect(await screen.findByText("147 repairs remaining")).toBeInTheDocument();
    expect(screen.getByText("Pro plan")).toBeInTheDocument();
  });

  it("shows a stable error state when billing is unavailable", async () => {
    vi.mocked(getBillingStatus).mockRejectedValue(new Error("offline"));
    render(<RepairCreditsCard userId="demo" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Repair Credits are temporarily unavailable");
  });

  it("authorizes one pending repair credit", async () => {
    vi.mocked(authorizeRepair).mockResolvedValue({
      task_id: "task-1",
      status: "authorized",
      credits_remaining: 2,
    });
    const authorized = vi.fn();
    render(
      <AuthorizationCard
        taskId="task-1"
        severity="critical"
        summary="Authorization boundary removed"
        confidence={91}
        creditsRemaining={3}
        onAuthorized={authorized}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /authorize repair/i }));

    await waitFor(() => expect(authorizeRepair).toHaveBeenCalledWith("task-1"));
    expect(authorized).toHaveBeenCalled();
  });
});
