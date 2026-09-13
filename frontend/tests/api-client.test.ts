import { afterEach, describe, expect, it, vi } from "vitest";

import { createTask } from "@/lib/api";

describe("API client transport", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("submits tasks through the same-origin backend proxy", async () => {
    const requestedUrls: string[] = [];
    vi.stubGlobal("fetch", async (input: RequestInfo | URL) => {
      requestedUrls.push(String(input));
      return new Response(JSON.stringify({ task_id: "task-123" }), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      });
    });

    await createTask({
      repo_url: "C:/projects/checkout",
      branch: "main",
      description: "Add bounded retries",
    });

    expect(requestedUrls).toEqual(["/api/backend/api/tasks"]);
  });

  it("turns a network failure into an actionable backend error", async () => {
    vi.stubGlobal("fetch", async () => {
      throw new TypeError("Failed to fetch");
    });

    await expect(
      createTask({
        repo_url: "C:/projects/checkout",
        branch: "main",
        description: "Add bounded retries",
      }),
    ).rejects.toThrow("ForgeGuard API is unavailable. Check the service connection and try again.");
  });
});
