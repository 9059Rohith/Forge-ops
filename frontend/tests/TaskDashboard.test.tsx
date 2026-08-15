import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

vi.mock("next/dynamic", () => ({ default: () => () => <div data-testid="diff-editor" /> }));
vi.mock("@/components/AgentGraph", () => ({ AgentGraph: () => <div data-testid="agent-graph" /> }));

import { TaskDashboard } from "@/components/TaskDashboard";
import type { TaskDetail, VerificationReceipt } from "@/lib/types";

const task: TaskDetail = {
  id: "task-1",
  user_id: "user-1",
  description: "Add retry handling",
  status: "verified",
  risk_level: "LOW",
  confidence_score: 94.6,
  repair_cycles: 1,
  tests_passed: 5,
  tests_total: 5,
  changed_files: ["checkout.py", "tests/test_checkout.py"],
  error_message: null,
  pending_plan: null,
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
    render(<TaskDashboard task={task} logs={[]} diff="diff" proof="proof body" receipt={null} loading={false} />);

    expect(screen.getByText("VERIFIED")).toBeInTheDocument();
    expect(screen.getAllByText("94.6%").length).toBeGreaterThan(0);
    await userEvent.click(screen.getByText("Security Review"));
    expect(screen.getByText(/flagged_files/i)).toBeInTheDocument();
  });

  it("copies the proof package", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    render(<TaskDashboard task={task} logs={[]} diff="diff" proof="proof body" receipt={null} loading={false} />);

    await userEvent.click(screen.getByRole("button", { name: /copy proof/i }));
    expect(writeText).toHaveBeenCalledWith("proof body");
  });

  it("downloads the sealed verification receipt with its visible identity", async () => {
    const createObjectURL = vi.fn().mockReturnValue("blob:forgeguard-receipt");
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const receipt = {
      schema_version: "1.0",
      receipt_id: "fg_deadbeefdeadbeef",
      decision: "VERIFIED",
      task: {
        id: "task-1",
        description: "Add retry handling",
        repository: "demo",
        branch: "main",
        changed_files: ["checkout.py"],
      },
      verification: {
        tests: { passed: 5, total: 5 },
        reviewers: {},
        confidence: 94.6,
        risk_level: "LOW",
        repair_cycles: 1,
      },
      provenance: { agent_runs: [], flight_logs: [] },
      artifacts: { diff_sha256: "a".repeat(64), proof_sha256: "b".repeat(64) },
      integrity: { algorithm: "sha256", digest: "c".repeat(64) },
    } satisfies VerificationReceipt;
    render(
      <TaskDashboard
        task={task}
        logs={[]}
        diff="diff"
        proof="proof body"
        loading={false}
        receipt={receipt}
      />,
    );

    expect(screen.getByText("fg_deadbeefdeadbeef")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /download receipt/i }));

    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect((click.mock.instances[0] as HTMLAnchorElement).download).toBe(
      "forgeguard-fg_deadbeefdeadbeef.json",
    );
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:forgeguard-receipt");
    click.mockRestore();
  });
});
