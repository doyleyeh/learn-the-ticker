import type { EvidenceBundle, MarketBar, Source } from "./contracts";
import { decimalInteger } from "./financialSeries";

export type ChartWindow = "1m" | "6m" | "ytd" | "1y" | "3y" | "5y" | "all";
export const chartWindows: Record<ChartWindow, string> = { "1m": "1 month", "6m": "6 months", ytd: "YTD", "1y": "1 year", "3y": "3 years", "5y": "5 years", all: "All retained" };
export const returnLabels: Record<string, string> = { ytd: "YTD", "1y": "1 year", "3y": "3 years", "5y": "5 years", retained: "Retained interval" };
export const returnGaps: Record<string, string> = { start_boundary_missing: "No observation at or before the required start boundary.", missing_price_rows: "The source reported missing prices.", insufficient_observations: "At least two compatible observations are required.", history_gap: "The retained history has a gap longer than seven days." };
const day = (value: string) => Date.parse(`${value}T00:00:00Z`);

export function privateSource(source: Source) {
  const host = new URL(source.url).hostname.toLowerCase();
  return source.usage_scope === "private_yahoo_v1" || source.provenance === "market_adapter" || host === "finance.yahoo.com" || host.endsWith(".finance.yahoo.com");
}

export function privateClaims(bundle: EvidenceBundle) {
  const sources = new Set(bundle.sources?.filter(privateSource).map((source) => source.id));
  for (const ref of bundle.context_references ?? []) sources.add(ref.id);
  const rows = [...(bundle.claims ?? []), ...(bundle.notes ?? [])];
  const blocked = new Set(rows.filter((row) => row.source_ids?.some((id) => sources.has(id))).map((row) => row.id));
  let changed = true;
  while (changed) {
    changed = false;
    for (const row of rows) if (!blocked.has(row.id) && row.input_claim_ids?.some((id) => blocked.has(id))) { blocked.add(row.id); changed = true; }
  }
  return blocked;
}

// Presentation guards supplement backend admission; they do not authenticate an archive.
export function admittedMarket(bundle: EvidenceBundle) {
  const market = bundle.market, source = bundle.sources?.find((item) => item.id === market?.source_id);
  if (!market || !source?.verified || source.asset_id !== bundle.asset.id || source.provenance !== "market_adapter"
    || source.usage_scope !== "private_yahoo_v1" || source.policy !== "metadata_only" || bundle.asset.asset_type !== "stock"
    || market.usage_scope !== "private_yahoo_v1" || market.currency !== "USD" || market.close_basis !== "split_adjusted"
    || market.adjusted_close_basis !== "splits_and_distributions" || !market.bars.length || market.bars.length > 2000) return undefined;
  if (market.bars.some((row, index) => !Number.isFinite(day(row.date)) || (index > 0 && row.date <= market.bars[index - 1].date)
    || [row.open, row.high, row.low, row.close, row.adjusted_close, row.volume].some((value) => decimalInteger(value) === undefined))) return undefined;
  return { market, source };
}

export function chartRows(bars: MarketBar[], window: ChartWindow) {
  if (!bars.length || window === "all") return bars;
  const end = new Date(day(bars.at(-1)!.date));
  let year = end.getUTCFullYear(), month = end.getUTCMonth(), date = end.getUTCDate();
  if (window === "ytd") { month = 0; date = 1; }
  else if (window === "1m" || window === "6m") month -= window === "1m" ? 1 : 6;
  else year -= { "1y": 1, "3y": 3, "5y": 5 }[window];
  const lastDay = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  const start = new Date(Date.UTC(year, month, Math.min(date, lastDay))).toISOString().slice(0, 10);
  return bars.filter((row) => row.date >= start);
}

export function priceGeometry(rows: MarketBar[], missingRows: boolean) {
  if (!rows.length) return undefined;
  const values = rows.map((row) => decimalInteger(row.close)!);
  const min = values.reduce((a, b) => a < b ? a : b), max = values.reduce((a, b) => a > b ? a : b);
  const first = day(rows[0].date), last = day(rows.at(-1)!.date);
  const points = rows.map((row, index) => ({ row,
    x: last === first ? 350 : 70 + (day(row.date) - first) / (last - first) * 550,
    y: max === min ? 125 : 220 - Number((values[index] - min) * 19000n / (max - min)) / 100,
  }));
  const segments: typeof points[] = [];
  points.forEach((point, index) => {
    if (!index || missingRows || day(point.row.date) - day(points[index - 1].row.date) > 7 * 86400000) segments.push([]);
    segments.at(-1)!.push(point);
  });
  return { points, segments, min: rows[values.indexOf(min)].close, max: rows[values.indexOf(max)].close };
}
