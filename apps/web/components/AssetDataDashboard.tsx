import {
  citationLabel,
  getCitationById,
  type AssetFixture,
  type OverviewTable,
  type StockOverviewSection
} from "../lib/fixtures";
import { AssetPriceRangeChart } from "./AssetPriceRangeChart";
import { CitationChip } from "./CitationChip";
import { FreshnessDisclosure } from "./FreshnessLabel";
import { InlineGlossaryText, type InlineGlossaryContextMap, type InlineGlossaryMatch } from "./InlineGlossaryText";

type AssetDataDashboardProps = {
  asset: AssetFixture;
  glossaryMatches?: readonly InlineGlossaryMatch[];
  glossaryContexts?: InlineGlossaryContextMap | null;
};

export function hasAssetDataDashboard(asset: AssetFixture) {
  const sections = dashboardSections(asset);
  return sections.some((section) => section.chart || section.table);
}

export function AssetDataDashboard({ asset, glossaryMatches = [], glossaryContexts }: AssetDataDashboardProps) {
  const sections = dashboardSections(asset);
  const chartSection = sections.find((section) => section.sectionId === "price_chart");
  const quoteStats = chartSection?.table ?? null;
  const dashboardTables = dashboardTableSections(asset, sections);

  if (!chartSection?.chart && !quoteStats && !dashboardTables.length) {
    return null;
  }

  const holdingTable = dashboardTables.find((entry) => entry.table.tableId === "top_holdings");
  const sectorTable = dashboardTables.find((entry) => entry.table.tableId === "sector_weightings");
  const performanceTable = dashboardTables.find((entry) => entry.table.tableId === "performance_returns");

  return (
    <section
      className="asset-data-dashboard stable-section"
      aria-labelledby="asset-data-dashboard-heading"
      data-asset-data-dashboard
      data-prd-section="asset_data_dashboard"
      data-asset-type={asset.assetType}
      data-dashboard-table-count={dashboardTables.length + (quoteStats ? 1 : 0)}
      data-dashboard-has-chart={chartSection?.chart ? "true" : "false"}
      data-dashboard-holdings-table={holdingTable ? "true" : "false"}
      data-dashboard-sector-weightings={sectorTable ? "true" : "false"}
      data-dashboard-performance-section={performanceTable ? "true" : "false"}
    >
      <div className="section-heading-row">
        <div className="section-heading">
          <p className="eyebrow">Stable data dashboard</p>
          <h2 id="asset-data-dashboard-heading">Asset Data Dashboard</h2>
        </div>
        <div className="state-row">
          <span className="state-pill" data-evidence-state={chartSection?.evidenceState ?? "mixed"}>
            Official-first facts with provider-labeled fallback
          </span>
        </div>
      </div>

      <div className="asset-dashboard-chart-region">
        <AssetPriceRangeChart asset={asset} initialChart={chartSection?.chart ?? null} />
        {quoteStats ? (
          <QuoteStatGrid
            asset={asset}
            table={quoteStats}
            glossaryMatches={glossaryMatches}
            glossaryContexts={glossaryContexts}
          />
        ) : (
          <UnavailablePanel title="Quote stats" message="Quote and fund stats are unavailable in the current evidence pack." />
        )}
      </div>

      <div className="asset-dashboard-table-grid" data-dashboard-structured-table-grid>
        {dashboardTables.map(({ section, table }) => (
          <DashboardTable
            key={`${section.sectionId}-${table.tableId}`}
            asset={asset}
            section={section}
            table={table}
            glossaryMatches={glossaryMatches}
            glossaryContexts={glossaryContexts}
          />
        ))}
      </div>
    </section>
  );
}

function QuoteStatGrid({
  asset,
  table,
  glossaryMatches,
  glossaryContexts
}: {
  asset: AssetFixture;
  table: OverviewTable;
  glossaryMatches: readonly InlineGlossaryMatch[];
  glossaryContexts?: InlineGlossaryContextMap | null;
}) {
  return (
    <div className="quote-stat-grid-panel" data-quote-stat-grid data-overview-table-id={table.tableId}>
      <dl className="quote-stat-grid">
        {table.rows.map((row) => (
          <div key={row.rowId} className="quote-stat" data-quote-stat-id={row.rowId} data-row-evidence-state={row.evidenceState}>
            <dt data-dashboard-glossary-label>
              <InlineGlossaryText
                text={String(row.values.label ?? row.label ?? row.rowId)}
                matches={glossaryMatches}
                contexts={glossaryContexts}
                sourceSection={`dashboard.quote_stats.${row.rowId}.label`}
              />
            </dt>
            <dd>{formatTableValue(row.values.value)}</dd>
          </div>
        ))}
      </dl>
      <div className="freshness-disclosure-row">
        <FreshnessDisclosure
          label="Stats as of"
          value={table.asOfDate ?? table.retrievedAt ?? "Unknown in current evidence"}
          state={table.freshnessState}
        />
      </div>
      <span className="chip-row">
        <CitationChips asset={asset} citationIds={table.citationIds} />
      </span>
      {table.limitations ? <p className="notice-text">{table.limitations}</p> : null}
    </div>
  );
}

function DashboardTable({
  asset,
  section,
  table,
  glossaryMatches,
  glossaryContexts
}: {
  asset: AssetFixture;
  section: StockOverviewSection;
  table: OverviewTable;
  glossaryMatches: readonly InlineGlossaryMatch[];
  glossaryContexts?: InlineGlossaryContextMap | null;
}) {
  const markerProps = {
    "data-dashboard-holdings-table": table.tableId === "top_holdings" ? "true" : undefined,
    "data-dashboard-sector-weightings": table.tableId === "sector_weightings" ? "true" : undefined,
    "data-dashboard-performance-section": table.tableId === "performance_returns" ? "true" : undefined
  };
  const subtitle = dashboardTableSubtitle(table);
  const collapsedRowCount = table.tableId === "performance_returns" ? 4 : table.rows.length;
  const visibleRows = table.rows.slice(0, collapsedRowCount);
  const hiddenRows = table.rows.slice(collapsedRowCount);

  return (
    <article
      className="asset-dashboard-table-panel"
      data-overview-table
      data-overview-table-id={table.tableId}
      data-overview-section-id={section.sectionId}
      data-evidence-state={table.evidenceState}
      {...markerProps}
    >
      <div className="structured-table-heading">
        <div>
          <h3>{table.title}</h3>
          <p>{subtitle}</p>
        </div>
        <span className="state-pill compact-state" data-evidence-state={table.evidenceState}>
          {table.evidenceState.replaceAll("_", " ")}
        </span>
      </div>
      <div className="structured-table-scroll">
        <table>
          <DashboardColGroup table={table} />
          <thead>
            <tr>
              {table.columns.map((column) => (
                <th key={column.columnId} data-align={column.align} data-dashboard-glossary-label>
                  <InlineGlossaryText
                    text={column.label}
                    matches={glossaryMatches}
                    contexts={glossaryContexts}
                    sourceSection={`dashboard.${table.tableId}.${column.columnId}.header`}
                  />
                </th>
              ))}
              <th className="source-column-header" data-align="center">
                Src
              </th>
            </tr>
          </thead>
          <tbody>
            <DashboardRows
              asset={asset}
              table={table}
              rows={visibleRows}
              glossaryMatches={glossaryMatches}
              glossaryContexts={glossaryContexts}
            />
          </tbody>
        </table>
      </div>
      {hiddenRows.length ? (
        <details className="dashboard-table-expander" data-dashboard-collapsible-table>
          <summary>Show {hiddenRows.length} more rows</summary>
          <div className="structured-table-scroll compact-table-scroll">
            <table>
              <DashboardColGroup table={table} />
              <tbody>
                <DashboardRows
                  asset={asset}
                  table={table}
                  rows={hiddenRows}
                  glossaryMatches={glossaryMatches}
                  glossaryContexts={glossaryContexts}
                />
              </tbody>
            </table>
          </div>
        </details>
      ) : null}
      <div className="freshness-disclosure-row">
        <FreshnessDisclosure
          label="Table as of"
          value={table.asOfDate ?? table.retrievedAt ?? table.limitations ?? "Unknown in current evidence"}
          state={table.freshnessState}
        />
      </div>
      {table.limitations ? <p className="notice-text">{table.limitations}</p> : null}
    </article>
  );
}

function DashboardColGroup({ table }: { table: OverviewTable }) {
  return (
    <colgroup>
      {table.columns.map((column) => (
        <col key={column.columnId} data-column-id={column.columnId} />
      ))}
      <col data-column-id="sources" />
    </colgroup>
  );
}

function DashboardRows({
  asset,
  table,
  rows,
  glossaryMatches,
  glossaryContexts
}: {
  asset: AssetFixture;
  table: OverviewTable;
  rows: OverviewTable["rows"];
  glossaryMatches: readonly InlineGlossaryMatch[];
  glossaryContexts?: InlineGlossaryContextMap | null;
}) {
  return (
    <>
      {rows.map((row) => (
        <tr key={row.rowId} data-row-evidence-state={row.evidenceState}>
          {table.columns.map((column) => {
            const value = row.values[column.columnId];
            const isLabelCell = column.columnId === "label" || column.columnId === "sector" || column.columnId === "period";
            return (
              <td key={column.columnId} data-align={column.align} data-value-type={column.valueType}>
                {column.valueType === "percent" && typeof value === "number" ? (
                  <PercentBar value={value} />
                ) : isLabelCell ? (
                  <span data-dashboard-glossary-label>
                    <InlineGlossaryText
                      text={formatTableValue(value)}
                      matches={glossaryMatches}
                      contexts={glossaryContexts}
                      sourceSection={`dashboard.${table.tableId}.${row.rowId}.${column.columnId}`}
                    />
                  </span>
                ) : (
                  formatTableValue(value)
                )}
              </td>
            );
          })}
          <td className="source-icon-cell" data-align="center">
            <SourceDisclosure asset={asset} citationIds={row.citationIds} />
          </td>
        </tr>
      ))}
    </>
  );
}

function UnavailablePanel({ title, message }: { title: string; message: string }) {
  return (
    <div className="asset-dashboard-unavailable" data-dashboard-unavailable-state>
      <h3>{title}</h3>
      <p>{message}</p>
    </div>
  );
}

function dashboardSections(asset: AssetFixture) {
  return asset.assetType === "stock" ? asset.stockSections ?? [] : asset.etfSections ?? [];
}

function dashboardTableSections(asset: AssetFixture, sections: StockOverviewSection[]) {
  const dashboardSectionIds =
    asset.assetType === "etf"
      ? new Set(["fund_objective_role", "holdings_exposure", "sector_weightings", "performance"])
      : new Set(["business_overview", "financial_quality", "valuation_context"]);
  return sections
    .filter((section) => section.table && dashboardSectionIds.has(section.sectionId))
    .map((section) => ({ section, table: section.table as OverviewTable }));
}

function dashboardTableSubtitle(table: OverviewTable) {
  switch (table.tableId) {
    case "etf_overview":
      return "Official issuer facts are preferred; provider fields fill overview gaps with labels.";
    case "top_holdings":
      return "Top positions use issuer rows first, then provider fallback where official rows are missing.";
    case "sector_weightings":
      return "Sector rows are issuer-first with provider fallback clearly labeled.";
    case "performance_returns":
      return "Historical returns are provider-derived context only, not forecasts.";
    case "stock_profile_snapshot":
      return "Profile fields are provider-labeled unless SEC-backed facts are available.";
    case "stock_financial_snapshot":
      return "SEC latest facts are combined with provider-labeled financial context.";
    case "stock_valuation_ratios":
      return "Provider valuation ratios are context only, not cheap-or-expensive labels.";
    default:
      return "Structured facts use official sources first and provider fallback where needed.";
  }
}

function CitationChips({ asset, citationIds }: { asset: AssetFixture; citationIds: string[] }) {
  return (
    <>
      {citationIds.map((citationId) => {
        const citation = getCitationById(asset, citationId);
        return citation ? <CitationChip key={citationId} citation={citation} label={citationLabel(citationId)} /> : null;
      })}
    </>
  );
}

function SourceDisclosure({ asset, citationIds }: { asset: AssetFixture; citationIds: string[] }) {
  const citations = citationIds
    .map((citationId) => {
      const citation = getCitationById(asset, citationId);
      return citation ? { citation, citationId } : null;
    })
    .filter((item): item is { citation: NonNullable<ReturnType<typeof getCitationById>>; citationId: string } => Boolean(item));
  const label = citations.map(({ citationId }) => citationLabel(citationId)).join(", ");

  if (!citations.length) {
    return <span className="source-icon-empty" aria-label="No source citation">-</span>;
  }

  return (
    <details className="source-icon-disclosure" data-dashboard-source-icon title={label}>
      <summary aria-label={`Show ${citations.length} source citation${citations.length === 1 ? "" : "s"}`}>
        <span aria-hidden="true">i</span>
        <span className="source-icon-count">{citations.length}</span>
      </summary>
      <span className="source-icon-popover">
        <CitationChips asset={asset} citationIds={citationIds} />
      </span>
    </details>
  );
}

function PercentBar({ value }: { value: number }) {
  const width = Math.max(0, Math.min(100, Math.abs(value)));
  return (
    <span className="percent-bar-cell">
      <span className="percent-bar-track" aria-hidden="true">
        <span className={value < 0 ? "percent-bar-fill negative" : "percent-bar-fill"} style={{ width: `${width}%` }} />
      </span>
      <span className={value < 0 ? "percent-bar-value negative" : "percent-bar-value"}>{formatPercent(value)}</span>
    </span>
  );
}

function formatTableValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return "Unavailable";
  }
  if (typeof value === "number") {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
  }
  return String(value);
}

function formatPercent(value: number) {
  return `${value.toFixed(2).replace(/\.?0+$/, "")}%`;
}
