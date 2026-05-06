import {
  type AssetFixture,
  type OverviewChart,
  type OverviewTable,
  type StockOverviewSection
} from "../lib/fixtures";
import { CompactCitationSources, resolveAssetCitations } from "./CompactCitationSources";
import { FreshnessDisclosure } from "./FreshnessLabel";

type StructuredOverviewDisplaysProps = {
  asset: AssetFixture;
  section: StockOverviewSection;
};

export function StructuredOverviewDisplays({ asset, section }: StructuredOverviewDisplaysProps) {
  return (
    <>
      {section.table ? <StructuredTable asset={asset} section={section} table={section.table} /> : null}
      {section.chart ? <PriceChartPanel asset={asset} section={section} chart={section.chart} /> : null}
    </>
  );
}

function StructuredTable({
  asset,
  section,
  table
}: {
  asset: AssetFixture;
  section: StockOverviewSection;
  table: OverviewTable;
}) {
  const markerProps = {
    "data-holdings-table": table.tableId === "top_holdings" ? "true" : undefined,
    "data-sector-weightings": table.tableId === "sector_weightings" ? "true" : undefined,
    "data-performance-section": table.tableId === "performance_returns" ? "true" : undefined
  };

  return (
    <div
      className="structured-table-panel"
      data-overview-table
      data-overview-table-id={table.tableId}
      data-overview-section-id={section.sectionId}
      data-evidence-state={table.evidenceState}
      {...markerProps}
    >
      <div className="structured-table-heading">
        <h3>{table.title}</h3>
        <span className="state-pill compact-state" data-evidence-state={table.evidenceState}>
          {table.evidenceState.replaceAll("_", " ")}
        </span>
      </div>
      <div className="structured-table-scroll">
        <table>
          <thead>
            <tr>
              {table.columns.map((column) => (
                <th key={column.columnId} data-align={column.align}>
                  {column.label}
                </th>
              ))}
              <th data-align="left">Sources</th>
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row) => (
              <tr key={row.rowId} data-row-evidence-state={row.evidenceState}>
                {table.columns.map((column) => {
                  const value = row.values[column.columnId];
                  return (
                    <td key={column.columnId} data-align={column.align} data-value-type={column.valueType}>
                      {column.valueType === "percent" && typeof value === "number" ? (
                        <PercentBar value={value} />
                      ) : (
                        formatTableValue(value, column.valueType)
                      )}
                    </td>
                  );
                })}
                <td>
                  <CompactCitationSources
                    citations={resolveAssetCitations(asset, row.citationIds)}
                    label={`${row.label ?? table.title} sources`}
                    showEmpty
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="freshness-disclosure-row">
        <FreshnessDisclosure
          label="Table as of"
          value={table.asOfDate ?? table.retrievedAt ?? table.limitations ?? "Unknown in current evidence"}
          state={table.freshnessState}
        />
      </div>
      {table.limitations ? <p className="notice-text">{table.limitations}</p> : null}
    </div>
  );
}

function PercentBar({ value }: { value: number }) {
  const width = Math.max(0, Math.min(100, value));
  return (
    <span className="percent-bar-cell">
      <span className="percent-bar-track" aria-hidden="true">
        <span className="percent-bar-fill" style={{ width: `${width}%` }} />
      </span>
      <span className="percent-bar-value">{formatPercent(value)}</span>
    </span>
  );
}

function PriceChartPanel({
  asset,
  section,
  chart
}: {
  asset: AssetFixture;
  section: StockOverviewSection;
  chart: OverviewChart;
}) {
  const points = chart.points.filter((point) => Number.isFinite(point.close));
  const pathPoints = chartPolyline(points);
  const first = points[0]?.close;
  const last = points[points.length - 1]?.close;
  const change = first && last ? ((last - first) / first) * 100 : null;

  return (
    <div
      className="price-chart-panel"
      data-price-chart-panel
      data-overview-section-id={section.sectionId}
      data-chart-point-count={points.length}
      data-evidence-state={chart.evidenceState}
    >
      <div className="structured-table-heading">
        <div>
          <h3>{chart.title}</h3>
          <p>{chart.range.toUpperCase()} · {chart.interval} · {chart.currency ?? asset.exchange}</p>
        </div>
        <span className={change !== null && change < 0 ? "price-change negative" : "price-change positive"}>
          {change === null ? "Change unavailable" : `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`}
        </span>
      </div>
      <svg className="price-chart-svg" viewBox="0 0 640 220" role="img" aria-label={`${asset.ticker} basic price chart`}>
        <line x1="0" y1="188" x2="640" y2="188" />
        <polyline points={pathPoints} />
      </svg>
      <div className="freshness-disclosure-row">
        <FreshnessDisclosure
          label="Chart as of"
          value={chart.asOfDate ?? chart.retrievedAt ?? "Unknown in current evidence"}
          state={chart.freshnessState}
        />
        {chart.delayedOrBestEffortLabel ? (
          <FreshnessDisclosure label="Provider label" value={chart.delayedOrBestEffortLabel} state={chart.freshnessState} />
        ) : null}
      </div>
      <div className="compact-source-row">
        <CompactCitationSources citations={resolveAssetCitations(asset, chart.citationIds)} label="Chart sources" />
      </div>
      {chart.limitations ? <p className="notice-text">{chart.limitations}</p> : null}
    </div>
  );
}

function chartPolyline(points: OverviewChart["points"]) {
  if (points.length === 0) {
    return "";
  }
  const closes = points.map((point) => point.close);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const spread = max - min || 1;
  return points
    .map((point, index) => {
      const x = points.length === 1 ? 320 : (index / (points.length - 1)) * 640;
      const y = 188 - ((point.close - min) / spread) * 156;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function formatTableValue(value: string | number | null | undefined, valueType: OverviewTable["columns"][number]["valueType"]) {
  if (value === null || value === undefined || value === "") {
    return "Unavailable";
  }
  if (valueType === "percent" && typeof value === "number") {
    return formatPercent(value);
  }
  return String(value);
}

function formatPercent(value: number) {
  return `${value.toFixed(2).replace(/\.?0+$/, "")}%`;
}
