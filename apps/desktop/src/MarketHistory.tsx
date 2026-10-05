import { useId, useMemo, useState } from "react";
import type { EvidenceBundle, MarketBar, MarketEvidence, Source } from "./contracts";
import { CitationChip } from "../components/CitationChip";
import { PriceHistoryAvailability } from "./FinancialHistory";
import { decimalInteger, displayNumber } from "./financialSeries";
import { admittedMarket, chartRows, chartWindows, priceGeometry, returnGaps, returnLabels, type ChartWindow } from "./marketPresentation";
import { sourceRoute } from "./routes";

export function MarketHistory({ bundle }: { bundle: EvidenceBundle }) {
  const admitted = useMemo(() => admittedMarket(bundle), [bundle]);
  if (!admitted) return <div className="plain-panel"><p>Quote: unavailable. Quote time, market session and delay are unknown.</p>{bundle.market && <p className="error">Price evidence could not be validated for display.</p>}<PriceHistoryAvailability/></div>;
  return <PrivateHistory key={bundle.id} bundle={bundle} {...admitted}/>;
}

function PrivateHistory({ bundle, market, source }: { bundle: EvidenceBundle; market: MarketEvidence; source: Source }) {
  const [window, setWindow] = useState<ChartWindow>("5y");
  const [page, setPage] = useState(0), [actionPage, setActionPage] = useState(0);
  const rows = useMemo(() => chartRows(market.bars, window), [market.bars, window]);
  const latest = market.bars.at(-1)!;
  const previous = market.bars.at(-2);
  const descending = [...rows].reverse(), actions = [...(market.actions ?? [])].reverse();
  const pages = Math.max(1, Math.ceil(rows.length / 20)), actionPages = Math.max(1, Math.ceil(actions.length / 20));
  return <div className="plain-panel market-history" data-evidence-layer="numeric">
    <p className="eyebrow">Historical prices · Private experimental mode</p>
    <h3>Latest retained daily close</h3><p className="market-close">{displayNumber(latest.close)} <span>{market.currency}</span></p>
    <p>As of {latest.date} · {market.exchange_label} · {market.timezone}</p>
    <p>Historical snapshot, not a current quote. Live session, after-hours price and quote delay are unavailable. Refresh evidence to check for newer observations.</p>
    <p className="ticker-meta">Yahoo Finance via unofficial yfinance · Retrieved {source.retrieved_at} · Publication date {source.published_at ?? "unknown"}</p>
    <p>For personal learning. With cloud research enabled, these saved values and citations can support explanations from your selected AI provider. Same-user backups retain them; shareable exports omit them.</p>
    <CitationChip href={`#${sourceRoute(bundle.id!, source.id!)}`} label="Inspect original price evidence" citation={{ citationId: source.id!, sourceDocumentId: source.id!, title: source.title, publisher: source.publisher, freshnessState: "unknown" }}/>
    <section aria-label="Retained daily quote fields">
      <h3>Daily snapshot · {latest.date}</h3>
      <dl className="ticker-facts">
        <div><dt>Open</dt><dd>{displayNumber(latest.open)} {market.currency}</dd></div>
        <div><dt>Low–high</dt><dd>{displayNumber(latest.low)}–{displayNumber(latest.high)} {market.currency}</dd></div>
        <div><dt>Volume (provider-reported)</dt><dd>{displayNumber(latest.volume)}</dd></div>
        <div><dt>Preceding retained close</dt><dd>{previous ? <>{displayNumber(previous.close)} {market.currency}<br/>{previous.date}</> : "Unavailable — no earlier observation retained."}</dd></div>
      </dl>
      <p className="ticker-meta">Prices use the same split-adjusted basis as the chart. The preceding observation may not be the previous trading session. Bid/ask, live and after-hours quotes are unavailable in daily history.</p>
    </section>
    <label className="financial-period">Chart period<select value={window} onChange={(event) => { setWindow(event.target.value as ChartWindow); setPage(0); }}>{Object.entries(chartWindows).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    <p>{rows.length} retained daily observations · {rows[0]?.date ?? "Unavailable"} through {rows.at(-1)?.date ?? "Unavailable"}. Windows end at the latest retained date, not today.</p>
    <PriceChart rows={rows} missingRows={market.gaps.some((gap) => gap === "missing_price_rows")}/>
    <p>Prices are split-adjusted and exclude distributions. Lines connect observed closes only; no missing price is imputed. The vertical axis uses the displayed range, not a zero baseline.</p>
    <p className="source-gap-note">Exchange-calendar completeness is unverified.{market.gaps.some((gap) => gap === "missing_price_rows") ? " The source reported missing price rows; connecting lines and affected returns are withheld." : " Holidays and unreported missing sessions cannot be distinguished here."}</p>
    <h3>Saved returns</h3><p>Price return excludes distributions. Total return estimate (provider-adjusted) uses adjusted close as a reinvestment proxy; it does not independently reconstruct cash reinvestment on payment dates.</p>
    {market.return_method === "yahoo-adjusted-ratio-v1" ? <div className="market-returns">{(market.returns ?? []).map((result) => <article key={result.period}>
      <h4>{returnLabels[result.period]}</h4>
      {result.source_id !== source.id ? <p>Unavailable — original return reference is missing.</p> : result.reason ? <p className="source-gap-note">Unavailable — {returnGaps[result.reason] ?? "The retained evidence is insufficient."}</p> : !result.start || decimalInteger(result.price_percent ?? "") === undefined || decimalInteger(result.total_return_estimate_percent ?? "") === undefined ? <p>Unavailable — no complete saved result.</p> : <>
        <p>Price return <strong>{displayNumber(result.price_percent!)}%</strong></p>
        <p>Total return estimate <strong>{displayNumber(result.total_return_estimate_percent!)}%</strong></p>
        <p className="ticker-meta">Observed {result.start} through {result.end}</p>
      </>}
      <p className="ticker-meta">Required start boundary {result.requested_start}</p>
    </article>)}</div> : <p className="source-gap-note">Returns were not retained in this version. Opening a saved page does not calculate new results.</p>}
    <details><summary>Return method and limitations</summary><p>Each saved return is (ending value ÷ starting value − 1) × 100, rounded to six decimal places, ties to even. Price return uses split-adjusted close; the separate estimate uses close adjusted for splits and distributions. Corporate actions are not added a second time. No annualization, fees, taxes or currency conversion.</p><p>The start is the last observation on or before the required boundary, within seven days. Missing prices, a missing baseline, a single observation or a gap over seven days withhold the return. Source adjustment errors remain possible. Method: {market.return_method ?? "not recorded"}. All results use the original price evidence linked above.</p></details>
    <details><summary>Exact daily values ({rows.length})</summary><p>OHLC is split-adjusted; adjusted close includes distributions. Volume is provider-reported. Original decimal strings are preserved.</p>
      <div className="market-table-scroll" tabIndex={0} role="region" aria-label="Daily price values"><table><thead><tr>{["Date", "Open", "High", "Low", "Close", "Adjusted close", "Volume"].map((label) => <th key={label} scope="col">{label}</th>)}</tr></thead><tbody>{descending.slice(page * 20, (page + 1) * 20).map((row) => <tr key={row.date}><th scope="row">{row.date}</th>{[row.open, row.high, row.low, row.close, row.adjusted_close, row.volume].map((value, index) => <td key={index}>{displayNumber(value)}</td>)}</tr>)}</tbody></table></div>
      {pages > 1 && <nav aria-label="Daily history pages"><button disabled={!page} onClick={() => setPage(page - 1)}>Newer prices</button><p aria-live="polite">Page {page + 1} of {pages}</p><button disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>Older prices</button></nav>}
    </details>
    <details><summary>Retained corporate actions ({actions.length})</summary><p>Provider event dates and original amounts/ratios. Amounts are in {market.currency}; event dates do not establish payment dates. No second adjustment is applied to prices or returns.</p>
      {actions.length ? <ul>{actions.slice(actionPage * 20, (actionPage + 1) * 20).map((action) => <li key={`${action.date}:${action.kind}`}>{action.date} · {action.kind === "capitalGains" ? "Capital-gain distribution" : action.kind === "splits" ? "Split ratio" : "Dividend"} · {action.kind === "splits" ? action.value : `${displayNumber(action.value)} ${market.currency}`}</li>)}</ul> : <p>No corporate actions were returned in this retained response; completeness is unverified.</p>}
      {actionPages > 1 && <nav aria-label="Corporate action pages"><button disabled={!actionPage} onClick={() => setActionPage(actionPage - 1)}>Newer actions</button><p aria-live="polite">Page {actionPage + 1} of {actionPages}</p><button disabled={actionPage + 1 >= actionPages} onClick={() => setActionPage(actionPage + 1)}>Older actions</button></nav>}
    </details>
    <p className="source-gap-note">See Key statistics for retained provider valuations when available. App-calculated price/earnings ratios require compatible dates, units and share bases.</p>
  </div>;
}

function PriceChart({ rows, missingRows }: { rows: MarketBar[]; missingRows: boolean }) {
  const id = useId(), geometry = useMemo(() => priceGeometry(rows, missingRows), [rows, missingRows]);
  if (!geometry) return <p>Chart unavailable — this window has no retained observations.</p>;
  return <figure className="market-chart"><figcaption>Daily close · USD · Split-adjusted</figcaption>
    <div className="market-axis-range">Displayed range: {displayNumber(geometry.min)} to {displayNumber(geometry.max)} USD</div>
    <svg role="img" aria-labelledby={`${id}-title ${id}-desc`} viewBox="0 0 660 270">
      <title id={`${id}-title`}>Retained daily closing prices</title><desc id={`${id}-desc`}>Historical split-adjusted closes, not a live quote. The time axis uses actual observation dates. Gaps over seven days are not connected; exact daily values and original evidence follow.</desc>
      {[30, 125, 220].map((y) => <line key={y} x1="70" x2="620" y1={y} y2={y} stroke="#c5d3ce" strokeDasharray="4 4"/>)}
      {geometry.segments.filter((segment) => segment.length > 1).map((segment) => <polyline key={segment[0].row.date} points={segment.map(({ x, y }) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" ")} fill="none" stroke="#176854" strokeWidth="2"/>)}
      {geometry.points.map(({ x, y, row }) => <circle key={row.date} cx={x} cy={y} r={rows.length > 200 ? 1 : 3} fill="#176854"><title>{row.date}: {row.close} USD</title></circle>)}
      <text x="70" y="253">{rows[0].date}</text><text x="620" y="253" textAnchor="end">{rows.at(-1)!.date}</text>
      <text x="65" y="26" textAnchor="end">High</text><text x="65" y="225" textAnchor="end">Low</text>
    </svg>
  </figure>;
}
