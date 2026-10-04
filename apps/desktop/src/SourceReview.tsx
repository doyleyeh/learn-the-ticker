import { useEffect, useState } from "react";
import { api } from "./client";
import type { SourceReviewDecision, SourceReviewRequest } from "./contracts";

export function SourceReview({ onReviewed }: { onReviewed: (runId: string) => void }) {
  const [requests, setRequests] = useState<SourceReviewRequest[]>([]);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const rows = await api<SourceReviewRequest[]>("/api/source-reviews", { signal: controller.signal });
        if (!controller.signal.aborted) setRequests(rows);
      } catch {
        if (!controller.signal.aborted) setRequests([]);
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(() => void refresh(), 1000);
      }
    }
    void refresh();
    return () => { controller.abort(); clearTimeout(timer); };
  }, []);
  async function decide(request: SourceReviewRequest, decision: SourceReviewDecision) {
    await api(`/api/jobs/${encodeURIComponent(request.run_id)}/source-reviews/${encodeURIComponent(request.id!)}`,
      { method: "POST", body: JSON.stringify(decision) });
    setRequests((rows) => rows.filter((row) => row.id !== request.id));
    onReviewed(request.run_id);
  }
  return <>{requests.map((request) => <SourceReviewCard key={request.id} request={request} onDecide={(decision) => decide(request, decision)}/>)}</>;
}

export function SourceReviewCard({ request, onDecide }: { request: SourceReviewRequest; onDecide: (decision: SourceReviewDecision) => Promise<void> }) {
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(decision: SourceReviewDecision) {
    setBusy(true); setError("");
    try { await onDecide(decision); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "Source review could not be submitted."); }
    finally { setBusy(false); }
  }
  return <section className="plain-panel source-review" aria-label="Source review">
    <h2>Choose sources for this research</h2>
    <p>Asset: {request.asset_id} · Research: {request.run_id.slice(0, 8)}</p>
    <p>The app will retrieve and independently check selected sources. Approval does not verify facts or expand usage rights. These pages have not yet been checked for this stage; publication and as-of dates remain unknown.</p>
    <p>Identity lookup and your provider’s permitted web browsing remain part of cloud research. This review controls the app’s evidence retrieval and admission.</p>
    <p>Waiting until {new Date(request.expires_at).toLocaleTimeString()}. Unanswered reviews stop research without approval. Earlier saved research stays available.</p>
    {error && <p role="alert">{error}</p>}
    <fieldset disabled={busy || Date.now() >= Date.parse(request.expires_at)}>
      <legend>Select permitted sources</legend>
      {request.sources.map((source) => <div className="source-review-option" key={source.id}>
        <label><input type="checkbox" checked={selected.includes(source.id!)} onChange={(event) => setSelected((ids) => event.target.checked ? [...ids, source.id!] : ids.filter((id) => id !== source.id))}/>{source.publisher} · {source.url}</label>
        <p>Usage permission: {source.policy} · Rules reviewed {source.reviewed_at} · <a href={source.rights_url} target="_blank" rel="noopener noreferrer">Source usage terms</a></p>
        {source.local_numeric_only && <p>Private numerical retrieval only. Yahoo history uses the owner-approved experimental local-use exception, not a Yahoo permission grant. Yahoo values and derived content stay out of cloud prompts and shareable exports. Source mapping and numerical checks still apply.</p>}
      </div>)}
      <div className="actions">
        <button type="button" onClick={() => setSelected(request.sources.map((source) => source.id!))}>Select listed sources</button>
        <button type="button" disabled={!selected.length} onClick={() => void submit({ source_ids: selected })}>Use selected sources</button>
        <button type="button" onClick={() => void submit({ source_ids: [] })}>Skip these sources</button>
        <button type="button" onClick={() => void submit({ cancel: true })}>Cancel this research</button>
      </div>
    </fieldset>
  </section>;
}
