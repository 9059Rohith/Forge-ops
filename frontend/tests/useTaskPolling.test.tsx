import { renderHook, waitFor } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getTask: vi.fn(),
  getFlightLog: vi.fn().mockResolvedValue([]),
  getDiff: vi.fn().mockResolvedValue({ diff: "" }),
  getProof: vi.fn().mockResolvedValue({ markdown: "", receipt: null }),
}));

import { useTaskPolling } from "@/hooks/useTaskPolling";
import { getProof, getTask } from "@/lib/api";


it("does not keep polling after a terminal status", async () => {
  vi.mocked(getTask).mockResolvedValue({ status: "verified" } as never);
  const { result } = renderHook(() => useTaskPolling("task-1", 10));

  await waitFor(() => expect(result.current.task?.status).toBe("verified"));
  await new Promise((resolve) => setTimeout(resolve, 35));
  expect(getTask).toHaveBeenCalledTimes(1);
});

it("exposes the sealed receipt returned with terminal proof", async () => {
  vi.mocked(getTask).mockResolvedValue({ status: "verified" } as never);
  vi.mocked(getProof).mockResolvedValue({
    markdown: "proof",
    receipt: { receipt_id: "fg_deadbeefdeadbeef" } as never,
  });

  const { result } = renderHook(() => useTaskPolling("task-2", 10));

  await waitFor(() => expect(result.current.receipt?.receipt_id).toBe("fg_deadbeefdeadbeef"));
});

