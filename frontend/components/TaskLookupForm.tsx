"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const TASK_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function TaskLookupForm() {
  const router = useRouter();
  const [taskId, setTaskId] = useState("");
  const [error, setError] = useState("");

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = taskId.trim();
    if (!TASK_ID_PATTERN.test(normalized)) {
      setError("Enter the task ID returned by the signed GitHub webhook.");
      return;
    }
    router.push(`/task/${normalized}`);
  }

  return (
    <form onSubmit={submit} className="rounded-[10px] border border-line bg-panel/90 p-6 shadow-panel md:p-9">
      <p className="font-mono text-xs uppercase tracking-[.18em] text-mint">Webhook task tracking</p>
      <h2 className="mt-2 text-2xl font-semibold text-ink">Open a signed GitHub job</h2>
      <p className="mt-3 text-sm leading-6 text-muted">
        Production jobs start from verified GitHub push webhooks. Paste the returned task ID to follow its evidence live.
      </p>
      <label htmlFor="task-id" className="mb-2 mt-6 block font-mono text-sm tracking-wide text-muted">Task ID</label>
      <Input
        id="task-id"
        value={taskId}
        onChange={(event) => setTaskId(event.target.value)}
        placeholder="00000000-0000-0000-0000-000000000000"
        autoComplete="off"
        spellCheck={false}
      />
      {error ? <p role="alert" className="mt-3 text-sm text-danger">{error}</p> : null}
      <Button type="submit" className="mt-5 w-full">
        Open task
        <ArrowRight className="size-4" aria-hidden="true" />
      </Button>
    </form>
  );
}
