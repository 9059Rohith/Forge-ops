import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api", () => ({
  createTask: vi.fn(),
  getBillingStatus: vi.fn(() => new Promise(() => undefined)),
}));

import { TaskForm } from "@/components/TaskForm";
import { createTask } from "@/lib/api";
import HomePage from "@/app/page";


describe("TaskForm", () => {
  const originalSubmissionMode = process.env.TASK_SUBMISSION_MODE;

  beforeEach(() => {
    push.mockReset();
    vi.mocked(createTask).mockReset();
  });

  afterEach(() => {
    if (originalSubmissionMode === undefined) delete process.env.TASK_SUBMISSION_MODE;
    else process.env.TASK_SUBMISSION_MODE = originalSubmissionMode;
  });

  it("starts without fabricated repository or task data", () => {
    render(<TaskForm />);

    expect(screen.getByLabelText("Repository")).toHaveValue("");
    expect(screen.getByLabelText("Engineering task")).toHaveValue("");
  });

  it("does not request demo billing data without an authenticated user", () => {
    render(<HomePage />);

    expect(screen.queryByLabelText(/repair credits/i)).not.toBeInTheDocument();
  });

  it("uses task lookup instead of unsupported submission in webhook mode", async () => {
    process.env.TASK_SUBMISSION_MODE = "webhook";
    render(<HomePage />);

    expect(screen.queryByRole("button", { name: /start autonomous engineering/i })).not.toBeInTheDocument();
    await userEvent.type(
      screen.getByLabelText("Task ID"),
      "7003ada0-f17d-4d8c-8f1f-508d89044dba",
    );
    await userEvent.click(screen.getByRole("button", { name: /open task/i }));
    expect(push).toHaveBeenCalledWith("/task/7003ada0-f17d-4d8c-8f1f-508d89044dba");
  });

  it("submits normalized values and navigates to the task", async () => {
    vi.mocked(createTask).mockResolvedValue({ task_id: "task-123" });
    render(<TaskForm />);

    await userEvent.type(screen.getByLabelText("Repository"), "C:/projects/checkout");
    await userEvent.type(
      screen.getByLabelText("Engineering task"),
      "Add retry handling with exponential backoff to checkout.",
    );
    await userEvent.click(screen.getByRole("button", { name: /start autonomous engineering/i }));

    expect(createTask).toHaveBeenCalledWith({
      repo_url: "C:/projects/checkout",
      branch: "main",
      description: "Add retry handling with exponential backoff to checkout.",
    });
    expect(push).toHaveBeenCalledWith("/task/task-123");
  });

  it("shows an actionable error when submission fails", async () => {
    vi.mocked(createTask).mockRejectedValue(new Error("Backend unavailable"));
    render(<TaskForm />);

    await userEvent.type(screen.getByLabelText("Repository"), "C:/projects/checkout");
    await userEvent.type(screen.getByLabelText("Engineering task"), "Add bounded retries");
    await userEvent.click(screen.getByRole("button", { name: /start autonomous engineering/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable");
  });
});
