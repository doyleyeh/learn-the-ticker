import { useEffect, useRef, useState } from "react";
import { api, downloadReport } from "./client";
import type { DatedItem, EvidenceBundle, ResearchReport, SavedResearch, Settings } from "./contracts";
import { bundleRoute, reportRoute, sourceRoute } from "./routes";
import { EvidenceView } from "./TickerDashboard";
import { SnapshotStatus } from "./EvidenceFreshness";

type Summary = Pick<ResearchReport, "id" | "created_at" | "bundle_id" | "asset" | "evidence_saved_at">;

export function DatedContext({ report }: { report: ResearchReport }) {
  const { focus } = report, { window } = focus;
  function items(rows: DatedItem[]) {
    return rows.length ? <ul>{rows.map((item) => <li key={item.event_id} className="plain-panel">
      <h4>{item.title} · Published {item.published}</h4>
      <p>Effective/reporting date: {item.effective ?? "Unknown"}. Date verified through the original SEC filing index.</p>
      <p>{item.text ?? "No admitted narrative quotation accompanies this filing."}</p>
      <a href={`#${sourceRoute(report.bundle_id, item.source_id)}`}>Original source for {item.title} on {item.published}</a>
    </li>)}</ul> : <p>No qualifying items are available in this saved page.</p>;
  }
  return <section className="dated-context" aria-label="Dated report context">
    <h2>Weekly News Focus</h2><p>U.S. Eastern date: {window.as_of}. Last completed week: {window.previous_start} through {window.previous_end}.</p>
    <p>{window.current_start ? `Current week through yesterday: ${window.current_start} through ${window.current_end}.` : "The current week is empty on Monday."}</p>
    <p>Partial coverage: independently verified filings in the original page only. Missing items do not establish that no developments occurred. Source publication dates stay separate from reporting periods.</p>
    <section aria-label="Weekly items"><h3>Weekly items ({focus.weekly?.length ?? 0})</h3>{items(focus.weekly ?? [])}</section>
    {focus.earlier_requested && <section aria-label="Earlier context"><h3>Earlier context</h3>
      <p>Fewer than three weekly items: available earlier evidence from {window.earlier_start} through {window.earlier_end}. Excluded from weekly counts and analysis.</p>{items(focus.earlier ?? [])}</section>}
    <section aria-label="Weekly analysis"><h3>Weekly analysis — app reading guide</h3>
      <p>{report.reading_guide ?? "Fewer than two verified weekly items. Weekly analysis is unavailable; the historical report remains usable."}</p>
      {report.reading_guide && <p>A fixed reading guide based on the dated selection; no AI synthesis or fresh retrieval.</p>}
      <div className="chip-row">{report.guide_source_ids?.map((id, index) => <a key={id} href={`#${sourceRoute(report.bundle_id, id)}`}>Guide source {index + 1}</a>)}</div>
    </section>
  </section>;
}

function ReportView({ report }: { report: ResearchReport }) {
  const [bundle, setBundle] = useState<EvidenceBundle>(), [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void api<EvidenceBundle>(`/api/bundles/${encodeURIComponent(report.bundle_id)}`, { signal: controller.signal })
      .then((value) => { if (!controller.signal.aborted && value.id === report.bundle_id) setBundle(value); })
      .catch(() => { if (!controller.signal.aborted) setError("Original page could not be read. The stored report context remains available; no new research was requested."); });
    return () => controller.abort();
  }, [report.bundle_id]);
  return <section aria-label="Saved historical report"><h2>{report.asset.name} · Historical report</h2>
    <p>Report saved: {report.created_at}. Original page saved: {report.evidence_saved_at}.</p>
    <p>This report preserves selected historical evidence. It is not a reconstruction of what was known on a past date. Opening it does not refresh evidence or regenerate analysis.</p>
    <a href={`#${bundleRoute(report.bundle_id)}`}>Open report’s original page</a>
    <div className="actions">{(["markdown", "json"] as const).map((format) => <button key={format} onClick={() => void downloadReport(report.id!, format).catch(() => setError("Report export failed. Your saved report is unchanged."))}>Export report {format === "json" ? "JSON" : "Markdown"}</button>)}</div>
    {error && <p role="alert">{error}</p>}
    <DatedContext report={report}/>
    {bundle ? <><SnapshotStatus bundle={bundle}/><EvidenceView bundle={bundle}/></> : !error && <p>Reading original saved evidence…</p>}
  </section>;
}

export function Reports({ library, saved, settings, reportId, initialBundle }: {
  library: EvidenceBundle[]; saved: SavedResearch[]; settings?: Settings; reportId: string | null; initialBundle: string | null;
}) {
  const [selected, setSelected] = useState(initialBundle ?? ""), [reports, setReports] = useState<Summary[]>([]);
  const [report, setReport] = useState<ResearchReport>(), [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(() => typeof navigator === "undefined" || navigator.onLine);
  const submitting = useRef(false);
  useEffect(() => {
    const update = () => setConnected(navigator.onLine);
    window.addEventListener("online", update); window.addEventListener("offline", update);
    return () => { window.removeEventListener("online", update); window.removeEventListener("offline", update); };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void api<Summary[]>("/api/reports", { signal: controller.signal }).then((value) => { if (!controller.signal.aborted) setReports(value); })
      .catch(() => { if (!controller.signal.aborted) setError("Saved report list could not be read."); });
    if (reportId) void api<ResearchReport>(`/api/reports/${encodeURIComponent(reportId)}`, { signal: controller.signal }).then((value) => { if (!controller.signal.aborted && value.id === reportId) setReport(value); })
      .catch(() => { if (!controller.signal.aborted) setError("This saved report could not be read. No new report was generated."); });
    return () => controller.abort();
  }, [reportId]);
  const choices = new Map<string, string>();
  for (const page of library) if (page.id && page.completion !== "section_checkpoint") choices.set(page.id, `${page.asset.name} · ${page.created_at}`);
  for (const page of saved) if (!choices.has(page.bundle_id)) choices.set(page.bundle_id, `Bookmarked: ${page.title}`);
  if (initialBundle && !choices.has(initialBundle)) choices.set(initialBundle, `Selected original page · ${initialBundle}`);
  const online = !!settings?.cloud_enabled && connected;
  async function save() {
    if (!online || !selected || submitting.current) return;
    submitting.current = true; setBusy(true); setError("");
    try {
      const value = await api<ResearchReport>("/api/reports", { method: "POST", body: JSON.stringify({ bundle_id: selected }) });
      location.hash = reportRoute(value.id);
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Report could not be saved."); }
    finally { submitting.current = false; setBusy(false); }
  }
  return <section className="reports"><h1>Historical reports</h1>
    <p>Save a fixed page with a separate dated news selection. No recent-news minimum is required. Research or refresh the asset separately when you need newer evidence.</p>
    {!online && <p role="status">Offline: saved reports and exports remain available. New reports are disabled.</p>}
    {error && <p role="alert">{error}</p>}
    <form className="plain-panel" onSubmit={(event) => { event.preventDefault(); void save(); }}>
      <label>Report saved page<select disabled={busy} value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">Choose original page</option>{[...choices].map(([id, title]) => <option key={id} value={id}>{title}</option>)}</select></label>
      <button disabled={!online || !selected || busy}>Save dated report</button>
    </form>
    <nav aria-label="Saved reports">{reports.map((item) => <a key={item.id} href={`#${reportRoute(item.id)}`}>{item.asset.symbol} · {item.created_at}</a>)}</nav>
    {!reports.length && <p>No dated reports have been saved.</p>}
    {report ? <ReportView key={report.id} report={report}/> : reportId && !error && <p>Reading saved report…</p>}
  </section>;
}
