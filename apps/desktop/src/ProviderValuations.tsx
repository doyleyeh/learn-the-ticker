import { useMemo, useState } from "react";
import type { EvidenceBundle, MarketValuations, Source, ValuationObservation } from "./contracts";
import { CitationChip } from "../components/CitationChip";
import { admittedMarket } from "./marketPresentation";
import { decimalInteger, displayNumber } from "./financialSeries";
import { sourceRoute } from "./routes";

export const valuationLabels: Record<ValuationObservation["metric"], string> = {
  MarketCap: "Market capitalization", EnterpriseValue: "Enterprise value", PeRatio: "Trailing P/E",
  PsRatio: "Price/sales", PbRatio: "Price/book", EnterprisesValueRevenueRatio: "EV/revenue", EnterprisesValueEBITDARatio: "EV/EBITDA",
};
const samplingLabels = { quarterly: "Quarterly samples", annual: "Annual samples", trailing: "Trailing-series samples" };
const periodTypes = { quarterly: "3M", annual: "12M", trailing: "TTM" };
const monetary = (metric: string) => metric === "MarketCap" || metric === "EnterpriseValue";

export function admittedValuations(bundle: EvidenceBundle) {
  const market = admittedMarket(bundle)?.market, data = market?.valuations;
  const source = bundle.sources?.find((item) => item.id === data?.source_id);
  if (!data || !source?.verified || data.method !== "yahoo-reported-valuation-v1" || market?.valuation_gap
    || source.asset_id !== bundle.asset.id || source.usage_scope !== "private_yahoo_v1" || source.provenance !== "market_adapter"
    || source.policy !== "metadata_only" || source.url !== `https://finance.yahoo.com/quote/${bundle.asset.symbol}/key-statistics/`
    || !data.points.length || data.points.length > 600) return undefined;
  const seen = new Set<string>();
  for (const point of data.points) {
    const key = `${point.metric}:${point.sampling}:${point.date}`;
    if (seen.has(key) || !(point.metric in valuationLabels) || point.period_type !== periodTypes[point.sampling]
      || !/^\d{4}-\d{2}-\d{2}$/.test(point.date) || !Number.isFinite(Date.parse(point.date))
      || point.date < data.requested_start || point.date > data.requested_end
      || (point.currency != null && point.currency !== "USD")
      || (point.value != null && (decimalInteger(point.value) === undefined || point.reason != null || (monetary(point.metric) && point.currency !== "USD")))
      || (point.value == null && !point.reason)) return undefined;
    seen.add(key);
  }
  return { data, source };
}

function displayPoint(point?: ValuationObservation) {
  if (!point) return "Unavailable — no retained observation.";
  if (point.value == null) return point.reason === "currency_missing" ? "Unavailable — source currency missing." : "Unavailable — source value missing.";
  return `${displayNumber(point.value)} ${monetary(point.metric) ? "USD" : "×"}`;
}

export function ProviderValuations({ bundle }: { bundle: EvidenceBundle }) {
  const admitted = useMemo(() => admittedValuations(bundle), [bundle]);
  if (!admitted) return <section className="plain-panel" aria-label="Provider valuation measures" data-local-only={Boolean(bundle.market) || undefined}>
    <h3>Provider valuation measures</h3><p className="source-gap-note">{bundle.market?.valuations ? "Valuation evidence could not be validated for display." : bundle.market?.valuation_gap === "not_selected" ? "Valuation source was not selected." : bundle.market?.valuation_gap === "source_unavailable" ? "Valuation retrieval was unavailable; no automatic retry was made." : "No provider valuation observations are retained in this version."} Opening saved research does not fetch or calculate new values.</p>
  </section>;
  return <RetainedValuations key={bundle.id} bundle={bundle} {...admitted}/>;
}

function RetainedValuations({ bundle, data, source }: { bundle: EvidenceBundle; data: MarketValuations; source: Source }) {
  const [metric, setMetric] = useState<ValuationObservation["metric"]>("PeRatio");
  const [sampling, setSampling] = useState<ValuationObservation["sampling"]>("quarterly");
  const rows = useMemo(() => data.points.filter((point) => point.metric === metric && point.sampling === sampling).sort((a, b) => b.date.localeCompare(a.date)), [data.points, metric, sampling]);
  const limit = sampling === "annual" ? 5 : 12;
  return <section className="plain-panel provider-valuations" aria-label="Provider valuation measures" data-evidence-layer="numeric">
    <p className="eyebrow">Provider calculations · Private experimental mode</p><h3>Provider valuation measures</h3>
    <p>Reported by Yahoo Finance through unofficial yfinance. These are supplied calculations, not issuer-reported figures or ratios recalculated by this app.</p>
    <p className="ticker-meta">Retrieved {source.retrieved_at} · Publication date {source.published_at ?? "unknown"}. Each observation has its own as-of date below; retrieval does not make it current.</p>
    <p>These saved observations and citations can support consented explanations through your selected AI provider. Same-user backups retain them; shareable exports omit them.</p>
    <CitationChip href={`#${sourceRoute(bundle.id!, source.id!)}`} label="Inspect original valuation evidence" citation={{ citationId: source.id!, sourceDocumentId: source.id!, title: source.title, publisher: source.publisher, freshnessState: "unknown" }}/>
    <h4>Latest retained trailing-series observations</h4><dl className="ticker-facts">{Object.entries(valuationLabels).map(([name, label]) => {
      const latest = data.points.filter((point) => point.metric === name && point.sampling === "trailing").sort((a, b) => b.date.localeCompare(a.date))[0];
      return <div key={name}><dt>{label}</dt><dd>{displayPoint(latest)}{latest && <><br/>As of {latest.date}</>}</dd></div>;
    })}</dl>
    <div className="financial-period"><label>Valuation metric<select value={metric} onChange={(event) => setMetric(event.target.value as ValuationObservation["metric"])}>{Object.entries(valuationLabels).map(([name, label]) => <option value={name} key={name}>{label}</option>)}</select></label>
      <label>Valuation sampling<select value={sampling} onChange={(event) => setSampling(event.target.value as ValuationObservation["sampling"])}>{Object.entries(samplingLabels).map(([name, label]) => <option value={name} key={name}>{label}</option>)}</select></label></div>
    <p>{rows.length} retained observations for {valuationLabels[metric]} · Showing up to {limit}, newest first. Requested {data.requested_start} through {data.requested_end}.</p>
    {rows.length < limit && <p className="source-gap-note">Fewer than {limit} observations were supplied. Missing periods are not filled.</p>}
    {rows.length ? <div className="market-table-scroll" tabIndex={0} role="region" aria-label="Dated valuation observations"><table><thead><tr><th scope="col">As of</th><th scope="col">Provider value</th><th scope="col">Reported period label</th></tr></thead><tbody>{rows.slice(0, limit).map((point) => <tr key={point.date}><th scope="row">{point.date}</th><td>{displayPoint(point)}</td><td>{point.period_type}</td></tr>)}</tbody></table></div> : <p>No observations for this metric and sampling.</p>}
    <details><summary>Valuation definitions and limitations</summary><p>Trailing P/E uses trailing earnings; forward estimates are not included. Quarterly or annual describes the supplied sampling, not a change to the ratio's earnings denominator. Market capitalization and enterprise value are monetary amounts; ratios are multiples. A provider's period label is retained without interpreting it as the exact underlying financial interval.</p><p>The provider's complete adjustment and earnings methodology has not been independently reconstructed. Historical values may reflect later revisions; these are not proven point-in-time records. No interpolation, currency conversion or combination with SEC EPS is performed. Different providers may use different definitions. Method: {data.method}.</p></details>
  </section>;
}
