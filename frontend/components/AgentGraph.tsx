"use client";

import { useEffect, useMemo } from "react";
import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  useReactFlow,
  useStore,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { Braces, Check, Cpu, Crosshair, ShieldCheck, Swords } from "lucide-react";
import type { TaskDetail } from "@/lib/types";

type GraphData = { label: string; detail: string; state: "idle" | "active" | "success" | "danger"; icon: string };

const icons = { engineer: Braces, security: ShieldCheck, scope: Crosshair, adversarial: Swords, risk: Cpu, result: Check };

function GraphNode({ data }: NodeProps<Node<GraphData>>) {
  const Icon = icons[data.icon as keyof typeof icons] || Cpu;
  const tone = data.state === "success" ? "border-mint/55 text-mint" : data.state === "danger" ? "border-danger/60 text-danger" : data.state === "active" ? "border-sky-400/60 text-sky-300" : "border-line text-muted";
  return (
    <div className={`min-w-[168px] rounded-lg border bg-[#0d1821] px-4 py-3 shadow-panel ${tone}`}>
      <Handle type="target" position={Position.Left} className="!size-2 !border-canvas !bg-current" />
      <div className="flex items-center gap-3">
        <span className="grid size-8 place-items-center rounded-full border border-current/40 bg-current/5"><Icon className="size-4" /></span>
        <span><strong className="block text-sm text-ink">{data.label}</strong><small className="mt-1 block font-mono text-[10px] text-current">{data.detail}</small></span>
      </div>
      <Handle type="source" position={Position.Right} className="!size-2 !border-canvas !bg-current" />
    </div>
  );
}

const nodeTypes = { evidence: GraphNode };

function FitGraphToViewport() {
  const width = useStore((state) => state.width);
  const height = useStore((state) => state.height);
  const { fitView, getNodes, setViewport } = useReactFlow();

  useEffect(() => {
    if (width <= 0 || height <= 0) return;
    const frame = requestAnimationFrame(() => {
      if (width < 600) {
        void setViewport({ x: 8, y: 48, zoom: 0.75 }, { duration: 0 });
        return;
      }
      void fitView({
        nodes: getNodes(),
        padding: 0.08,
        duration: 0,
        minZoom: 0.55,
        maxZoom: 1.35,
      });
    });
    return () => cancelAnimationFrame(frame);
  }, [fitView, getNodes, height, setViewport, width]);

  return null;
}

export function AgentGraph({ task }: { task: TaskDetail }) {
  const graph = useMemo(() => {
    const evaluation = Object.fromEntries(task.evaluations.map((item) => [item.category, item]));
    const active = task.status;
    const auditMode = active === "audit_complete" || task.pending_plan === "Read-only security audit";
    const reviewState = (name: string): GraphData["state"] => evaluation[name] ? (["high", "critical"].includes(evaluation[name].severity) ? "danger" : "success") : active === "reviewing" ? "active" : "idle";
    const nodes: Node<GraphData>[] = [
      { id: "engineer", type: "evidence", position: { x: 20, y: 64 }, data: auditMode ? { label: "Repository Audit", detail: evaluation.security ? "Source analyzed" : "Indexing source", state: evaluation.security ? "success" : "active", icon: "security" } : { label: "Engineer", detail: task.agent_runs.some((run) => run.agent_name === "engineer" && run.status === "completed") ? "Patch generated" : "Preparing patch", state: ["engineering", "planning"].includes(active) ? "active" : task.agent_runs.some((run) => run.agent_name === "engineer") ? "success" : "idle", icon: "engineer" } },
      { id: "security", type: "evidence", position: { x: 285, y: 0 }, data: { label: "Security", detail: evaluation.security ? `${evaluation.security.score}%` : "Independent review", state: reviewState("security"), icon: "security" } },
      { id: "scope", type: "evidence", position: { x: 285, y: 64 }, data: { label: "Scope", detail: evaluation.scope ? `${evaluation.scope.score}%` : "Independent review", state: reviewState("scope"), icon: "scope" } },
      { id: "adversarial", type: "evidence", position: { x: 285, y: 128 }, data: { label: "Adversarial", detail: evaluation.adversarial ? `${evaluation.adversarial.score}%` : "Challenge patch", state: reviewState("adversarial"), icon: "adversarial" } },
      { id: "risk", type: "evidence", position: { x: 555, y: 64 }, data: { label: "Risk Engine", detail: task.risk_level ? `${task.risk_level} · ${task.confidence_score}%` : "Awaiting evidence", state: task.risk_level ? (task.risk_level === "LOW" ? "success" : "danger") : active === "reviewing" ? "active" : "idle", icon: "risk" } },
      { id: "result", type: "evidence", position: { x: 815, y: 64 }, data: { label: task.status === "audit_complete" ? "AUDIT COMPLETE" : task.status === "verified" ? "VERIFIED" : ["failed", "blocked", "manual_review_required"].includes(task.status) ? "BLOCKED" : "Decision", detail: task.status === "audit_complete" ? "Report ready" : task.status === "verified" ? "Proof ready" : task.status === "repairing" ? "Repairing" : task.status === "manual_review_required" ? "Human review" : "Pending", state: ["verified", "audit_complete"].includes(task.status) ? "success" : ["failed", "blocked", "manual_review_required"].includes(task.status) ? "danger" : task.status === "repairing" ? "active" : "idle", icon: "result" } },
    ];
    const edges: Edge[] = ["security", "scope", "adversarial"].flatMap((reviewer) => [
      { id: `engineer-${reviewer}`, source: "engineer", target: reviewer, animated: active === "reviewing", style: { stroke: "#49606e", strokeWidth: 1.5 } },
      { id: `${reviewer}-risk`, source: reviewer, target: "risk", animated: active === "reviewing", style: { stroke: "#49606e", strokeWidth: 1.5 } },
    ]).concat([{ id: "risk-result", source: "risk", target: "result", animated: active === "reviewing", style: { stroke: ["verified", "audit_complete"].includes(task.status) ? "#64e6bd" : "#49606e", strokeWidth: 1.7 } }]);
    return { nodes, edges };
  }, [task]);

  return (
    <section className="h-[260px] overflow-hidden rounded-lg border border-line bg-[#07111a] xl:h-[190px]" aria-label="Live agent verification graph">
      <ReactFlow nodes={graph.nodes} edges={graph.edges} nodeTypes={nodeTypes} minZoom={0.55} maxZoom={1.35} nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} proOptions={{ hideAttribution: true }}>
        <FitGraphToViewport />
        <Background color="#1c2b36" gap={24} size={1} />
        <Controls showInteractive={false} className="!border-line !bg-panel !fill-ink" />
      </ReactFlow>
    </section>
  );
}
