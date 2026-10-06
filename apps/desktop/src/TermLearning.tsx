import { useEffect, useRef, useState, type ReactNode } from "react";
import { glossaryTerms, type GlossaryTerm } from "../lib/glossary";
import { CitationChip } from "../components/CitationChip";
import { api, watchJob } from "./client";
import { sourceRoute } from "./routes";
import { privateSource } from "./marketPresentation";
import type { EvidenceBundle, Settings, TermExplanation, TermRequest } from "./contracts";
import { DeleteSavedItem } from "./DeleteSavedItem";

type TermJob = { id?: string; status: string; result?: TermExplanation; error?: string };
const core = Object.values(glossaryTerms);
export const normalizeTerm = (value: string) => value.normalize("NFKC").trim().replace(/\s+/g, " ").toLocaleLowerCase("en");
export function coreDefinition(value: string): GlossaryTerm | undefined { return core.find((entry) => normalizeTerm(entry.term) === normalizeTerm(value)); }
export function conciseSelection(value: string): string { const text = value.trim().replace(/\s+/g, " "); return text.length <= 120 && text.split(" ").length <= 16 ? text : ""; }

export function TermLearning({ bundle, level, settings, children }: { bundle: EvidenceBundle; level: "beginner" | "intermediate"; settings?: Settings; children: ReactNode }) {
  const [term, setTerm] = useState("");
  const [mode, setMode] = useState<"term" | "question">("term");
  const [selected, setSelected] = useState("");
  const [job, setJob] = useState<TermJob>();
  const [answer, setAnswer] = useState<TermExplanation>();
  const [error, setError] = useState("");
  const [requesting, setRequesting] = useState(false);
  const [progress, setProgress] = useState("");
  const [cached, setCached] = useState<Record<string, TermExplanation>>({});
  const panel = useRef<HTMLElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const requests = useRef(new Set<string>());
  const revision = useRef(0);
  const busy = requesting || job?.status === "queued" || job?.status === "running";
  const fallback = mode === "term" ? coreDefinition(term) : undefined;
  const language = settings?.language ?? bundle.language ?? "en";
  const common = bundle.asset.asset_type === "stock" ? ["revenue", "market cap", "operating margin", "EPS", "free cash flow", "debt"] : bundle.asset.asset_type === "etf" ? ["expense ratio", "AUM", "holdings", "NAV", "tracking error"] : ["liquidity", "credit risk", "market risk"];
  const request = (value: string, kind: "term" | "question" = "term"): TermRequest => ({ term: value, mode: kind, bundle_id: bundle.id!, language, level, provider: settings?.provider ?? "codex" });
  const fail = (value: unknown) => setError(value instanceof Error ? value.message : "The explanation is unavailable.");

  useEffect(() => {
    if (!job?.id || !["queued", "running"].includes(job.status)) return;
    let active = true, polling = false;
    const refresh = async () => {
      if (polling) return;
      polling = true;
      try {
        const value = await api<TermJob>(`/api/jobs/${job.id}`);
        if (!active) return;
        setJob(value);
        if (value.error) setError(value.error);
        if (value.status === "completed" && value.result) {
          setProgress("");
          setAnswer(value.result);
          if (value.result.mode !== "question") setCached((previous) => ({ ...previous, [normalizeTerm(value.result!.term)]: value.result! }));
        }
      } catch (error) { if (active) fail(error); }
      finally { polling = false; }
    };
    const close = watchJob(job.id, (event) => { if (!active) return; if (event.text) setProgress(event.text); if (event.kind.startsWith("run.")) void refresh(); }, () => void refresh());
    const timer = setInterval(() => void refresh(), 2000);
    return () => { active = false; clearInterval(timer); close(); };
  }, [job?.id, job?.status]);

  async function hover(value: string) {
    const key = normalizeTerm(value);
    if (requests.current.has(key)) return;
    requests.current.add(key);
    const current = revision.current;
    try {
      const result = await api<TermJob>("/api/terms/lookup", { method: "POST", body: JSON.stringify(request(value)) });
      if (current !== revision.current) { requests.current.delete(key); return; }
      if (result.result) setCached((previous) => ({ ...previous, [key]: result.result! }));
    } catch { requests.current.delete(key); }
  }

  async function explain(value: string, kind: "term" | "question" = "term") {
    if (busy || !value.trim()) return;
    const current = ++revision.current;
    setMode(kind); setTerm(value); setSelected(""); setAnswer(undefined); setJob(undefined); setError(""); setRequesting(true); setProgress("");
    panel.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    try {
      let result = await api<TermJob>("/api/terms/lookup", { method: "POST", body: JSON.stringify(request(value, kind)) });
      if (!result.result && settings?.cloud_enabled) result = await api<TermJob>("/api/terms", { method: "POST", body: JSON.stringify(request(value, kind)) });
      if (current !== revision.current) return;
      setJob(result); setAnswer(result.result);
      if (result.result && kind === "term") setCached((previous) => ({ ...previous, [normalizeTerm(value)]: result.result! }));
      if (!result.result && result.status === "unavailable") setProgress(kind === "question" ? "No saved answer for this question and evidence version." : "No saved explanation for this evidence version. A core definition is shown when available.");
    } catch (error) { if (current === revision.current) fail(error); }
    finally { if (current === revision.current) setRequesting(false); }
  }

  function captureSelection() {
    const selection = window.getSelection();
    if (!selection || !selection.rangeCount || !content.current?.contains(selection.anchorNode) || !content.current.contains(selection.focusNode)) { setSelected(""); return; }
    const range = selection.getRangeAt(0);
    if ([...content.current.querySelectorAll("[data-local-only]")].some((node) => range.intersectsNode(node))) { setSelected(""); return; }
    setSelected(conciseSelection(selection.toString()));
  }

  return <>
    <div ref={content} onMouseUp={captureSelection} onKeyUp={captureSelection}>{children}</div>
    <section id="ticker-learning" tabIndex={-1} ref={panel} className="plain-panel term-learning" aria-labelledby="term-learning-title">
      <h2 id="term-learning-title">Understand this page</h2>
      <p>Learning context: {bundle.asset.name} ({bundle.asset.symbol}) · Evidence saved {bundle.created_at ?? "at an unknown time"}. Explanations use this saved version’s permitted evidence and original references automatically.</p>
      <p>Select words on this page, choose a core term, or type a term. Hover and keyboard focus reuse saved explanations and core definitions without generating content.</p>
      {(bundle.market || bundle.sources?.some(privateSource)) && <p>Admitted Yahoo prices, returns, valuations and analyst opinions are included with original dates and citations when you request cloud explanations. Generated interpretations do not become factual evidence.</p>}
      <div className="actions">{common.map((value) => <button type="button" key={value} disabled={busy} onMouseEnter={() => void hover(value)} onFocus={() => void hover(value)} title={cached[normalizeTerm(value)]?.explanation ?? coreDefinition(value)?.definition} onClick={() => void explain(value)}>{value}</button>)}</div>
      <label>Learning mode<select value={mode} disabled={busy} onChange={(event) => { setMode(event.target.value as "term" | "question"); setTerm(""); setAnswer(undefined); setJob(undefined); setProgress(""); setError(""); }}><option value="term">Explain a term</option><option value="question">Question about saved page</option></select></label>
      {mode === "question" && <p>Answers use only this saved page’s admitted evidence and original dates, with web research disabled. Missing or newer information requires an explicit new research request. Questions stay with this version and are not rerun when the page is refreshed.</p>}
      <form className="research-bar" onSubmit={(event) => { event.preventDefault(); void explain(term, mode); }}><label>{mode === "question" ? "Question about this saved page" : "Term to explain"}<input value={term} required maxLength={mode === "question" ? 1000 : 120} disabled={busy} onChange={(event) => { setTerm(event.target.value); setAnswer(undefined); setJob(undefined); setProgress(""); setError(""); }}/></label><button disabled={busy}>{settings?.cloud_enabled ? mode === "question" ? "Answer from saved page" : "Explain term" : "Look up saved explanation"}</button></form>
      {!settings?.cloud_enabled && <p>Online explanations are off. Core definitions and previously generated explanations work offline.</p>}
      {fallback && !answer && <div className="term-result"><h3>{fallback.term} · Core definition</h3><p>{fallback.definition}</p><p>{fallback.whyItMatters}</p><p>Common misunderstanding: {fallback.beginnerMistake}</p><p className="term-meta">Curated learning material in English. General definition; it does not describe this asset’s current figures.</p></div>}
      {answer && <div className="term-result" aria-live="polite"><h3>{answer.term}</h3><p>{answer.explanation}</p><p className="term-meta">{answer.basis === "snapshot" ? "Interpretation of this evidence version" : answer.basis === "insufficient" ? "Insufficient saved evidence · No current-data check" : "General explanation · No source citation supplied"} · {answer.language} · {answer.level} · {answer.provider}</p><p>Generated {new Date(answer.created_at!).toLocaleString()}. This explanation has not been independently verified and is never used as factual evidence.</p><div className="chip-row">{answer.source_ids?.map((id) => { const source = bundle.sources?.find((entry) => entry.id === id); return source ? <CitationChip key={id} label={source.title} href={`#${sourceRoute(bundle.id!, id)}`} citation={{ citationId: id, sourceDocumentId: id, title: source.title, publisher: source.publisher, freshnessState: "unknown" }}/> : null; })}</div></div>}
      {progress && <p role="status">{progress}</p>}
      {answer && <DeleteSavedItem key={`delete:${answer.id}`} kind="term" id={answer.id} title={`${answer.term} · ${answer.language} · ${answer.level}`} onDeleted={() => {
        const removed = answer.id;
        revision.current += 1; requests.current.clear();
        setCached((previous) => Object.fromEntries(Object.entries(previous).filter(([, value]) => value.id !== removed)));
        setAnswer(undefined); setJob(undefined); setError(""); setProgress("Saved explanation deleted. Other saved interpretations and original evidence remain available.");
      }}/>}
      {busy && <p role="status">{requesting ? "Checking saved explanations…" : "Your selected provider is preparing an explanation."}</p>}
      {job?.id && ["queued", "running"].includes(job.status) && <button onClick={() => api<TermJob>(`/api/jobs/${job.id}/cancel`, { method: "POST" }).then((value) => { setJob(value); setProgress("Explanation cancelled."); }).catch(fail)}>Cancel explanation</button>}
      {error && <p role="alert">{error}</p>}
    </section>
    {selected && !busy && <div className="term-selection-bar"><button onClick={() => void explain(selected)}>Explain “{selected}”</button><button aria-label="Dismiss term selection" onClick={() => setSelected("")}>×</button></div>}
  </>;
}
