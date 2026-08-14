"use client";

import { useMemo } from "react";
import { Background, Controls, Handle, Position, ReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";
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

export function AgentGraph({ task }: { task: TaskDetail }) {
  const graph = useMemo(() => {
    const evaluation = Object.fromEntries(task.evaluations.map((item) => [item.category, item]));
    const active = task.status;
    const reviewState = (name: string): GraphData["state"] => evaluation[name] ? (["high", "critical"].includes(evaluation[name].severity) ? "danger" : "success") : active === "reviewing" ? "active" : "idle";
    const nodes: Node<GraphData>[] = [
      { id: "engineer", type: "evidence", position: { x: 20, y: 64 }, data: { label: "Engineer", detail: task.agent_runs.some((run) => run.agent_name === "engineer" && run.status === "completed") ? "Patch generated" : "Preparing patch", state: ["engineering", "planning"].includes(active) ? "active" : task.agent_runs.some((run) => run.agent_name === "engineer") ? "success" : "idle", icon: "engineer" } },
      { id: "security", type: "evidence", position: { x: 285, y: 0 }, data: { label: "Security", detail: evaluation.security ? `${evaluation.security.score}%` : "Independent review", state: reviewState("security"), icon: "security" } },
      { id: "scope", type: "evidence", position: { x: 285, y: 64 }, data: { label: "Scope", detail: evaluation.scope ? `${evaluation.scope.score}%` : "Independent review", state: reviewState("scope"), icon: "scope" } },
      { id: "adversarial", type: "evidence", position: { x: 285, y: 128 }, data: { label: "Adversarial", detail: evaluation.adversarial ? `${evaluation.adversarial.score}%` : "Challenge patch", state: reviewState("adversarial"), icon: "adversarial" } },
      { id: "risk", type: "evidence", position: { x: 555, y: 64 }, data: { label: "Risk Engine", detail: task.risk_level ? `${task.risk_level} · ${task.confidence_score}%` : "Awaiting evidence", state: task.risk_level ? (task.risk_level === "LOW" ? "success" : "danger") : active === "reviewing" ? "active" : "idle", icon: "risk" } },
      { id: "result", type: "evidence", position: { x: 815, y: 64 }, data: { label: task.status === "verified" ? "VERIFIED" : task.status === "failed" || task.status === "blocked" ? "BLOCKED" : "Decision", detail: task.status === "verified" ? "Proof ready" : task.status === "repairing" ? "Repairing" : "Pending", state: task.status === "verified" ? "success" : ["failed", "blocked"].includes(task.status) ? "danger" : task.status === "repairing" ? "active" : "idle", icon: "result" } },
    ];
    const edges: Edge[] = ["security", "scope", "adversarial"].flatMap((reviewer) => [
      { id: `engineer-${reviewer}`, source: "engineer", target: reviewer, animated: active === "reviewing", style: { stroke: "#49606e", strokeWidth: 1.5 } },
      { id: `${reviewer}-risk`, source: reviewer, target: "risk", animated: active === "reviewing", style: { stroke: "#49606e", strokeWidth: 1.5 } },
    ]).concat([{ id: "risk-result", source: "risk", target: "result", animated: active === "reviewing", style: { stroke: task.status === "verified" ? "#64e6bd" : "#49606e", strokeWidth: 1.7 } }]);
    return { nodes, edges };
  }, [task]);

  return (
    <section className="h-[260px] overflow-hidden rounded-lg border border-line bg-[#07111a] xl:h-[190px]" aria-label="Live agent verification graph">
      <ReactFlow nodes={graph.nodes} edges={graph.edges} nodeTypes={nodeTypes} fitView minZoom={0.55} maxZoom={1.35} nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} proOptions={{ hideAttribution: true }}>
        <Background color="#1c2b36" gap={24} size={1} />
        <Controls showInteractive={false} className="!border-line !bg-panel !fill-ink" />
      </ReactFlow>
    </section>
  );
}
