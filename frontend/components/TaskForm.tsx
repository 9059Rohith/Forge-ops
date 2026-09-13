"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, LoaderCircle } from "lucide-react";
import { createTask } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export function TaskForm() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!repoUrl.trim() || !branch.trim() || description.trim().length < 3) {
      setError("Repository, branch, and a clear engineering task are required.");
      return;
    }
    setSubmitting(true);
    try {
      const result = await createTask({
        repo_url: repoUrl.trim(),
        branch: branch.trim(),
        description: description.trim(),
      });
      router.push(`/task/${result.task_id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to start the task.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-[10px] border border-line bg-panel/90 p-6 shadow-panel md:p-9">
      <div className="space-y-5">
        <div className="block font-mono text-sm tracking-wide text-muted">
          <label htmlFor="repository" className="mb-2 block">Repository</label>
          <Input
            id="repository"
            value={repoUrl}
            onChange={(event) => setRepoUrl(event.target.value)}
            placeholder="C:/projects/my-repository or https://github.com/org/repository"
            autoComplete="url"
            spellCheck={false}
            aria-describedby="repository-hint"
          />
          <span id="repository-hint" className="sr-only">Use a local repository path or an HTTPS GitHub URL.</span>
        </div>
        <div className="block font-mono text-sm tracking-wide text-muted">
          <label htmlFor="branch" className="mb-2 block">Branch</label>
          <Input id="branch" value={branch} onChange={(event) => setBranch(event.target.value)} spellCheck={false} />
        </div>
        <div className="block font-mono text-sm tracking-wide text-muted">
          <label htmlFor="engineering-task" className="mb-2 block">Engineering task</label>
          <Textarea
            id="engineering-task"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Describe the engineering change and its constraints"
          />
        </div>
        {error && (
          <p role="alert" className="rounded-md border border-danger/35 bg-danger/10 px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : null}
          {submitting ? "Starting secure worktree…" : "Start autonomous engineering"}
          {!submitting && <ArrowRight className="size-4" aria-hidden="true" />}
        </Button>
      </div>
    </form>
  );
}
