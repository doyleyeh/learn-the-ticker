import {
  citationLabel,
  getCitationById,
  type AssetFixture,
  type EtfOverviewSection,
  type EtfSectionItem
} from "../lib/fixtures";
import { CitationChip } from "./CitationChip";
import { FreshnessLabel } from "./FreshnessLabel";
import { InlineGlossaryText, type InlineGlossaryContextMap, type InlineGlossaryMatch } from "./InlineGlossaryText";

type AssetEtfSectionsProps = {
  asset: AssetFixture;
  glossaryMatches?: readonly InlineGlossaryMatch[];
  glossaryContexts?: InlineGlossaryContextMap | null;
};

export function AssetEtfSections({ asset, glossaryMatches = [], glossaryContexts }: AssetEtfSectionsProps) {
  if (asset.assetType !== "etf" || !asset.etfSections?.length) {
    return null;
  }

  const deepDiveSections = asset.etfSections.filter(
    (section) => !["etf_specific_risks", "recent_developments", "educational_suitability"].includes(section.sectionId)
  );

  return (
    <div
      className="section-stack etf-prd-sections"
      data-etf-prd-sections
      data-asset-ticker={asset.ticker}
      data-shared-prd-section-shell
      data-deep-dive-duplicate-sections-filtered="etf_specific_risks,recent_developments,educational_suitability"
    >
      {deepDiveSections.map((section) => (
        <EtfSection
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

function EtfSection({
  asset,
  section,
  glossaryMatches,
  glossaryContexts
}: {
  asset: AssetFixture;
  section: EtfOverviewSection;
  glossaryMatches: readonly InlineGlossaryMatch[];
  glossaryContexts?: InlineGlossaryContextMap | null;
}) {
  const isRecent = section.sectionId === "recent_developments";
  const isRisk = section.sectionId === "etf_specific_risks";
  const riskItems = isRisk ? section.items.slice(0, 3) : section.items;
  const sectionClassName = [
    "asset-prd-section",
    "plain-panel",
    isRecent ? "recent-section" : "stable-section",
    section.sectionType === "evidence_gap" ? "unknown-state" : ""
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <section
      className={sectionClassName}
      aria-labelledby={`etf-section-${section.sectionId}`}
      data-etf-section-id={section.sectionId}
      data-section-type={section.sectionType}
      data-evidence-state={section.evidenceState}
      data-freshness-state={section.freshnessState}
      data-etf-stable-recent-separation={isRecent ? "recent" : "stable"}
    >
      <div className="section-heading">
        <p className="eyebrow">
          {isRecent ? "Recent developments" : section.sectionType === "risk" ? "Exactly three shown first" : "Stable ETF facts"}
        </p>
        <h2 id={`etf-section-${section.sectionId}`}>{section.title}</h2>
      </div>

      <div className="state-row etf-section-state">
        <FreshnessLabel
          label="Section freshness"
          value={section.asOfDate ?? section.retrievedAt ?? section.limitations ?? "Unknown in local fixture"}
          state={section.freshnessState}
        />
        <span className="state-pill" data-evidence-state={section.evidenceState}>
          Evidence: {section.evidenceState.replaceAll("_", " ")}
        </span>
      </div>

      <p>
        <InlineGlossaryText
          text={section.beginnerSummary}
          matches={glossaryMatches}
          contexts={glossaryContexts}
          sourceSection={`etf.${section.sectionId}.summary`}
        />
      </p>

      {section.metrics?.length ? (
        <dl className="fact-list etf-metric-list">
          {section.metrics.map((metric) => (
            <div key={metric.metricId} data-etf-section-metric-id={metric.metricId}>
              <dt>
                <InlineGlossaryText
                  text={metric.label}
                  matches={glossaryMatches}
                  contexts={glossaryContexts}
                  sourceSection={`etf.${section.sectionId}.metric_label`}
                />
              </dt>
              <dd>
                <InlineGlossaryText
                  text={formatMetricValue(metric.value, metric.unit)}
                  matches={glossaryMatches}
                  contexts={glossaryContexts}
                  sourceSection={`etf.${section.sectionId}.metric_value`}
                />{" "}
                <CitationChips asset={asset} citationIds={metric.citationIds} />
              </dd>
            </div>
          ))}
        </dl>
      ) : null}

      <div
        className={isRisk ? "risk-grid etf-section-items" : "etf-section-items"}
        data-etf-top-risk-count={isRisk ? riskItems.length : undefined}
      >
        {riskItems.map((item) => (
          <EtfSectionItemCard
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

function EtfSectionItemCard({
  asset,
  item,
  isRisk,
  glossaryMatches,
  glossaryContexts
}: {
  asset: AssetFixture;
  item: EtfSectionItem;
  isRisk: boolean;
  glossaryMatches: readonly InlineGlossaryMatch[];
  glossaryContexts?: InlineGlossaryContextMap | null;
}) {
  const className = isRisk ? "risk-card" : "etf-section-item";

  return (
    <article
      className={className}
      data-etf-section-item-id={item.itemId}
      data-evidence-state={item.evidenceState}
      data-freshness-state={item.freshnessState}
    >
      <div className="etf-item-heading">
        <h3>
          <InlineGlossaryText
            text={item.title}
            matches={glossaryMatches}
            contexts={glossaryContexts}
            sourceSection="etf.item_title"
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
          sourceSection="etf.item_summary"
        />
      </p>
      <div className="state-row">
        <FreshnessLabel
          label={item.eventDate ? "Event date" : "As of"}
          value={item.eventDate ?? item.asOfDate ?? item.limitations ?? "Unknown in local fixture"}
          state={item.freshnessState}
        />
        {item.retrievedAt ? <FreshnessLabel label="Retrieved" value={item.retrievedAt} state={item.freshnessState} /> : null}
      </div>
      {item.citationIds.length ? (
        <span className="chip-row">
          <CitationChips asset={asset} citationIds={item.citationIds} />
        </span>
      ) : (
        <p className="source-gap-note">No citation chip is shown because this ETF item is an explicit evidence gap.</p>
      )}
    </article>
  );
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

function formatMetricValue(value: string | number | null | undefined, unit: string | null | undefined) {
  if (value === null || value === undefined) {
    return "Unavailable";
  }

  return unit ? `${value}${unit}` : String(value);
}
