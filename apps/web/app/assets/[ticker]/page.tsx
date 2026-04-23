import { notFound } from "next/navigation";
import { AssetHeader } from "../../../components/AssetHeader";
import { AIComprehensiveAnalysisPanel } from "../../../components/AIComprehensiveAnalysisPanel";
import { AssetChatPanel } from "../../../components/AssetChatPanel";
import { AssetEtfSections } from "../../../components/AssetEtfSections";
import { AssetStockSections } from "../../../components/AssetStockSections";
import { AssetModeLayout } from "../../../components/AssetModeLayout";
import { CitationChip } from "../../../components/CitationChip";
import { ComparisonSuggestions } from "../../../components/ComparisonSuggestions";
import { ExportControls } from "../../../components/ExportControls";
import { FreshnessLabel } from "../../../components/FreshnessLabel";
import { GlossaryPopover } from "../../../components/GlossaryPopover";
import { SourceDrawer } from "../../../components/SourceDrawer";
import { WeeklyNewsPanel } from "../../../components/WeeklyNewsPanel";
import { beginnerGlossaryGroupsByAssetType } from "../../../lib/glossary";
import { getAssetComparisonSuggestions } from "../../../lib/compareSuggestions";
import { assetPageExportUrl, assetSourceListExportUrl } from "../../../lib/exportControls";
import {
  getAIComprehensiveAnalysisFixture,
  assetFixtures,
  citationLabel,
  getCitationById,
  getCitationContextsForSource,
  getPrimarySource,
  getAssetFixture,
  toSourceDrawerDocument,
  getWeeklyNewsFocusFixture
} from "../../../lib/fixtures";

type AssetPageProps = {
  params: Promise<{
    ticker: string;
  }>;
};

type SourceDrawerState =
  | "available"
  | "unsupported"
  | "out_of_scope"
  | "unknown"
  | "eligible_not_cached"
  | "deleted"
  | "stale"
  | "partial"
  | "unavailable"
  | "insufficient_evidence";

function sourceDrawerStateFromFreshness(freshnessState: string): SourceDrawerState {
  if (freshnessState === "fresh") {
    return "available";
  }
  if (freshnessState === "stale") {
    return "stale";
  }
  if (freshnessState === "unknown") {
    return "unknown";
  }
  if (freshnessState === "unavailable") {
    return "unavailable";
  }
  if (freshnessState === "partial") {
    return "partial";
  }
  if (freshnessState === "insufficient_evidence") {
    return "insufficient_evidence";
  }
  return "unknown";
}

export function generateStaticParams() {
  return Object.keys(assetFixtures).map((ticker) => ({ ticker }));
}

export default async function AssetPage({ params }: AssetPageProps) {
  const { ticker } = await params;
  const asset = getAssetFixture(ticker);

  if (!asset) {
    notFound();
  }

  const weeklyNewsFocus = getWeeklyNewsFocusFixture(asset.ticker);
  const aiComprehensiveAnalysis = getAIComprehensiveAnalysisFixture(asset.ticker);

  if (!weeklyNewsFocus || !aiComprehensiveAnalysis) {
    notFound();
  }

  const primarySource = getPrimarySource(asset);
  const firstClaim = asset.claims[0];
  const firstClaimCitation = getCitationById(asset, firstClaim.citationIds[0]) ?? asset.citations[0];
  const hasStockPrdSections = asset.assetType === "stock" && Boolean(asset.stockSections?.length);
  const hasEtfPrdSections = asset.assetType === "etf" && Boolean(asset.etfSections?.length);
  const hasPrdSections = hasStockPrdSections || hasEtfPrdSections;
  const sectionSourceDocumentIds = new Set(
    [...(asset.stockSections ?? []), ...(asset.etfSections ?? [])].flatMap((section) => section.sourceDocumentIds)
  );
  const mergedCitations = [
    ...asset.citations,
    ...weeklyNewsFocus.citations,
    ...aiComprehensiveAnalysis.citations
  ].filter((citation, index, collection) => collection.findIndex((entry) => entry.citationId === citation.citationId) === index);
  const mergedSources = [
    ...asset.sourceDocuments,
    ...weeklyNewsFocus.sourceDocuments,
    ...aiComprehensiveAnalysis.sourceDocuments
  ].filter(
    (source, index, collection) =>
      collection.findIndex((entry) => entry.sourceDocumentId === source.sourceDocumentId) === index
  );
  const timelyContextSourceDocumentIds = new Set([
    ...weeklyNewsFocus.sourceDocuments.map((source) => source.sourceDocumentId),
    ...aiComprehensiveAnalysis.sourceDocumentIds
  ]);
  const drawerSourceDocumentIds = new Set([...sectionSourceDocumentIds, ...timelyContextSourceDocumentIds]);
  const drawerSources = mergedSources
    .filter((source) => drawerSourceDocumentIds.has(source.sourceDocumentId))
    .map(toSourceDrawerDocument);
  const timelyContextClaimsBySourceDocumentId = new Map(
    weeklyNewsFocus.items.map((item) => [
      item.source.sourceDocumentId,
      `Weekly News Focus: ${item.title}. ${item.summary}`
    ])
  );
  for (const sourceDocumentId of aiComprehensiveAnalysis.sourceDocumentIds) {
    if (!timelyContextClaimsBySourceDocumentId.has(sourceDocumentId)) {
      timelyContextClaimsBySourceDocumentId.set(
        sourceDocumentId,
        `AI Comprehensive Analysis cites this source while keeping timely context separate from stable facts for ${asset.ticker}.`
      );
    }
  }
  const glossaryGroups = beginnerGlossaryGroupsByAssetType[asset.assetType];
  const comparisonSuggestions = getAssetComparisonSuggestions(asset.ticker);
  const inlineGlossaryTerms =
    asset.assetType === "etf" ? (["expense ratio", "index tracking"] as const) : (["market risk", "P/E ratio"] as const);

  return (
    <main>
      <AssetHeader asset={asset} />
      <AssetModeLayout
        asset={asset}
        beginnerMode={
          <>
            <section
              className="plain-panel stable-section"
              aria-labelledby="beginner-overview"
              data-beginner-stable-recent-separation="stable"
              data-beginner-primary-claim={firstClaim.claimId}
            >
              <div className="section-heading">
                <p className="eyebrow">Stable facts</p>
                <h2 id="beginner-overview">Beginner overview</h2>
              </div>
              <div className="state-row">
                <FreshnessLabel label="Page last updated" value={asset.freshness.pageLastUpdatedAt} state="fresh" />
                <FreshnessLabel label="Beginner overview as of" value={asset.freshness.factsAsOf} state="fresh" />
              </div>
              <p>
                {asset.beginnerSummary.whatItIs} <CitationChip citation={firstClaimCitation} />
              </p>
              <p>{asset.beginnerSummary.whyPeopleConsiderIt}</p>
              <p className="notice-text">{asset.beginnerSummary.mainCatch}</p>
              <div className="inline-tools" aria-label="Beginner glossary terms">
                {inlineGlossaryTerms.map((term) => (
                  <GlossaryPopover key={term} term={term} />
                ))}
              </div>
            </section>

            <section
              className="plain-panel stable-section glossary-learning-panel"
              aria-labelledby={`beginner-glossary-${asset.ticker.toLowerCase()}`}
              data-beginner-stable-recent-separation="stable"
              data-beginner-glossary-area
              data-glossary-asset-ticker={asset.ticker}
              data-glossary-asset-type={asset.assetType}
              data-glossary-no-generated-context
            >
              <div className="section-heading">
                <p className="eyebrow">Learning terms</p>
                <h2 id={`beginner-glossary-${asset.ticker.toLowerCase()}`}>Glossary for this page</h2>
              </div>
              <div className="glossary-group-grid">
                {glossaryGroups.map((group) => (
                  <article className="glossary-term-group" key={group.groupId} data-glossary-term-group={group.groupId}>
                    <h3>{group.title}</h3>
                    <div className="inline-tools glossary-term-list" data-glossary-term-list={group.groupId}>
                      {group.terms.map((term) => (
                        <GlossaryPopover key={term} term={term} />
                      ))}
                    </div>
                  </article>
                ))}
              </div>
              <p className="source-gap-note" data-glossary-generic-education>
                Generic glossary entries do not create asset facts, citation chips, or source documents.
              </p>
            </section>

            <section
              className="plain-panel stable-section"
              aria-labelledby="beginner-top-risks"
              data-beginner-stable-recent-separation="stable"
              data-beginner-top-risks
            >
              <div className="section-heading">
                <p className="eyebrow">Exactly three shown first</p>
                <h2 id="beginner-top-risks">Top risks</h2>
              </div>
              <FreshnessLabel label="Top risks as of" value={asset.freshness.factsAsOf} state="fresh" />
              <div className="risk-grid" data-beginner-top-risk-count={asset.topRisks.slice(0, 3).length}>
                {asset.topRisks.slice(0, 3).map((risk) => {
                  const citation = getCitationById(asset, risk.citationIds[0]);
                  return (
                    <article className="risk-card" key={risk.title}>
                      <h3>{risk.title}</h3>
                      <p>{risk.plainEnglishExplanation}</p>
                      {citation ? <CitationChip citation={citation} label={citationLabel(risk.citationIds[0])} /> : null}
                    </article>
                  );
                })}
              </div>
            </section>

            <section
              className="plain-panel stable-section"
              aria-labelledby="beginner-details"
              data-beginner-stable-recent-separation="stable"
            >
              <div className="section-heading">
                <p className="eyebrow">What this is</p>
                <h2 id="beginner-details">{asset.assetType === "etf" ? "Fund facts" : "Business facts"}</h2>
              </div>
              <FreshnessLabel label="Stable facts as of" value={asset.freshness.factsAsOf} state="fresh" />
              <dl className="fact-list">
                {asset.facts.map((fact) => {
                  const citation = fact.citationId ? getCitationById(asset, fact.citationId) : undefined;
                  return (
                    <div key={fact.label}>
                      <dt>{fact.label}</dt>
                      <dd>
                        {fact.value}{" "}
                        {citation ? <CitationChip citation={citation} label={citationLabel(fact.citationId ?? "")} /> : null}
                      </dd>
                    </div>
                  );
                })}
              </dl>
            </section>

            <WeeklyNewsPanel focus={weeklyNewsFocus} citations={mergedCitations} />

            <AIComprehensiveAnalysisPanel analysis={aiComprehensiveAnalysis} citations={mergedCitations} />

            <section className="plain-panel" aria-labelledby="beginner-educational-framing" data-beginner-educational-framing>
              <div className="section-heading">
                <p className="eyebrow">Educational framing</p>
                <h2 id="beginner-educational-framing">Educational suitability</h2>
              </div>
              <p>{asset.suitabilitySummary.mayFit}</p>
              <p>{asset.suitabilitySummary.mayNotFit}</p>
              <p>{asset.suitabilitySummary.learnNext}</p>
            </section>

            <ComparisonSuggestions model={comparisonSuggestions} />

            <AssetChatPanel ticker={asset.ticker} assetName={asset.name} />
          </>
        }
        deepDiveMode={
          hasStockPrdSections ? (
            <AssetStockSections asset={asset} />
          ) : hasEtfPrdSections ? (
            <AssetEtfSections asset={asset} />
          ) : (
            <section className="plain-panel unknown-state" aria-labelledby="unknowns">
              <div className="section-heading">
                <p className="eyebrow">Uncertainty</p>
                <h2 id="unknowns">Stale and unknown treatment</h2>
              </div>
              <div className="state-row">
                <FreshnessLabel label="Valuation context" value="Unknown in local fixture" state="unknown" />
                <FreshnessLabel label="Live market quote" value="Unavailable by design" state="stale" />
              </div>
              <p>
                Missing live facts are labeled instead of being filled in from model memory. This skeleton uses local fixture
                data only.
              </p>
            </section>
          )
        }
        sourceTools={
          <>
            <ExportControls
              title={`Save ${asset.ticker} learning output`}
              marker={`asset-export-${asset.ticker.toLowerCase()}`}
              controls={[
                {
                  kind: "link",
                  controlId: "asset-page",
                  label: "Open asset-page Markdown export",
                  href: assetPageExportUrl(asset.ticker),
                  helper: "Includes page sections, citation IDs, freshness labels, disclaimer, and licensing scope."
                },
                {
                  kind: "link",
                  controlId: "asset-source-list",
                  label: "Open source-list Markdown export",
                  href: assetSourceListExportUrl(asset.ticker),
                  helper: "Includes source titles, publishers, URLs, dates, retrieved timestamps, and allowed excerpts."
                }
              ]}
            />
            {hasPrdSections ? (
              drawerSources.map((source) => (
                <SourceDrawer
                  key={source.source_document_id}
                  source={source}
                  claim={
                    getCitationContextsForSource(asset, source.source_document_id)[0]?.claimContext ??
                    timelyContextClaimsBySourceDocumentId.get(source.source_document_id) ??
                    firstClaim.claimText
                  }
                  contexts={getCitationContextsForSource(asset, source.source_document_id)}
                  drawerState={sourceDrawerStateFromFreshness(source.freshness_state)}
                />
              ))
            ) : (
              <SourceDrawer
                source={toSourceDrawerDocument(primarySource)}
                claim={firstClaim.claimText}
                drawerState={sourceDrawerStateFromFreshness(primarySource.freshnessState)}
              />
            )}
          </>
        }
      />
    </main>
  );
}
