import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api", () => ({ createTask: vi.fn() }));

import { TaskForm } from "@/components/TaskForm";
import { createTask } from "@/lib/api";


describe("TaskForm", () => {
  beforeEach(() => {
    push.mockReset();
    vi.mocked(createTask).mockReset();
  });

  it("submits normalized values and navigates to the task", async () => {
    vi.mocked(createTask).mockResolvedValue({ task_id: "task-123" });
    render(<TaskForm />);

    await userEvent.clear(screen.getByLabelText("Repository"));
    await userEvent.type(screen.getByLabelText("Repository"), "demo");
    await userEvent.click(screen.getByRole("button", { name: /start autonomous engineering/i }));

    expect(createTask).toHaveBeenCalledWith({
      repo_url: "demo",
      branch: "main",
      description: "Add retry handling with exponential backoff to checkout. Do not change the public API.",
    });
    expect(push).toHaveBeenCalledWith("/task/task-123");
  });

  it("shows an actionable error when submission fails", async () => {
    vi.mocked(createTask).mockRejectedValue(new Error("Backend unavailable"));
    render(<TaskForm />);

    await userEvent.click(screen.getByRole("button", { name: /start autonomous engineering/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable");
  });
});

