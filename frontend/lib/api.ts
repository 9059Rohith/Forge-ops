import type { BillingStatus, FlightLog, RepairAuthorization, TaskDetail, TaskInput, VerificationReceipt } from "@/lib/types";

const API_BASE = "/api/backend";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch (cause) {
    throw new Error("ForgeGuard API is unavailable. Check the service connection and try again.", {
      cause,
    });
  }
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
  request<{ markdown: string; receipt: VerificationReceipt | null }>(
    `/api/tasks/${encodeURIComponent(id)}/proof`,
  );

export const getBillingStatus = (userId: string) =>
  request<BillingStatus>(`/api/billing/status/${encodeURIComponent(userId)}`);
export const createCheckout = (userId: string, plan: "developer" | "pro" | "team") =>
  request<{ checkout_url: string }>("/api/billing/checkout", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, plan }),
  });
export const getAuthorization = (id: string) =>
  request<RepairAuthorization>(`/api/repairs/${encodeURIComponent(id)}/authorization`);
export const authorizeRepair = (id: string) =>
  request<{ task_id: string; status: string; credits_remaining: number }>(
    `/api/repairs/${encodeURIComponent(id)}/authorize`,
    { method: "POST" },
  );

