import { useEffect, useState } from "react";
import { api } from "./client";
import type { ApprovalDecision, ApprovalRequest } from "./contracts";

const labels = { command: "Run a command", file_change: "Change files", permissions: "Expand permissions" };

export function AccessReview() {
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const result = await api<ApprovalRequest[]>("/api/approvals", { signal: controller.signal });
        if (!controller.signal.aborted) setRequests(result);
      } catch {
        // A stale review must not survive a service disconnect.
        if (!controller.signal.aborted) setRequests([]);
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(() => void refresh(), 1000);
      }
    }
    void refresh();
    return () => { controller.abort(); clearTimeout(timer); };
  }, []);

  async function decide(request: ApprovalRequest, decision: ApprovalDecision["decision"]) {
    setBusy(true); setError("");
    try {
      await api(`/api/jobs/${encodeURIComponent(request.run_id)}/approvals/${encodeURIComponent(request.id!)}`, { method: "POST", body: JSON.stringify({ decision }) });
      setRequests((items) => items.filter((item) => item.id !== request.id));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "The review could not be submitted. No permission was granted.");
    } finally { setBusy(false); }
  }

  return <>
    {error && <p role="alert">{error}</p>}
    {requests.map((request) => <section className="plain-panel" key={request.id} aria-label="Requested access review" aria-live="polite">
      <h2>Review requested access</h2>
      <p>{request.provider} requested: {labels[request.kind]}.</p>
      <p>{request.message}</p>
      <p>Waiting until {new Date(request.expires_at).toLocaleTimeString()}. If unanswered, research stops without granting access.</p>
      <fieldset disabled={busy}>
        <legend>Choose how to continue</legend>
        <button onClick={() => void decide(request, "deny")}>Deny access and continue</button>
        <button onClick={() => void decide(request, "cancel")}>Cancel this research</button>
      </fieldset>
    </section>)}
  </>;
}
