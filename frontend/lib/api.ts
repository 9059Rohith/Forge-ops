import type { FlightLog, TaskDetail, TaskInput } from "@/lib/types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string | Array<{ msg: string }> };
      if (typeof body.detail === "string") detail = body.detail;
      if (Array.isArray(body.detail)) detail = body.detail.map((item) => item.msg).join("; ");
    } catch {
      // Preserve the status-based fallback for non-JSON upstream failures.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const createTask = (input: TaskInput) =>
  request<{ task_id: string }>("/api/tasks", { method: "POST", body: JSON.stringify(input) });

export const getTask = (id: string) => request<TaskDetail>(`/api/tasks/${encodeURIComponent(id)}`);
export const getFlightLog = (id: string) =>
  request<FlightLog[]>(`/api/tasks/${encodeURIComponent(id)}/flight-log`);
export const getDiff = (id: string) =>
  request<{ diff: string }>(`/api/tasks/${encodeURIComponent(id)}/diff`);
export const getProof = (id: string) =>
  request<{ markdown: string }>(`/api/tasks/${encodeURIComponent(id)}/proof`);

