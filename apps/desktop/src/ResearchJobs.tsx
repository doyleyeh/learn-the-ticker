import { useEffect, useState } from "react";
import { api } from "./client";
import type { ResearchJobSummary } from "./contracts";

export function ResearchJobs({ currentId, revision, onOpen }: { currentId?: string; revision?: string; onOpen: (id: string) => Promise<void> }) {
  const [jobs, setJobs] = useState<ResearchJobSummary[]>([]);
  const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState("");
  const [opening, setOpening] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void api<ResearchJobSummary[]>("/api/research/jobs", { signal: controller.signal }).then((value) => {
      if (!controller.signal.aborted) { setJobs(value); setError(""); }
    }).catch(() => { if (!controller.signal.aborted) setError("Research history could not be loaded. Reconnect and refresh the list."); });
    return () => controller.abort();
  }, [refresh, revision]);
  async function open(id: string) {
    setOpening(true); setError("");
    try { await onOpen(id); }
    catch { setError("This job could not be opened. Reconnect and refresh the list; no research was restarted."); }
    finally { setOpening(false); }
  }
  return <details className="plain-panel research-jobs"><summary>Recent research jobs ({jobs.length})</summary>
    <p>Reopen progress or a saved result after reconnecting. Opening a job never starts it again. Up to 50 jobs are shown, active jobs first.</p>
    <button onClick={() => setRefresh(refresh + 1)}>Refresh job list</button>
    {error && <p role="alert" className="error">{error}</p>}
    <ResearchJobList jobs={jobs} currentId={currentId} disabled={opening} onOpen={(id) => { void open(id); }}/>
  </details>;
}

export function ResearchJobList({ jobs, currentId, disabled, onOpen }: {
  jobs: ResearchJobSummary[]; currentId?: string; disabled: boolean; onOpen: (id: string) => void;
}) {
  return <>{jobs.length === 0 && <p>No retained research jobs yet.</p>}{jobs.map((job) => <article key={job.id}>
    <p>{job.request.query}</p><p>Status: {job.status.replaceAll("_", " ")} · Requested {new Date(job.created_at).toLocaleString()}</p>
    <p>{job.request.provider ?? "codex"} · {job.request.model ?? "Default model at request time"} · {job.request.language ?? "en"} · {job.request.level ?? "beginner"}</p>
    {job.request.asset_id && <p>Scope: {job.request.asset_id}</p>}
    <button disabled={disabled} aria-pressed={job.id === currentId} onClick={() => onOpen(job.id)}>{job.id === currentId ? "Reopen viewed job" : "Open job"}</button>
  </article>)}</>;
}
