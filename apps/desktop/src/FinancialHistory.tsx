import { useId, useMemo, useState } from "react";
import type { EvidenceBundle, FinancialObservation, Source } from "./contracts";
import { CitationChip } from "../components/CitationChip";
import { FreshnessLabel } from "../components/FreshnessLabel";
import { sourceRoute } from "./routes";
import { chartGeometry, concepts, displayNumber, financialSeries, gapLabel, type FinancialSeries } from "./financialSeries";

const periodLabels = { annual: "Annual periods", quarter: "Quarterly periods", instant: "Point-in-time observations", other_duration: "Other durations" };

export function FinancialHistory({ bundle }: { bundle: EvidenceBundle }) {
  const { series, sources, excluded } = useMemo(() => financialSeries(bundle), [bundle]);
  return <section className="plain-panel financial-history" aria-labelledby="financial-history-heading" data-evidence-layer="numeric">
    <h2 id="financial-history-heading">Financial history</h2>
    <p>Reported issuer observations retain their original units and dates. They describe the business, not a stock price or a forecast.</p>
    {!bundle.financials ? <p className="source-gap-note">Unavailable — this snapshot has no independently admitted financial observations for this asset.</p> : <>
      <p>Issuer: {bundle.financials.issuer.name} · CIK {bundle.financials.issuer.identifiers?.cik}</p>
      <FreshnessLabel label="Identity and issuer association checked" value={bundle.financials.checked_at} state="partial"/>
      <p>Historical observations. A recent retrieval does not make an older reporting period current. “Latest retained” means the most recent filing version in this saved snapshot.</p>
      <p>Default view: up to five annual periods, twelve quarters or twenty point-in-time observations. All retained filing versions remain available below each series.</p>
      {excluded > 0 && <p className="error" role="status">Some observations are hidden because their source or numeric reference could not be validated for display.</p>}
      {series.length === 0 && <p className="source-gap-note">Insufficient evidence — no supported series is available.</p>}
      {series.map((value, index) => <SeriesPanel key={`${bundle.id}:${value.key}`} series={value} bundle={bundle} sources={sources} initiallyOpen={index === 0}/>)}
      {!!bundle.financials.gaps?.length && <details><summary>Evidence gaps ({bundle.financials.gaps.length})</summary><ul>{bundle.financials.gaps.map((gap) => <li key={gap}>{gapLabel(gap)}</li>)}</ul></details>}
    </>}
    <section className="financial-unavailable" aria-label="Price and return availability"><h3>Price history and returns</h3>
      <p>Five-year daily price history: unavailable in this snapshot.</p>
      <p>Price return: unavailable — independently verified, corporate-action-compatible prices are required.</p>
      <p>Total return: unavailable — compatible prices, distributions and a stated reinvestment method are required. Price return does not include distributions.</p>
      <p>Historical valuation: unavailable — price and financial inputs must refer to compatible dates, units and share bases.</p>
    </section>
  </section>;
}

function SeriesPanel({ series, bundle, sources, initiallyOpen }: { series: FinancialSeries; bundle: EvidenceBundle; sources: Map<string, Source>; initiallyOpen: boolean }) {
  const [open, setOpen] = useState(initiallyOpen);
  const [history, setHistory] = useState(false);
  const [historyPage, setHistoryPage] = useState(0);
  const rows = [...series.rows].reverse();
  const pages = Math.max(1, Math.ceil(rows.length / 20));
  const chartAllowed = series.period !== "other_duration" && !["us-gaap:EarningsPerShareDiluted", "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"].includes(series.concept);
  return <details className="financial-series" open={open} onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>{concepts[series.concept].label} · {series.unit} · {periodLabels[series.period]} · {series.points.length} retained periods</summary>
    {open && <>
      <p>{concepts[series.concept].description}</p><p className="financial-concept">Source concept: {series.concept}</p>
      {series.withheld > 0 && <p className="error">{series.withheld} period(s) withheld from the chart and latest values because no single unconflicted current version is available. Inspect filing history below.</p>}
      {series.points.length === 0 ? <p>Insufficient evidence for a trend. Conflicted or superseded figures do not supply chart values.</p> : <>
        {chartAllowed ? <ObservationChart series={series}/> : <p>Trend chart unavailable: {series.period === "other_duration" ? "these periods have nonstandard or year-to-date durations" : "independent corporate-action compatibility has not been established for these share-based figures"}. Original observations remain readable below.</p>}
        <h3>Latest retained values</h3>
        <div className="financial-observations">{series.points.map(({ row, citations }) => <article key={row.id}>
          <ObservationValue row={row}/>
          {citations.map((item) => <ObservationCitation key={item.id} row={item} bundle={bundle} source={sources.get(item.source_id)!}/>)}
        </article>)}</div>
      </>}
      <details open={history} onToggle={(event) => setHistory(event.currentTarget.open)}><summary>All retained filing versions ({rows.length})</summary>
        {history && <><p>Superseded and conflicting values are preserved for inspection; they are excluded from latest values and charts. Reported fiscal labels belong to the filing and may describe a comparative observation.</p>
          <div className="financial-observations">{rows.slice(historyPage * 20, (historyPage + 1) * 20).map((row) => <article key={row.id}>
            <p className="state-pill">{row.revision === "current" ? "Latest retained version" : row.revision === "conflict" ? "Unresolved conflict" : "Superseded version"}</p>
            <ObservationValue row={row}/><ObservationCitation row={row} bundle={bundle} source={sources.get(row.source_id)!}/>
            <p>Filing fiscal label: {row.reported_fiscal_year} {row.reported_fiscal_period}</p>
            {!!row.supersedes?.length && <p>Replaces {row.supersedes.length} retained earlier observation(s).</p>}
          </article>)}</div>
          {pages > 1 && <nav aria-label="Filing history pages"><button disabled={historyPage === 0} onClick={() => setHistoryPage(historyPage - 1)}>Previous filings</button><p aria-live="polite">Page {historyPage + 1} of {pages}</p><button disabled={historyPage + 1 === pages} onClick={() => setHistoryPage(historyPage + 1)}>Next filings</button></nav>}
        </>}
      </details>
    </>}
  </details>;
}

function ObservationValue({ row }: { row: FinancialObservation }) {
  return <><p>{row.start ? `${row.start} through ${row.end}` : `As of ${row.end}`}</p><p className="financial-value">{displayNumber(row.value)} <span>{row.unit}</span></p></>;
}

function ObservationCitation({ row, bundle, source }: { row: FinancialObservation; bundle: EvidenceBundle; source: Source }) {
  return <div className="financial-citation"><p>Filed {row.filed} · {row.form} · {row.accession}</p><p>Retrieved {source.retrieved_at ?? "Unknown"} · Permission: {source.policy?.replaceAll("_", " ")}</p>
    <CitationChip href={`#${sourceRoute(bundle.id!, row.source_id)}`} label="Inspect original evidence" citation={{ citationId: row.source_id, sourceDocumentId: row.source_id, title: source.title, publisher: source.publisher, freshnessState: "unknown" }}/>
  </div>;
}

function ObservationChart({ series }: { series: FinancialSeries }) {
  const id = useId();
  const geometry = chartGeometry(series.points);
  const width = 640, left = 108, plotWidth = 500, rowHeight = 34;
  const height = series.points.length * rowHeight + 30;
  const x = (position: number) => left + position * plotWidth / 100;
  return <figure className="financial-chart"><figcaption>{concepts[series.concept].label} · {series.unit}. Bars start at zero. Separate reported periods; gaps are not filled. Exact values and citations follow.</figcaption>
    <svg role="img" aria-labelledby={`${id}-title ${id}-desc`} viewBox={`0 0 ${width} ${height}`}>
      <title id={`${id}-title`}>{concepts[series.concept].label} by reported period</title>
      <desc id={`${id}-desc`}>Bars start at zero and use one concept, unit and period type. Dates label each period end. Only latest retained unconflicted observations are plotted.</desc>
      <line x1={x(geometry.zero)} x2={x(geometry.zero)} y1="10" y2={height - 15} stroke="currentColor"/>
      {series.points.map(({ row }, index) => {
        const position = geometry.positions[index], y = 15 + index * rowHeight;
        return <g key={row.id}><text x="0" y={y + 17}>{row.end}</text><rect x={Math.min(x(position), x(geometry.zero))} y={y} width={Math.abs(position - geometry.zero) * plotWidth / 100} height="23" fill={row.value.startsWith("-") ? "#9e4a37" : "#176854"}><title>{row.start ?? "Instant"} through {row.end}: {row.value} {row.unit}; filed {row.filed}</title></rect></g>;
      })}
    </svg>
  </figure>;
}
