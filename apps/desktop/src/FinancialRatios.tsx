import { useMemo } from "react";
import type { EvidenceBundle, FinancialRatio } from "./contracts";
import { ObservationCitation } from "./FinancialHistory";
import { concepts, displayNumber, financialSeries } from "./financialSeries";

const reasons: Record<NonNullable<FinancialRatio["reason"]>, string> = {
  missing_income: "No net income observation matches this exact reporting interval.",
  conflicting_inputs: "The latest filing versions contain conflicting inputs.",
  ambiguous_inputs: "More than one current input remains; no filing or currency was selected automatically.",
  different_units: "The inputs use different currencies. No conversion was applied.",
  different_filings: "The latest inputs come from different filings. Older figures were not substituted.",
  nonpositive_revenue: "Revenue is zero or negative; this percentage is withheld.",
};

export function FinancialRatios({ bundle }: { bundle: EvidenceBundle }) {
  const { series, sources } = useMemo(() => financialSeries(bundle), [bundle]);
  const observations = new Map(series.flatMap((group) => group.rows.map((row) => [row.id, row] as const)));
  const calculated = bundle.financials?.ratio_method === "sec-net-income-revenue-v1" && bundle.asset.asset_type === "stock";
  const ratios = calculated ? bundle.financials?.ratios ?? [] : [];
  return <section aria-label="Calculated financial statistics" data-evidence-layer="calculation" className="financial-history">
    <h3>Net income / revenue (%)</h3>
    <p>Calculated as net income divided by revenue × 100, using the same issuer, filing, currency and reporting interval. Each revenue concept stays separate.</p>
    <p className="ticker-meta">Historical calculations, rounded to six decimal percentage places, ties to even. These are not reported percentages, forecasts or valuations. Saved results remain unchanged offline.</p>
    {!calculated ? <p className="source-gap-note">Not calculated for this saved version.</p> : !ratios.length && <p className="source-gap-note">Unavailable — no annual or quarterly revenue periods were admitted.</p>}
    {[...ratios].reverse().map((ratio) => {
      const inputs = ratio.input_ids.map((id) => observations.get(id));
      const sourceIds = new Set<string>(ratio.source_ids);
      const referencesValid = inputs.length > 0 && inputs.every((row) => row && sourceIds.has(row.source_id))
        && ratio.source_ids.every((id) => inputs.some((row) => row?.source_id === id));
      const paired = inputs.length === 2 && inputs.every((row) => row?.revision === "current" && row.start === ratio.start && row.end === ratio.end && row.period === ratio.period)
        && inputs[0]?.unit === inputs[1]?.unit && inputs[0]?.accession === inputs[1]?.accession && inputs[0]?.filed === inputs[1]?.filed
        && inputs.some((row) => row?.concept === "us-gaap:NetIncomeLoss") && inputs.some((row) => row?.concept === ratio.denominator_concept);
      const available = referencesValid && paired && !ratio.reason && typeof ratio.percent === "string"
        && /^-?(0|[1-9][0-9]*)(\.[0-9]{1,6})?$/.test(ratio.percent);
      return <details className="financial-series" key={`${ratio.denominator_concept}:${ratio.period}:${ratio.start}:${ratio.end}`}>
        <summary>{ratio.start} through {ratio.end} · {ratio.period === "annual" ? "Annual" : "Quarterly"} · {concepts[ratio.denominator_concept].label} · {available ? `${displayNumber(ratio.percent!)}%` : "Unavailable"}</summary>
        {available ? <p className="financial-value">{displayNumber(ratio.percent!)}%</p> : <p className="source-gap-note">{referencesValid && ratio.reason ? reasons[ratio.reason] : "The stored calculation or its original input references could not be validated for display."}</p>}
        <p className="ticker-meta">Revenue concept: {ratio.denominator_concept} · Method: {bundle.financials?.ratio_method}</p>
        {referencesValid && inputs.slice(0, 20).map((row) => row && <article key={row.id}>
          <h4>{concepts[row.concept].label}</h4><p>{displayNumber(row.value)} {row.unit} · {row.revision === "current" ? "Latest retained version" : "Unresolved conflict"}</p>
          <ObservationCitation row={row} bundle={bundle} source={sources.get(row.source_id)!}/>
        </article>)}
        {inputs.length > 20 && <p>Showing 20 of {inputs.length} conflicting inputs. Inspect Financials for all retained filing versions.</p>}
      </details>;
    })}
  </section>;
}
