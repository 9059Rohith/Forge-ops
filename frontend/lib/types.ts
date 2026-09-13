export type TaskStatus =
  | "queued"
  | "planning"
  | "engineering"
  | "reviewing"
  | "blocked"
  | "awaiting_authorization"
  | "manual_review_required"
  | "repairing"
  | "audit_complete"
  | "verified"
  | "failed";

export interface Project {
  id: string;
  repo_url: string;
  repo_full_name?: string | null;
  branch: string;
  created_at: string;
}

export interface Evaluation {
  id: string;
  category: "security" | "scope" | "adversarial";
  score: number;
  severity: "none" | "low" | "medium" | "high" | "critical";
  finding: string;
  evidence: Record<string, unknown>;
}

export interface AgentRun {
  id: string;
  agent_name: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  output: Record<string, unknown>;
}

export interface FlightLog {
  id: string;
  timestamp: string;
  event: string;
}

export interface VerificationReceipt {
  schema_version: "1.0";
  receipt_id: string;
  decision: "VERIFIED" | "BLOCKED" | "AUDIT_COMPLETE";
  task: {
    id: string;
    description: string;
    repository: string;
    branch: string;
    changed_files: string[];
  };
  verification: {
    tests: { passed: number; total: number };
    reviewers: Record<
      string,
      {
        score: number;
        severity: string;
        finding: string;
        evidence: Record<string, unknown>;
      }
    >;
    confidence: number | null;
    risk_level: string | null;
    repair_cycles: number;
  };
  provenance: {
    agent_runs: Array<Record<string, unknown>>;
    flight_logs: Array<Record<string, unknown>>;
  };
  artifacts: { diff_sha256: string; proof_sha256: string };
  integrity: { algorithm: "sha256"; digest: string };
}

export interface TaskDetail {
  id: string;
  user_id: string | null;
  description: string;
  status: TaskStatus;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | null;
  confidence_score: number | null;
  repair_cycles: number;
  tests_passed: number;
  tests_total: number;
  changed_files: string[];
  error_message: string | null;
  pending_plan: string | null;
  repair_branch?: string | null;
  pr_url?: string | null;
  pr_number?: number | null;
  created_at: string;
  updated_at: string;
  project: Project;
  evaluations: Evaluation[];
  agent_runs: AgentRun[];
}

export interface TaskInput {
  repo_url: string;
  branch: string;
  description: string;
}

export interface BillingStatus {
  user_id: string;
  plan: "free" | "developer" | "pro" | "team";
  subscription_status: "active" | "past_due" | "canceled";
  credits_remaining: number;
  credits_used: number;
  credits_total: number;
  period_end: string | null;
}

export interface RepairAuthorization {
  task_id: string;
  awaiting_authorization: boolean;
  credits_remaining: number;
  pending_plan: string | null;
}

