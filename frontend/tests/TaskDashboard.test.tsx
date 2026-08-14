import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

vi.mock("next/dynamic", () => ({ default: () => () => <div data-testid="diff-editor" /> }));
vi.mock("@/components/AgentGraph", () => ({ AgentGraph: () => <div data-testid="agent-graph" /> }));

import { TaskDashboard } from "@/components/TaskDashboard";
import type { TaskDetail } from "@/lib/types";

const task: TaskDetail = {
  id: "task-1",
  description: "Add retry handling",
  status: "verified",
  risk_level: "LOW",
  confidence_score: 94.6,
  repair_cycles: 1,
  tests_passed: 5,
  tests_total: 5,
  changed_files: ["checkout.py", "tests/test_checkout.py"],
  error_message: null,
  created_at: "2026-08-15T10:12:31Z",
  updated_at: "2026-08-15T10:14:02Z",
  project: { id: "p1", repo_url: "demo", branch: "main", created_at: "2026-08-15T10:12:31Z" },
  evaluations: [
    { id: "e1", category: "security", score: 96, severity: "none", finding: "Authorization remains intact.", evidence: { flagged_files: [] } },
    { id: "e2", category: "scope", score: 97, severity: "none", finding: "Focused change.", evidence: {} },
    { id: "e3", category: "adversarial", score: 94, severity: "low", finding: "Retry bounds covered.", evidence: {} }
  ],
  agent_runs: []
};

describe("TaskDashboard", () => {
  it("renders verification evidence and expands reviewer details", async () => {
    render(<TaskDashboard task={task} logs={[]} diff="diff" proof="proof body" loading={false} />);

    expect(screen.getByText("VERIFIED")).toBeInTheDocument();
    expect(screen.getAllByText("94.6%").length).toBeGreaterThan(0);
    await userEvent.click(screen.getByText("Security Review"));
    expect(screen.getByText(/flagged_files/i)).toBeInTheDocument();
  });

  it("copies the proof package", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    render(<TaskDashboard task={task} logs={[]} diff="diff" proof="proof body" loading={false} />);

    await userEvent.click(screen.getByRole("button", { name: /copy proof/i }));
    expect(writeText).toHaveBeenCalledWith("proof body");
  });
});
