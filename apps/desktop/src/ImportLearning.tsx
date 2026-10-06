import { useEffect, useRef, useState } from "react";
import { api, watchJob } from "./client";
import type { ImportExplanation, ImportLearningScope, RetainedImportView, Settings } from "./contracts";
import { DeleteSavedItem } from "./DeleteSavedItem";

type LearningJob = { id?: string; status: string; result?: ImportExplanation; error?: string };

export function ImportLearning({ view, settings, level }: { view: RetainedImportView; settings?: Settings; level: "beginner" | "intermediate" }) {
  const [permission, setPermission] = useState(false);
  const [job, setJob] = useState<LearningJob>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const request = useRef<AbortController | undefined>(undefined);
  const documentId = view.item.id, contentHash = view.item.content_hash, language = settings?.language ?? "en";
  const busy = loading || job?.status === "queued" || job?.status === "running";
  useEffect(() => () => { request.current?.abort(); request.current = undefined; }, []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setJob(undefined); setError(""); setPermission(false);
    const scope: ImportLearningScope = { document_id: documentId, content_hash: contentHash, language, level };
    api<LearningJob>("/api/imports/explanations/lookup", { method: "POST", body: JSON.stringify(scope), signal: controller.signal }).then((value) => {
      if (!controller.signal.aborted) setJob(value);
    }).catch((error: unknown) => { if (!controller.signal.aborted) setError(error instanceof Error ? error.message : "Saved explanation unavailable."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [documentId, contentHash, language, level]);

  useEffect(() => {
    if (!job?.id || !["queued", "running"].includes(job.status)) return;
    let active = true, polling = false;
    const controller = new AbortController();
    async function refresh() {
      if (polling) return;
      polling = true;
      try {
        const value = await api<LearningJob>(`/api/jobs/${job!.id}`, { signal: controller.signal });
        if (active) { setJob(value); if (value.error) setError(value.error); }
      } catch (error) { if (active) setError(error instanceof Error ? error.message : "Explanation status unavailable."); }
      finally { polling = false; }
    }
    const close = watchJob(job.id, () => { void refresh(); }, () => { void refresh(); });
    const timer = setInterval(() => { void refresh(); }, 2000);
    return () => { active = false; controller.abort(); clearInterval(timer); close(); };
  }, [job?.id, job?.status]);

  async function generate() {
    if (busy || request.current || !permission || !settings?.cloud_enabled) return;
    const controller = new AbortController(); request.current = controller;
    setLoading(true); setError("");
    try {
      const value = await api<LearningJob>("/api/imports/explanations", { method: "POST", signal: controller.signal, body: JSON.stringify({
        document_id: documentId, content_hash: contentHash, language, level, provider: settings.provider ?? "codex", model: settings.model,
        transmission_confirmed: true,
      }) });
      if (request.current === controller) { setJob(value); setPermission(false); }
    } catch (error) {
      if (request.current === controller) setError(`${error instanceof Error ? error.message : "Explanation request unavailable."} Reopen this document to check its status before retrying after a lost connection.`);
    } finally {
      if (request.current === controller) { request.current = undefined; setLoading(false); }
    }
  }

  return <section className="plain-panel" aria-labelledby="import-learning-heading">
    <h2 id="import-learning-heading">Understand this document</h2>
    <p>Explanations use this retained document only, with browsing disabled. They do not check its claims against other sources or become facts or chart values.</p>
    <p>{language} · {level} · Selected provider: {settings?.provider ?? "codex"}</p>
    {job?.result ? <ImportExplanationDetails value={job.result}/> : <>
      {!settings?.cloud_enabled && <p>Online explanations are off. Previously saved explanations remain available.</p>}
      <label><input type="checkbox" checked={permission} disabled={busy || !settings?.cloud_enabled} onChange={(event) => setPermission(event.target.checked)}/> I have permission to send this document’s extracted content and title to my selected AI provider for this explanation.</label>
      <button disabled={busy || !permission || !settings?.cloud_enabled} onClick={() => void generate()}>Explain this document</button>
    </>}
    {loading && <p role="status">Checking the document and saved explanation…</p>}
    {(job?.status === "queued" || job?.status === "running") && <><p role="status">Preparing your explanation with browsing disabled.</p><button onClick={() => {
      void api<LearningJob>(`/api/jobs/${job.id}/cancel`, { method: "POST" }).then(setJob).catch((error: unknown) => setError(error instanceof Error ? error.message : "Cancellation could not be confirmed."));
    }}>Cancel document explanation</button></>}
    {job?.status === "unavailable" && <p>No saved explanation for this document, language and reader level.</p>}
    {job?.status === "cancelled" && <p role="status">Explanation cancelled.</p>}
    {job?.result && <DeleteSavedItem key={`delete:${job.result.id}`} kind="import_explanation" id={job.result.id} title={`${view.item.title} · ${job.result.language} · ${job.result.level}`} onDeleted={() => {
      setJob({ status: "unavailable" }); setPermission(false); setError("");
    }}/>}
    {error && <p role="alert" className="error">{error}</p>}
  </section>;
}

export function ImportExplanationDetails({ value }: { value: ImportExplanation }) {
  return <div className="import-result" aria-live="polite">
    <h3>Saved interpretation · Unverified</h3>
    <p>{value.explanation}</p>
    <p>Generated {new Date(value.created_at!).toLocaleString()} · {value.provider} · {value.language} · {value.level}. This date does not establish source freshness.</p>
    <p>Original document references below. Quotes confirm where text appeared; they do not independently verify the explanation.</p>
    <ul>{value.references.map((reference, index) => <li key={`${reference.locator}:${index}`}><strong>{reference.locator}</strong><blockquote>{reference.quote}</blockquote></li>)}</ul>
  </div>;
}
