import { useMemo } from "react";
import type { AnalystEstimate, EvidenceBundle } from "./contracts";
import { CitationChip } from "../components/CitationChip";
import { admittedMarket } from "./marketPresentation";
import { decimalInteger, displayNumber } from "./financialSeries";
import { sourceRoute } from "./routes";

const periods = { "0q": "Current quarter", "+1q": "Next quarter", "0y": "Current year", "+1y": "Next year" };
const gaps = { period_missing: "Forecast date missing", currency_missing: "Source currency missing", value_missing: "Source value missing" };

export function admittedEstimates(bundle: EvidenceBundle) {
  const market = admittedMarket(bundle)?.market, data = market?.estimates;
  const source = bundle.sources?.find((s) => s.id === data?.source_id);
  if (!data || !source?.verified || market?.estimate_gap || data.kind !== "analyst_opinion"
    || data.method !== "yahoo-consensus-estimates-v1" || source.asset_id !== bundle.asset.id
    || source.provenance !== "market_adapter" || source.usage_scope !== "private_yahoo_v1"
    || source.policy !== "metadata_only" || source.url !== `https://finance.yahoo.com/quote/${bundle.asset.symbol}/analysis/`
    || source.as_of != null || source.published_at != null || !data.points.length || data.points.length > 8) return undefined;
  const seen = new Set<string>();
  for (const p of data.points) {
    const key = `${p.period}:${p.metric}`, values = [p.average, p.low, p.high];
    const reason = p.period_end == null ? "period_missing" : p.currency == null ? "currency_missing" : values.every((v) => v == null) ? "value_missing" : null;
    const unit = p.currency === "USD" ? p.metric === "eps" ? "USD/share" : "USD" : null;
    if (seen.has(key) || !(p.period in periods) || !["eps", "revenue"].includes(p.metric)
      || (p.period_end != null && (!/^\d{4}-\d{2}-\d{2}$/.test(p.period_end) || !Number.isFinite(Date.parse(p.period_end))))
      || (p.currency != null && p.currency !== "USD") || (p.unit ?? null) !== unit || (p.reason ?? null) !== reason
      || (reason != null && values.some((v) => v != null))
      || values.some((v) => v != null && decimalInteger(v) === undefined)
      || (p.analysts != null && (!Number.isInteger(p.analysts) || p.analysts < 0 || p.analysts > 10000))) return undefined;
    seen.add(key);
  }
  if (data.points.some((p) => !seen.has(`${p.period}:${p.metric === "eps" ? "revenue" : "eps"}`))) return undefined;
  return { data, source };
}

function amount(point: AnalystEstimate, value?: string | null) {
  if (point.reason) return `Unavailable — ${gaps[point.reason]}.`;
  return value == null ? "Unavailable" : `${displayNumber(value)} ${point.unit}`;
}

export function AnalystInsights({ bundle }: { bundle: EvidenceBundle }) {
  const admitted = useMemo(() => admittedEstimates(bundle), [bundle]);
  if (!admitted) return <div className="plain-panel"><p className="source-gap-note">{bundle.market?.estimates ? "Analyst evidence could not be validated for display." : bundle.market?.estimate_gap === "not_selected" ? "Analyst source was not selected." : bundle.market?.estimate_gap === "source_unavailable" ? "Analyst retrieval was unavailable; no automatic retry was made." : "Unavailable — this snapshot has no qualified analyst estimates or outlooks."}</p><p>External estimates are opinions about the future, separate from reported results. Missing estimates are not inferred from prices or generated explanations.</p></div>;
  const { data, source } = admitted;
  return <div className="plain-panel analyst-insights" data-evidence-layer="numeric">
    <p className="eyebrow">Third-party opinions · Private experimental mode</p><h3>EPS and revenue estimates</h3>
    <p>Consensus estimates supplied by Yahoo Finance through unofficial yfinance. These are opinions, not reported results, app calculations or generated predictions. Underlying contributing analysts are not identified by this dataset.</p>
    <p className="ticker-meta">Retrieved {source.retrieved_at} · Estimate publication / as-of time unknown. Forecast period ends describe the period being estimated, not when the estimate was published.</p>
    <CitationChip label="Yahoo Finance estimates" href={`#${sourceRoute(bundle.id!, source.id!)}`} citation={{ citationId: source.id!, sourceDocumentId: source.id!, title: source.title, publisher: source.publisher, freshnessState: "unknown" }}/>
    <p>Current / next are the provider's labels at retrieval. Saved estimates may have changed; opening this page does not refresh them.</p>
    {Object.entries(periods).map(([period, label]) => {
      const rows = data.points.filter((p) => p.period === period);
      return <section key={period} aria-label={`${label} estimates`}><h4>{label} ({period})</h4>
        {rows.length ? <div className="market-table-scroll" tabIndex={0} role="region" aria-label={`${label} estimate table`}><table><thead><tr><th scope="col">Metric / forecast end</th><th scope="col">Average</th><th scope="col">Low</th><th scope="col">High</th><th scope="col">Analysts</th></tr></thead><tbody>{rows.map((p) => <tr key={p.metric}><th scope="row">{p.metric === "eps" ? "EPS" : "Revenue"}<br/>{p.period_end ?? "Forecast date unknown"}</th><td>{amount(p, p.average)}</td><td>{amount(p, p.low)}</td><td>{amount(p, p.high)}</td><td>{p.analysts ?? "Unknown"}</td></tr>)}</tbody></table></div> : <p className="source-gap-note">No retained estimates for this period.</p>}
      </section>;
    })}
    <details><summary>Estimate definitions and limitations</summary><p>EPS is earnings per share; revenue is a monetary amount. Average, low, high and analyst counts are supplied for each metric without recalculation or currency conversion. EPS share/adjustment methodology has not been independently reconstructed. Estimates may change and may differ from eventual results. Missing values remain unavailable; no growth rate or historical consensus series is inferred.</p></details>
  </div>;
}
