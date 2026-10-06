import { useEffect, useRef, useState } from "react";
import { api } from "./client";
import type { ComparisonCell, ComparisonResult, ComparisonRow, ComparisonSide, EvidenceBundle, SavedResearch, Settings } from "./contracts";
import { bundleRoute, comparisonRoute, sourceRoute } from "./routes";
import { EvidenceFreshness, SourceAgeLabel } from "./EvidenceFreshness";
import { displayNumber } from "./financialSeries";

type Summary = Omit<ComparisonResult, "rows">;
const alignments: Record<ComparisonRow["alignment"], string> = {
  aligned: "Matching type, units, period and method. These figures do not establish investment suitability.",
  descriptive: "Source descriptions only; no numerical equivalence is implied.",
  missing_evidence: "Insufficient compatible evidence. No value has been filled in.",
  different_types: "Different asset types; the metrics are not directly comparable.",
  different_units: "Different units or currencies; no conversion was made.",
  different_periods: "Different dates or reporting periods; these values are not aligned.",
  different_methods: "Different calculation or sampling methods; these values are not aligned.",
  share_basis_unverified: "Cross-instrument share bases have not been reconciled.",
};
const gaps: Record<NonNullable<ComparisonCell["state"]>, string> = {
  available: "Available", missing: "Missing in this saved page", not_applicable: "Not applicable to this asset type",
  unknown_type: "Asset type is unconfirmed", conflict: "Conflicting or ambiguous latest observations; value withheld",
};
const names: Record<string, string> = { Assets: "Assets", Liabilities: "Liabilities", StockholdersEquity: "Stockholders’ equity",
  Revenues: "Revenue", RevenueFromContractWithCustomerExcludingAssessedTax: "Revenue from customer contracts, excluding tax",
  NetIncomeLoss: "Net income", NetCashProvidedByUsedInOperatingActivities: "Operating cash flow",
  EarningsPerShareDiluted: "Diluted earnings per share", WeightedAverageNumberOfDilutedSharesOutstanding: "Weighted average diluted shares" };

function rowLabel(row: ComparisonRow) {
  if (!row.id.startsWith("financial:")) return row.label;
  const [, concept, period] = row.id.split(":");
  return `${names[concept] ?? concept} · ${period}`;
}

function Cell({ cell, side }: { cell: ComparisonCell; side: ComparisonSide }) {
  return <div className="comparison-cell"><h4>{side.asset.name}</h4>
    {cell.state === "available" ? <>{cell.value != null && <p className="financial-value">{displayNumber(cell.value)} {cell.unit}</p>}{cell.text && <p>{cell.text}</p>}</>
      : <p>{gaps[cell.state ?? "missing"]}</p>}
    {(cell.start || cell.end) && <p className="ticker-meta">Original period: {cell.start ? `${cell.start} to ` : ""}{cell.end ?? "Unknown"}</p>}
    {!cell.end && cell.state === "available" && <p className="ticker-meta">Observation date not recorded.</p>}
    {cell.source_ids?.map((source, index) => <p key={source}><a href={`#${sourceRoute(side.bundle_id, source)}`}>Original source {index + 1} for {side.asset.symbol}</a></p>)}
  </div>;
}

function OriginalSources({ side }: { side: ComparisonSide }) {
  const [bundle, setBundle] = useState<EvidenceBundle>();
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void api<EvidenceBundle>(`/api/bundles/${encodeURIComponent(side.bundle_id)}`, { signal: controller.signal })
      .then((value) => { if (!controller.signal.aborted && value.id === side.bundle_id) setBundle(value); })
      .catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [side.bundle_id]);
  return <section className="plain-panel" aria-label={`Original evidence for ${side.asset.symbol}`}>
    <h3>{side.asset.name} · {side.asset.symbol}</h3><p>{side.asset.asset_type} · {side.asset.exchange ?? "Venue unknown"}</p>
    <p>Page saved: {side.saved_at}. Recorded availability: {side.state}. {side.completion === "section_checkpoint" && "Incomplete research section."}</p>
    <a href={`#${bundleRoute(side.bundle_id)}`}>Open original page for {side.asset.symbol}</a>
    <EvidenceFreshness bundleId={side.bundle_id}>
      {failed && <p>Original source details could not be read. The saved comparison remains available.</p>}
      <details><summary>Original dates and source permissions for {side.asset.symbol}</summary>
        {!failed && !bundle && <p>Reading saved source details…</p>}
        {bundle && !bundle.sources?.length && <p>No source dates are available.</p>}
        {bundle?.sources?.map((source) => <article key={source.id}><a href={`#${sourceRoute(side.bundle_id, source.id!)}`}>{source.title}</a>
          <p>{source.publisher} · Published: {source.published_at ?? "Unknown"} · As of: {source.as_of ?? "Unknown"} · Retrieved: {source.retrieved_at ?? "Unknown"}</p>
          <p>Usage: {source.usage_scope === "private_yahoo_v1" ? "Unofficial Yahoo data for personal learning; shareable exports are restricted." : source.policy}</p>
          <SourceAgeLabel sourceId={source.id!}/></article>)}
      </details>
    </EvidenceFreshness>
  </section>;
}

export function ComparisonView({ result }: { result: ComparisonResult }) {
  const hasEvidence = (row: ComparisonRow) => [row.left.state, row.right.state].some((state) => state === "available" || state === "conflict");
  function row(item: ComparisonRow) {
    return <article className="comparison-row" key={item.id} data-comparison-row={item.id}>
      <h3>{rowLabel(item)}</h3><p>{alignments[item.alignment]}</p>
      <div className="comparison-columns"><Cell cell={item.left} side={result.left}/><Cell cell={item.right} side={result.right}/></div>
    </article>;
  }
  return <section className="comparison-result" aria-label="Saved comparison">
    <h2>{result.left.asset.symbol} and {result.right.asset.symbol}</h2>
    <p>Comparison saved: {result.created_at}. Opening this result does not refresh or recalculate its evidence.</p>
    <p>These are historical observations and source descriptions. Differences in business, instrument structure and accounting limit comparisons; no investment winner is selected.</p>
    <p>Returns retain their original dates and adjustment method. Total return estimates use provider-adjusted prices, not independently reconstructed distributions. Valuations are supplied provider measures with distinct sampling periods.</p>
    <div className="comparison-columns"><OriginalSources key={result.left.bundle_id} side={result.left}/><OriginalSources key={result.right.bundle_id} side={result.right}/></div>
    {result.rows.filter(hasEvidence).map(row)}
    {!result.rows.some(hasEvidence) && <p>No admitted comparable observations are available in these pages.</p>}
    <details className="comparison-gaps"><summary>Other dimensions and missing evidence ({result.rows.filter((item) => !hasEvidence(item)).length})</summary>
      {result.rows.filter((item) => !hasEvidence(item)).map(row)}
    </details>
  </section>;
}

export function Comparisons({ library, saved, settings, resultId, initialLeft }: {
  library: EvidenceBundle[]; saved: SavedResearch[]; settings?: Settings; resultId: string | null; initialLeft: string | null;
}) {
  const [left, setLeft] = useState(initialLeft ?? ""), [right, setRight] = useState("");
  const [results, setResults] = useState<Summary[]>([]), [result, setResult] = useState<ComparisonResult>();
  const [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(() => typeof navigator === "undefined" || navigator.onLine);
  const submitting = useRef(false);
  useEffect(() => {
    const update = () => setConnected(navigator.onLine);
    window.addEventListener("online", update); window.addEventListener("offline", update);
    return () => { window.removeEventListener("online", update); window.removeEventListener("offline", update); };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void api<Summary[]>("/api/comparisons", { signal: controller.signal }).then((items) => {
      if (!controller.signal.aborted) setResults(items);
    }).catch(() => { if (!controller.signal.aborted) setError("Saved comparison list could not be read."); });
    if (resultId) void api<ComparisonResult>(`/api/comparisons/${encodeURIComponent(resultId)}`, { signal: controller.signal }).then((value) => {
      if (!controller.signal.aborted && value.id === resultId) setResult(value);
    }).catch(() => { if (!controller.signal.aborted) setError("This saved comparison could not be read. No new comparison was generated."); });
    return () => controller.abort();
  }, [resultId]);
  const choices = new Map<string, string>();
  for (const entry of library) if (entry.id) choices.set(entry.id, `${entry.asset.name} · ${entry.asset.symbol} · Page saved ${entry.created_at}`);
  for (const entry of saved) if (!choices.has(entry.bundle_id)) choices.set(entry.bundle_id, `Bookmarked: ${entry.title} · ${entry.bundle_id}`);
  if (initialLeft && !choices.has(initialLeft)) choices.set(initialLeft, `Selected original page · ${initialLeft}`);
  const online = !!settings?.cloud_enabled && connected;
  async function generate() {
    if (submitting.current || !online || !left || !right || left === right) return;
    submitting.current = true; setBusy(true); setError("");
    try {
      const value = await api<ComparisonResult>("/api/comparisons", { method: "POST", body: JSON.stringify({ left_bundle_id: left, right_bundle_id: right }) });
      location.hash = comparisonRoute(value.id);
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Comparison could not be saved."); }
    finally { submitting.current = false; setBusy(false); }
  }
  return <section className="comparisons"><h1>Compare saved evidence</h1>
    <p>Select two original pages. Missing data stays missing; research another asset separately to establish its identity and evidence first.</p>
    {!online && <p role="status">Offline: previously generated comparisons remain readable. New comparisons are disabled.</p>}
    {error && <p role="alert">{error}</p>}
    <form onSubmit={(event) => { event.preventDefault(); void generate(); }} className="plain-panel">
      <div className="comparison-columns">{(["Left", "Right"] as const).map((label) => <label key={label}>{label} saved page
        <select disabled={busy} value={label === "Left" ? left : right} onChange={(event) => label === "Left" ? setLeft(event.target.value) : setRight(event.target.value)}>
          <option value="">Choose a saved page</option>{[...choices].map(([id, title]) => <option key={id} value={id}>{title}</option>)}
        </select></label>)}</div>
      <button disabled={busy || !online || !left || !right || left === right}>Create and save comparison</button>
    </form>
    <nav aria-label="Saved comparisons">{results.map((item) => <a key={item.id} href={`#${comparisonRoute(item.id)}`}>{item.left.asset.symbol} and {item.right.asset.symbol} · {item.created_at}</a>)}</nav>
    {!results.length && <p>No comparisons have been saved.</p>}
    {result ? <ComparisonView key={result.id} result={result}/> : resultId && !error && <p>Reading saved comparison…</p>}
  </section>;
}
