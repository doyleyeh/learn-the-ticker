import type { EvidenceBundle, FinancialObservation, Source } from "./contracts";

export const concepts: Record<string, { label: string; description: string }> = {
  "us-gaap:Assets": { label: "Assets", description: "Resources reported by the issuer at a point in time." },
  "us-gaap:Liabilities": { label: "Liabilities", description: "Obligations reported by the issuer at a point in time." },
  "us-gaap:StockholdersEquity": { label: "Stockholders’ equity", description: "The reported accounting interest remaining after liabilities." },
  "us-gaap:Revenues": { label: "Revenue", description: "Revenue under this specific reporting concept. Other revenue concepts are shown separately." },
  "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax": { label: "Revenue from customer contracts", description: "Revenue from customer contracts excluding assessed taxes. It is not joined to the separate Revenues concept." },
  "us-gaap:NetIncomeLoss": { label: "Net income or loss", description: "The issuer’s reported profit or loss for the stated period." },
  "us-gaap:NetCashProvidedByUsedInOperatingActivities": { label: "Operating cash flow", description: "Reported cash provided by or used in operating activities over the stated period." },
  "us-gaap:EarningsPerShareDiluted": { label: "Diluted earnings per share", description: "Reported earnings per diluted share. Historical figures are not independently adjusted for corporate actions here." },
  "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding": { label: "Weighted average diluted shares", description: "Reported weighted average diluted shares for the stated period, not shares at a single date." },
};

export type FinancialPoint = { row: FinancialObservation; citations: FinancialObservation[] };
export type FinancialSeries = {
  key: string; concept: string; unit: string; period: FinancialObservation["period"];
  rows: FinancialObservation[]; points: FinancialPoint[]; withheld: number;
};

// These fixed-scale integers are presentation inputs only. Exact values remain strings.
export function decimalInteger(value: string): bigint | undefined {
  if (value.length > 80 || !/^-?(0|[1-9][0-9]*)(\.[0-9]{1,18})?$/.test(value)) return undefined;
  const [whole, fraction = ""] = value.replace(/^-/, "").split(".");
  if (whole.length > 41) return undefined;
  const number = BigInt(whole + fraction.padEnd(18, "0"));
  return value.startsWith("-") ? -number : number;
}

export function displayNumber(value: string): string {
  const [whole, fraction] = value.split(".");
  return whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",") + (fraction === undefined ? "" : "." + fraction);
}

export function financialSeries(bundle: EvidenceBundle): { series: FinancialSeries[]; excluded: number; sources: Map<string, Source> } {
  const sources = new Map((bundle.sources ?? []).map((source) => [source.id!, source]));
  const groups = new Map<string, FinancialSeries>();
  let excluded = 0;
  for (const row of bundle.financials?.observations ?? []) {
    const source = sources.get(row.source_id);
    if (!source?.verified || source.asset_id !== bundle.asset.id || source.policy !== "full_text_allowed" || source.provenance !== "structured_adapter"
      || !concepts[row.concept] || decimalInteger(row.value) === undefined || row.cik !== bundle.financials?.issuer.identifiers?.cik) {
      excluded++; continue;
    }
    const key = JSON.stringify([row.concept, row.unit, row.period]);
    if (!groups.has(key)) groups.set(key, { key, concept: row.concept, unit: row.unit, period: row.period, rows: [], points: [], withheld: 0 });
    groups.get(key)!.rows.push(row);
  }
  for (const series of groups.values()) {
    series.rows.sort((a, b) => a.end.localeCompare(b.end) || (a.start ?? "").localeCompare(b.start ?? "") || a.filed.localeCompare(b.filed) || a.id.localeCompare(b.id));
    const periods = new Map<string, FinancialObservation[]>();
    for (const row of series.rows) {
      const key = JSON.stringify([row.start, row.end]);
      if (!periods.has(key)) periods.set(key, []);
      periods.get(key)!.push(row);
    }
    for (const rows of periods.values()) {
      const current = rows.filter((row) => row.revision === "current");
      if (rows.some((row) => row.revision === "conflict") || new Set(current.map((row) => row.value)).size !== 1) {
        series.withheld++; continue;
      }
      series.points.push({ row: current[0], citations: current });
    }
    // Match the default history windows and keep a large archive bounded on screen.
    const limit = series.period === "annual" ? 5 : series.period === "quarter" ? 12 : 20;
    series.points = series.points.slice(-limit);
  }
  return { series: [...groups.values()].sort((a, b) => a.key.localeCompare(b.key)), excluded, sources };
}

export function chartGeometry(points: FinancialPoint[]) {
  const values = points.map(({ row }) => decimalInteger(row.value)!);
  const min = values.reduce((a, b) => b < a ? b : a, 0n);
  const max = values.reduce((a, b) => b > a ? b : a, 0n);
  const range = max - min || 1n;
  // Convert only bounded coordinates, never the source number, to floating point.
  const coordinate = (value: bigint) => Number((value - min) * 10_000n / range) / 100;
  return { zero: coordinate(0n), positions: values.map(coordinate) };
}

export const gapLabels: Record<string, string> = {
  price_history_unavailable: "Price history is unavailable.",
  corporate_actions_unavailable: "Corporate-action and distribution history is unavailable.",
  source_access_or_rate_limited: "Some sources were unavailable or rate limited.",
  unsupported_unit: "Some observations use unsupported units.",
  unsupported_form: "Some observations use unsupported filing forms.",
  no_supported_observations: "No supported observations were available.",
  conflicting_latest_values: "Latest filing versions contain unresolved conflicting values.",
  nonstandard_or_year_to_date_period: "Nonstandard or year-to-date periods are not combined into annual or quarterly history.",
  incomplete_annual_history: "The five-year annual history is incomplete.",
  incomplete_quarter_history: "The twelve-quarter history is incomplete.",
  incomplete_instant_history: "The history of point-in-time observations is incomplete.",
  source_unavailable_or_invalid: "The source was unavailable or could not be validated.",
};

export function gapLabel(gap: string): string {
  const [concept, reason] = gap.split(":", 2);
  return reason ? `${concepts["us-gaap:" + concept]?.label ?? concept}: ${gapLabels[reason] ?? "Evidence is incomplete."}`
    : gapLabels[gap] ?? "Evidence is incomplete.";
}
