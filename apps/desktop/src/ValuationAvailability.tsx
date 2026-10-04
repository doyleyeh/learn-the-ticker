import { useMemo } from "react";
import type { EvidenceBundle } from "./contracts";
import { admittedMarket } from "./marketPresentation";
import { financialSeries } from "./financialSeries";

export function ValuationAvailability({ bundle }: { bundle: EvidenceBundle }) {
  const market = useMemo(() => admittedMarket(bundle), [bundle]);
  const { series } = useMemo(() => financialSeries(bundle), [bundle]);
  const income = series.filter((group) => group.concept === "us-gaap:EarningsPerShareDiluted" && group.unit === "USD/shares" && group.period === "annual");
  const usableIncome = income.some((group) => {
    const latest = group.points.at(-1)?.row, retained = group.rows.at(-1);
    return latest && latest.start === retained?.start && latest.end === retained?.end;
  });
  return <section aria-label="Valuation availability" className="financial-unavailable" data-local-only={Boolean(bundle.market) || undefined}>
    <h3>Valuation and yield</h3>
    {bundle.asset.asset_type !== "stock" ? <p className="source-gap-note">Stock valuation metrics are unavailable for this asset type{bundle.asset.asset_type === "unknown" ? " until its identity is confirmed" : ""}.</p> : <>
      <p className="source-gap-note">{market ? "Historical daily prices are retained. They alone cannot establish these metrics." : "A verified daily price snapshot is unavailable for these metrics."}</p>
      <dl>
        <dt>Historical P/E</dt><dd>Unavailable — {usableIncome ? "annual diluted EPS is retained, but its share class and stock-split basis have not been independently matched to the price series." : "no single current, unconflicted annual diluted EPS figure in USD per share is available for alignment."} Compatible earnings intervals and share bases are required; prices and EPS are not divided automatically.</dd>
        <dt>Market capitalization</dt><dd>Unavailable — shares outstanding for the same listing and price date have not been verified. Weighted-average diluted shares describe a reporting period and are not a substitute.</dd>
        <dt>Dividend yield</dt><dd>Unavailable — a complete compatible dividend period and a stated trailing or forward method have not been verified. Individual retained dividend events do not establish that coverage.</dd>
      </dl>
    </>}
  </section>;
}
