import { normalizeTicker, type EvidenceState, type FreshnessState, type OverviewChart } from "./fixtures";

export const chartRanges = ["1d", "5d", "1mo", "6mo", "ytd", "1y", "5y", "max"] as const;
export type ChartRange = (typeof chartRanges)[number];

export const defaultChartRange: ChartRange = "6mo";

export const chartRangeLabels: Record<ChartRange, string> = {
  "1d": "1D",
  "5d": "5D",
  "1mo": "1M",
  "6mo": "6M",
  ytd: "YTD",
  "1y": "1Y",
  "5y": "5Y",
  max: "All"
};

type Fetcher = typeof fetch;

type BackendOverviewChartPoint = {
  timestamp: string;
  close: number;
  volume: number | null;
};

type BackendOverviewChart = {
  chart_id: string;
  title: string;
  range: string;
  interval: string;
  points: BackendOverviewChartPoint[];
  currency: string | null;
  citation_ids: string[];
  source_document_ids: string[];
  freshness_state: string;
  evidence_state: string;
  as_of_date: string | null;
  retrieved_at: string | null;
  delayed_or_best_effort_label: string | null;
  limitations: string | null;
};

type BackendChartResponse = {
  schema_version: string;
  requested_range: string;
  supported_ranges: string[];
  default_range: string;
  chart: BackendOverviewChart | null;
};

export async function fetchAssetChart(
  ticker: string,
  range: ChartRange,
  fetcher: Fetcher = fetch
): Promise<OverviewChart | null> {
  const response = await fetcher(`/api/assets/${encodeURIComponent(normalizeTicker(ticker))}/chart?range=${range}`, {
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`Chart fetch failed with HTTP ${response.status}`);
  }
  const payload = (await response.json()) as BackendChartResponse;
  if (!isBackendChartResponse(payload) || !payload.chart) {
    return null;
  }
  return toOverviewChart(payload.chart);
}

export function isChartRange(value: string): value is ChartRange {
  return (chartRanges as readonly string[]).includes(value);
}

function isBackendChartResponse(value: unknown): value is BackendChartResponse {
  if (!value || typeof value !== "object") {
    return false;
  }
  const payload = value as Partial<BackendChartResponse>;
  return (
    payload.schema_version === "asset-chart-v1" &&
    typeof payload.requested_range === "string" &&
    Array.isArray(payload.supported_ranges) &&
    typeof payload.default_range === "string" &&
    (payload.chart === null || typeof payload.chart === "object")
  );
}

function toOverviewChart(chart: BackendOverviewChart): OverviewChart {
  return {
    chartId: chart.chart_id,
    title: chart.title,
    range: chart.range,
    interval: chart.interval,
    points: chart.points.map((point) => ({
      timestamp: point.timestamp,
      close: point.close,
      volume: point.volume
    })),
    currency: chart.currency,
    citationIds: chart.citation_ids,
    sourceDocumentIds: chart.source_document_ids,
    freshnessState: toFreshnessState(chart.freshness_state),
    evidenceState: toEvidenceState(chart.evidence_state),
    asOfDate: chart.as_of_date,
    retrievedAt: chart.retrieved_at,
    delayedOrBestEffortLabel: chart.delayed_or_best_effort_label,
    limitations: chart.limitations
  };
}

function toFreshnessState(value: string): FreshnessState {
  if (["fresh", "stale", "unknown", "unavailable"].includes(value)) {
    return value as FreshnessState;
  }
  return "unknown";
}

function toEvidenceState(value: string): EvidenceState {
  if (
    [
      "supported",
      "partial",
      "no_major_recent_development",
      "no_high_signal",
      "unavailable",
      "unknown",
      "stale",
      "mixed",
      "insufficient_evidence",
      "unsupported"
    ].includes(value)
  ) {
    return value as EvidenceState;
  }
  return "unknown";
}
