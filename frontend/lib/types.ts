export type TaskStatus =
  | "queued"
  | "planning"
  | "engineering"
  | "reviewing"
  | "blocked"
  | "repairing"
  | "verified"
  | "failed";

export interface Project {
  id: string;
  repo_url: string;
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

export interface TaskDetail {
  id: string;
  description: string;
  status: TaskStatus;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | null;
  confidence_score: number | null;
  repair_cycles: number;
  tests_passed: number;
  tests_total: number;
  changed_files: string[];
  error_message: string | null;
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

