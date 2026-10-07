import {
  type AssetFixture,
  type StockOverviewSection,
  type StockSectionItem
} from "../lib/fixtures";
import { CompactCitationSources, resolveAssetCitations } from "./CompactCitationSources";
import { InlineGlossaryText, type InlineGlossaryContextMap, type InlineGlossaryMatch } from "./InlineGlossaryText";

type AssetStockSectionsProps = {
  asset: AssetFixture;
  glossaryMatches?: readonly InlineGlossaryMatch[];
  glossaryContexts?: InlineGlossaryContextMap | null;
};

export function AssetStockSections({ asset, glossaryMatches = [], glossaryContexts }: AssetStockSectionsProps) {
  if (asset.assetType !== "stock" || !asset.stockSections?.length) {
    return null;
  }

  const deepDiveDuplicateIds = new Set([
    "top_risks",
    "recent_developments",
    "educational_suitability",
    "business_overview",
    "financial_quality",
    "valuation_context",
    "price_chart"
  ]);
  const deepDiveSections = asset.stockSections.filter(
    (section) =>
      !deepDiveDuplicateIds.has(section.sectionId) &&
      !section.table &&
      !section.chart &&
      !section.sectionId.startsWith("provider_")
  );

  return (
    <div
      className="section-stack stock-prd-sections"
      data-stock-prd-sections
      data-asset-ticker={asset.ticker}
      data-shared-prd-section-shell
      data-dashboard-duplicate-sections-filtered="business_overview,financial_quality,valuation_context,price_chart"
      data-deep-dive-duplicate-sections-filtered="top_risks,recent_developments,educational_suitability,business_overview,financial_quality,valuation_context,price_chart,provider_metric_tables"
      data-deep-dive-table-chart-policy="exclude_table_or_chart_sections"
      data-deep-dive-source-status-sections="products_services,strengths,market_reference,evidence_limits"
    >
      {deepDiveSections.map((section) => (
        <StockSection
          key={section.sectionId}
          asset={asset}
          section={section}
          glossaryMatches={glossaryMatches}
          glossaryContexts={glossaryContexts}
        />
      ))}
    </div>
  );
}

function StockSection({
  asset,
  section,
  glossaryMatches,
  glossaryContexts
}: {
  asset: AssetFixture;
  section: StockOverviewSection;
  glossaryMatches: readonly InlineGlossaryMatch[];
  glossaryContexts?: InlineGlossaryContextMap | null;
}) {
  const isRecent = section.sectionId === "recent_developments";
  const isRisk = section.sectionId === "top_risks";
  const riskItems = isRisk ? section.items.slice(0, 3) : section.items;
  const sectionClassName = [
    "asset-prd-section",
    "plain-panel",
    isRecent ? "recent-section" : "stable-section",
    section.sectionType === "evidence_gap" ? "unknown-state" : ""
  ]
    .filter(Boolean)
    .join(" ");
  const sectionCitationIds = uniqueCitationIds([
    ...(section.metrics ?? []).flatMap((metric) => metric.citationIds),
    ...section.items.flatMap((item) => item.citationIds)
  ]);

  return (
    <section
      className={sectionClassName}
      aria-labelledby={`stock-section-${section.sectionId}`}
      data-stock-section-id={section.sectionId}
      data-section-type={section.sectionType}
      data-evidence-state={section.evidenceState}
      data-freshness-state={section.freshnessState}
      data-stock-stable-recent-separation={isRecent ? "recent" : "stable"}
    >
      <div className="section-heading-row">
        <div className="section-heading">
          <p className="eyebrow">
            {isRecent ? "Recent developments" : section.sectionType === "risk" ? "Exactly three shown first" : "Stable stock facts"}
          </p>
          <h2 id={`stock-section-${section.sectionId}`}>{section.title}</h2>
        </div>
        <div className="state-row stock-section-state">
          <span className="state-pill" data-evidence-state={section.evidenceState}>
            Evidence: {section.evidenceState.replaceAll("_", " ")}
          </span>
          <CompactCitationSources
            citations={resolveAssetCitations(asset, sectionCitationIds)}
            label={`${section.title} evidence details`}
            metadataRows={[
              {
                label: "Section freshness",
                value: section.asOfDate ?? section.retrievedAt ?? section.limitations ?? "Unknown in current evidence",
                state: section.freshnessState
              }
            ]}
            dashboardSourceIcon
          />
        </div>
      </div>

      <p>
        <InlineGlossaryText
          text={section.beginnerSummary}
          matches={glossaryMatches}
          contexts={glossaryContexts}
          sourceSection={`stock.${section.sectionId}.summary`}
        />
      </p>

      {section.metrics?.length ? (
        <dl className="fact-list stock-metric-list">
          {section.metrics.map((metric) => (
            <div key={metric.metricId} data-stock-section-metric-id={metric.metricId}>
              <dt>
                <InlineGlossaryText
                  text={metric.label}
                  matches={glossaryMatches}
                  contexts={glossaryContexts}
                  sourceSection={`stock.${section.sectionId}.metric_label`}
                />
              </dt>
              <dd>
                <InlineGlossaryText
                  text={formatStockMetricValue(metric.value)}
                  matches={glossaryMatches}
                  contexts={glossaryContexts}
                  sourceSection={`stock.${section.sectionId}.metric_value`}
                />
                <CompactCitationSources
                  citations={resolveAssetCitations(asset, metric.citationIds)}
                  label={`${metric.label} sources`}
                />
              </dd>
            </div>
          ))}
        </dl>
      ) : null}

      <div
        className={isRisk ? "risk-grid stock-section-items" : "stock-section-items"}
        data-stock-top-risk-count={isRisk ? riskItems.length : undefined}
      >
        {riskItems.map((item) => (
          <StockSectionItemCard
            key={item.itemId}
            asset={asset}
            item={item}
            isRisk={isRisk}
            glossaryMatches={glossaryMatches}
            glossaryContexts={glossaryContexts}
          />
        ))}
      </div>

      {section.limitations ? <p className="notice-text">{section.limitations}</p> : null}
    </section>
  );
}

function StockSectionItemCard({
  asset,
  item,
  isRisk,
  glossaryMatches,
  glossaryContexts
}: {
  asset: AssetFixture;
  item: StockSectionItem;
  isRisk: boolean;
  glossaryMatches: readonly InlineGlossaryMatch[];
  glossaryContexts?: InlineGlossaryContextMap | null;
}) {
  const className = isRisk ? "risk-card" : "stock-section-item";

  return (
    <article
      className={className}
      data-stock-section-item-id={item.itemId}
      data-evidence-state={item.evidenceState}
      data-freshness-state={item.freshnessState}
    >
      <div className="stock-item-heading">
        <h3>
          <InlineGlossaryText
            text={item.title}
            matches={glossaryMatches}
            contexts={glossaryContexts}
            sourceSection="stock.item_title"
          />
        </h3>
        <span className="state-pill compact-state" data-evidence-state={item.evidenceState}>
          {item.evidenceState.replaceAll("_", " ")}
        </span>
      </div>
      <p>
        <InlineGlossaryText
          text={item.summary}
          matches={glossaryMatches}
          contexts={glossaryContexts}
          sourceSection="stock.item_summary"
        />
      </p>
      {item.citationIds.length ? (
        <div className="compact-source-row">
          <CompactCitationSources
            citations={resolveAssetCitations(asset, item.citationIds)}
            label={`${item.title} sources`}
            metadataRows={[
              {
                label: item.eventDate ? "Event date" : "As of",
                value: item.eventDate ?? item.asOfDate ?? item.limitations ?? "Unknown in current evidence",
                state: item.freshnessState
              },
              { label: "Retrieved", value: item.retrievedAt ?? null, state: item.freshnessState }
            ]}
          />
        </div>
      ) : (
        <p className="source-gap-note">No citation chip is shown because this item is an explicit evidence gap.</p>
      )}
    </article>
  );
}

function formatStockMetricValue(value: string | number | null | undefined) {
  if (value === null || value === undefined) {
    return "Unavailable";
  }

  return String(value);
}

function uniqueCitationIds(citationIds: string[]) {
  return [...new Set(citationIds)];
}
