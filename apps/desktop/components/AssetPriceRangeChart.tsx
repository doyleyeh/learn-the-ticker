"use client";

import { useMemo, useState, useTransition } from "react";
import {
  chartRangeLabels,
  chartRanges,
  defaultChartRange,
  fetchAssetChart,
  isChartRange,
  type ChartRange
} from "../lib/assetChart";
import {
  type AssetFixture,
  type OverviewChart,
  type OverviewChartPoint
} from "../lib/fixtures";
import { CompactCitationSources, resolveAssetCitations } from "./CompactCitationSources";

type AssetPriceRangeChartProps = {
  asset: AssetFixture;
  initialChart: OverviewChart | null;
};

export function AssetPriceRangeChart({ asset, initialChart }: AssetPriceRangeChartProps) {
  const initialRange = isChartRange(initialChart?.range ?? "") ? (initialChart?.range as ChartRange) : defaultChartRange;
  const [activeRange, setActiveRange] = useState<ChartRange>(initialRange);
  const [chart, setChart] = useState<OverviewChart | null>(initialChart);
  const [loadState, setLoadState] = useState<"ready" | "loading" | "unavailable" | "error">(initialChart ? "ready" : "unavailable");
  const [isPending, startTransition] = useTransition();
  const geometry = useMemo(() => buildChartGeometry(chart?.points ?? []), [chart]);
  const change = geometry.firstClose && geometry.lastClose ? ((geometry.lastClose - geometry.firstClose) / geometry.firstClose) * 100 : null;
  const latestLabel = geometry.lastClose === null ? "Price unavailable" : formatNumber(geometry.lastClose);
  const shouldShowLoading = loadState === "loading" || isPending;

  function selectRange(range: ChartRange) {
    if (range === activeRange && chart) {
      return;
    }
    setActiveRange(range);
    setLoadState("loading");
    startTransition(() => {
      fetchAssetChart(asset.ticker, range)
        .then((nextChart) => {
          setChart(nextChart);
          setLoadState(nextChart ? "ready" : "unavailable");
        })
        .catch(() => {
          setChart(null);
          setLoadState("error");
        });
    });
  }

  return (
    <div
      className="asset-dashboard-chart"
      data-dashboard-chart
      data-active-chart-range={activeRange}
      data-active-chart-label={chartRangeLabels[activeRange]}
      data-chart-point-count={chart?.points.length ?? 0}
      data-evidence-state={chart?.evidenceState ?? "unavailable"}
    >
      <div className="asset-dashboard-chart-toolbar">
        <div className="chart-range-tabs" role="tablist" aria-label={`${asset.ticker} chart range`} data-chart-range-tabs>
          {chartRanges.map((range) => (
            <button
              key={range}
              type="button"
              role="tab"
              aria-selected={activeRange === range}
              className="chart-range-tab"
              data-chart-range={range}
              onClick={() => selectRange(range)}
            >
              {chartRangeLabels[range]}
            </button>
          ))}
        </div>
        <span className={change !== null && change < 0 ? "price-change negative" : "price-change positive"}>
          {change === null ? "Change unavailable" : `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`}
        </span>
      </div>

      <div className="asset-dashboard-chart-canvas" aria-busy={shouldShowLoading} data-chart-loading-state={loadState}>
        {chart && geometry.linePath ? (
          <svg className="asset-dashboard-chart-svg" viewBox="0 0 720 320" role="img" aria-label={`${asset.ticker} ${chartRangeLabels[activeRange]} price chart`}>
            <defs>
              <linearGradient id={`asset-chart-area-${asset.ticker}`} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="currentColor" stopOpacity="0.24" />
                <stop offset="100%" stopColor="currentColor" stopOpacity="0.02" />
              </linearGradient>
            </defs>
            {geometry.gridLines.map((line) => (
              <line key={line.y} className="chart-grid-line" x1="24" x2="660" y1={line.y} y2={line.y} />
            ))}
            <path className="chart-area-path" d={geometry.areaPath} fill={`url(#asset-chart-area-${asset.ticker})`} />
            <path className={change !== null && change < 0 ? "chart-line-path negative" : "chart-line-path"} d={geometry.linePath} />
            <g className="chart-volume-bars" data-chart-volume-bars>
              {geometry.volumeBars.map((bar) => (
                <rect key={bar.key} x={bar.x} y={bar.y} width={bar.width} height={bar.height} rx="1.5" />
              ))}
            </g>
            {geometry.latestMarker ? (
              <g className="chart-latest-marker">
                <line x1="24" x2="682" y1={geometry.latestMarker.y} y2={geometry.latestMarker.y} />
                <circle cx={geometry.latestMarker.x} cy={geometry.latestMarker.y} r="4" />
                <text x="690" y={geometry.latestMarker.y + 4}>{latestLabel}</text>
              </g>
            ) : null}
            {geometry.xLabels.map((label) => (
              <text key={label.key} className="chart-axis-label" x={label.x} y="308">
                {label.text}
              </text>
            ))}
            {geometry.yLabels.map((label) => (
              <text key={label.key} className="chart-axis-label y-axis" x="666" y={label.y + 4}>
                {label.text}
              </text>
            ))}
          </svg>
        ) : (
          <div className="asset-dashboard-chart-unavailable" data-dashboard-chart-unavailable>
            {loadState === "error" ? "Chart range could not be loaded from the local API." : "Chart points are unavailable for this range."}
          </div>
        )}
        {shouldShowLoading ? <div className="asset-dashboard-chart-loading">Loading range...</div> : null}
      </div>

      <div className="compact-source-row">
        <CompactCitationSources
          citations={chart ? resolveAssetCitations(asset, chart.citationIds) : []}
          label="Chart evidence details"
          metadataRows={[
            {
              label: "Chart as of",
              value: chart?.asOfDate ?? chart?.retrievedAt ?? "Unknown in current evidence",
              state: chart?.freshnessState ?? "unavailable"
            },
            {
              label: "Range",
              value: `${chartRangeLabels[activeRange]} · ${chart?.interval ?? "interval unavailable"} · ${chart?.currency ?? asset.exchange ?? "currency unavailable"}`,
              state: chart?.freshnessState ?? "unavailable"
            },
            { label: "Provider label", value: chart?.delayedOrBestEffortLabel ?? null, state: chart?.freshnessState ?? "unknown" }
          ]}
        />
      </div>
      {chart?.limitations ? <p className="notice-text">{chart.limitations}</p> : null}
    </div>
  );
}

function buildChartGeometry(points: OverviewChartPoint[]) {
  const validPoints = points.filter((point) => Number.isFinite(point.close));
  const width = 720;
  const chartLeft = 24;
  const chartRight = 660;
  const chartTop = 28;
  const chartBottom = 226;
  const volumeTop = 238;
  const volumeBottom = 288;
  const closes = validPoints.map((point) => point.close);
  const minClose = closes.length ? Math.min(...closes) : 0;
  const maxClose = closes.length ? Math.max(...closes) : 1;
  const spread = maxClose - minClose || 1;
  const volumes = validPoints.map((point) => (typeof point.volume === "number" ? point.volume : 0));
  const maxVolume = Math.max(...volumes, 1);
  const pointPosition = (point: OverviewChartPoint, index: number) => {
    const x = validPoints.length === 1 ? (chartLeft + chartRight) / 2 : chartLeft + (index / (validPoints.length - 1)) * (chartRight - chartLeft);
    const y = chartBottom - ((point.close - minClose) / spread) * (chartBottom - chartTop);
    return { x, y };
  };
  const positions = validPoints.map(pointPosition);
  const linePath = positions
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(" ");
  const areaPath = linePath ? `${linePath} L ${positions[positions.length - 1].x.toFixed(2)} ${chartBottom} L ${positions[0].x.toFixed(2)} ${chartBottom} Z` : "";
  const barWidth = Math.max(2, Math.min(8, (chartRight - chartLeft) / Math.max(validPoints.length, 1) - 2));
  const volumeBars = validPoints.map((point, index) => {
    const volume = typeof point.volume === "number" ? point.volume : 0;
    const height = Math.max(2, (volume / maxVolume) * (volumeBottom - volumeTop));
    const x = positions[index].x - barWidth / 2;
    return {
      key: `${point.timestamp}-${index}`,
      x,
      y: volumeBottom - height,
      width: barWidth,
      height
    };
  });
  const latestPosition = positions[positions.length - 1];
  return {
    linePath,
    areaPath,
    volumeBars,
    latestMarker: latestPosition ? { x: latestPosition.x, y: latestPosition.y } : null,
    firstClose: closes[0] ?? null,
    lastClose: closes[closes.length - 1] ?? null,
    gridLines: [chartTop, chartTop + 66, chartTop + 132, chartBottom].map((y) => ({ y })),
    yLabels: [maxClose, (maxClose + minClose) / 2, minClose].map((value, index) => ({
      key: `y-${index}`,
      y: index === 0 ? chartTop : index === 1 ? (chartTop + chartBottom) / 2 : chartBottom,
      text: formatNumber(value)
    })),
    xLabels: buildDateLabels(validPoints, chartLeft, chartRight),
    width
  };
}

function buildDateLabels(points: OverviewChartPoint[], chartLeft: number, chartRight: number) {
  if (!points.length) {
    return [];
  }
  const labelIndexes = [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])];
  return labelIndexes.map((index) => ({
    key: `${points[index].timestamp}-${index}`,
    x: points.length === 1 ? (chartLeft + chartRight) / 2 : chartLeft + (index / (points.length - 1)) * (chartRight - chartLeft),
    text: formatDateLabel(points[index].timestamp)
  }));
}

function formatDateLabel(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value.slice(0, 10);
  }
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date);
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
}
