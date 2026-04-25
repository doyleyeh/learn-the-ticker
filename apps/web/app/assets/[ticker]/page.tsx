import { notFound } from "next/navigation";
import { AssetHeader } from "../../../components/AssetHeader";
import { AIComprehensiveAnalysisPanel } from "../../../components/AIComprehensiveAnalysisPanel";
import { AssetChatPanel } from "../../../components/AssetChatPanel";
import { AssetEtfSections } from "../../../components/AssetEtfSections";
import { AssetStockSections } from "../../../components/AssetStockSections";
import { AssetLearningLayout } from "../../../components/AssetModeLayout";
import { CitationChip } from "../../../components/CitationChip";
import { ComparisonSuggestions } from "../../../components/ComparisonSuggestions";
import { ExportControls } from "../../../components/ExportControls";
import { FreshnessLabel } from "../../../components/FreshnessLabel";
import { InlineGlossaryText, type InlineGlossaryMatch } from "../../../components/InlineGlossaryText";
import { WeeklyNewsPanel } from "../../../components/WeeklyNewsPanel";
import { fetchSupportedAssetDetails } from "../../../lib/assetDetails";
import { fetchSupportedAssetGlossaryContexts } from "../../../lib/assetGlossary";
import { fetchSupportedAssetOverview } from "../../../lib/assetOverview";
import { fetchSupportedSourceDrawerResponse, sourceDrawerEntriesByDocumentId } from "../../../lib/sourceDrawer";
import { fetchSupportedAssetWeeklyNews } from "../../../lib/assetWeeklyNews";
import { beginnerGlossaryGroupsByAssetType, type GlossaryTermKey } from "../../../lib/glossary";
import { getAssetComparisonSuggestions } from "../../../lib/compareSuggestions";
import {
  assetPageExportUrl,
  assetSourceListExportUrl,
  fetchSupportedAssetExportContract,
  type AssetExportContractValidation
} from "../../../lib/exportControls";
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
  const fallbackAsset = getAssetFixture(ticker);

  if (!fallbackAsset) {
    notFound();
  }

  let asset = fallbackAsset;
  let overviewRendering: "backend_contract" | "local_fixture" = "local_fixture";
  let detailsRendering: "backend_contract" | "local_fixture" = "local_fixture";
  let weeklyNewsRendering: "backend_contract" | "local_fixture" = "local_fixture";
  let sourceDrawerRendering: "backend_contract" | "mixed_fallback" | "local_fixture" = "local_fixture";
  let glossaryRendering: "backend_contract" | "local_fixture" = "local_fixture";
  let assetPageExportContract: AssetExportContractValidation | null = null;
  let assetSourceListExportContract: AssetExportContractValidation | null = null;

  try {
    asset = await fetchSupportedAssetOverview(fallbackAsset.ticker, fallbackAsset);
    overviewRendering = "backend_contract";
  } catch {
    asset = fallbackAsset;
  }

  try {
    asset = await fetchSupportedAssetDetails(asset.ticker, asset);
    detailsRendering = "backend_contract";
  } catch {
    detailsRendering = "local_fixture";
  }

  let weeklyNewsFocus = getWeeklyNewsFocusFixture(asset.ticker);
  let aiComprehensiveAnalysis = getAIComprehensiveAnalysisFixture(asset.ticker);

  if (!weeklyNewsFocus || !aiComprehensiveAnalysis) {
    notFound();
  }

  try {
    const backendWeeklyNews = await fetchSupportedAssetWeeklyNews(
      asset.ticker,
      weeklyNewsFocus,
      aiComprehensiveAnalysis,
      asset.assetType
    );
    weeklyNewsFocus = backendWeeklyNews.weeklyNewsFocus;
    aiComprehensiveAnalysis = backendWeeklyNews.aiComprehensiveAnalysis;
    weeklyNewsRendering = "backend_contract";
  } catch {
    weeklyNewsRendering = "local_fixture";
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
  const backendSourceDrawer = await (async () => {
    try {
      return await fetchSupportedSourceDrawerResponse(asset.ticker);
    } catch {
      return null;
    }
  })();
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
  const additionalInlineGlossaryTerms: GlossaryTermKey[] = asset.assetType === "etf" ? ["market risk"] : [];
  const glossaryTermsForBackend = [
    ...new Set<GlossaryTermKey>([...glossaryGroups.flatMap((group) => group.terms), ...additionalInlineGlossaryTerms])
  ];
  const inlineGlossaryMatches: InlineGlossaryMatch[] = [...glossaryTermsForBackend];
  if (asset.assetType === "stock") {
    inlineGlossaryMatches.push({ match: "P/E", term: "P/E ratio" });
  }
  const backendGlossaryContexts = await (async () => {
    try {
      return await fetchSupportedAssetGlossaryContexts(asset.ticker, glossaryTermsForBackend);
    } catch {
      return null;
    }
  })();
  if (backendGlossaryContexts) {
    glossaryRendering = "backend_contract";
  }
  const comparisonSuggestions = getAssetComparisonSuggestions(asset.ticker);
  try {
    assetPageExportContract = await fetchSupportedAssetExportContract(asset.ticker, "asset_page");
  } catch {
    assetPageExportContract = null;
  }
  try {
    assetSourceListExportContract = await fetchSupportedAssetExportContract(asset.ticker, "asset_source_list");
  } catch {
    assetSourceListExportContract = null;
  }
  const localDrawerEntries = drawerSources.map((source) => {
    const sourceContexts = getCitationContextsForSource(asset, source.source_document_id);
    return {
      source,
      claim:
        sourceContexts[0]?.claimContext ??
        timelyContextClaimsBySourceDocumentId.get(source.source_document_id) ??
        firstClaim.claimText,
      contexts: sourceContexts,
      drawerState: sourceDrawerStateFromFreshness(source.freshness_state)
    };
  });
  const primarySourceEntry = {
    source: toSourceDrawerDocument(primarySource),
    claim: firstClaim.claimText,
    contexts: getCitationContextsForSource(asset, primarySource.sourceDocumentId),
    drawerState: sourceDrawerStateFromFreshness(primarySource.freshnessState)
  };
  const backendDrawerEntries = backendSourceDrawer ? sourceDrawerEntriesByDocumentId(backendSourceDrawer) : null;
  const overlaySourceDrawerEntry = <T extends { source: { source_document_id: string } }>(entry: T) =>
    backendDrawerEntries?.get(entry.source.source_document_id) ?? entry;
  const renderedDrawerEntries = hasPrdSections
    ? localDrawerEntries.map(overlaySourceDrawerEntry)
    : [overlaySourceDrawerEntry(primarySourceEntry)];
  const whatItDoesOrHoldsSection =
    asset.assetType === "etf"
      ? asset.etfSections?.find((section) => section.sectionId === "holdings_exposure")
      : asset.stockSections?.find((section) => section.sectionId === "business_overview");
  const whatItDoesOrHoldsItems = whatItDoesOrHoldsSection?.items.slice(0, 2) ?? [];
  const keySourceTitles = renderedDrawerEntries.slice(0, 3).map((entry) => entry.source.title);

  if (backendDrawerEntries) {
    sourceDrawerRendering = renderedDrawerEntries.every((entry) => backendDrawerEntries.has(entry.source.source_document_id))
      ? "backend_contract"
      : "mixed_fallback";
  }

  return (
    <main
      data-asset-overview-rendering={overviewRendering}
      data-asset-details-rendering={detailsRendering}
      data-asset-weekly-news-rendering={weeklyNewsRendering}
      data-asset-source-drawer-rendering={sourceDrawerRendering}
      data-asset-glossary-rendering={glossaryRendering}
      data-asset-page-export-contract={assetPageExportContract?.rendering ?? "local_fallback"}
      data-asset-source-list-export-contract={assetSourceListExportContract?.rendering ?? "local_fallback"}
      data-prd-layout-marker="supported-asset-page-learning-flow-v1"
      data-prd-section-order="header,beginner_summary,top_risks,key_facts,what_it_does_or_holds,weekly_news_focus,ai_comprehensive_analysis,deep_dive,ask_about_this_asset,sources,educational_disclaimer"
    >
      <AssetHeader asset={asset} layoutMarker="header" />
      <AssetLearningLayout
        asset={asset}
        beginnerSections={
          <>
            <section
              className="plain-panel stable-section"
              aria-labelledby="beginner-overview"
              data-beginner-stable-recent-separation="stable"
              data-beginner-primary-claim={firstClaim.claimId}
              data-prd-section="beginner_summary"
            >
              <div className="section-heading">
                <p className="eyebrow">Stable facts</p>
                <h2 id="beginner-overview">Beginner Summary</h2>
              </div>
              <div className="state-row">
                <FreshnessLabel label="Page last updated" value={asset.freshness.pageLastUpdatedAt} state="fresh" />
                <FreshnessLabel label="Beginner overview as of" value={asset.freshness.factsAsOf} state="fresh" />
              </div>
              <div
                className="beginner-summary-grid"
                data-beginner-summary-card-count="3"
                data-beginner-summary-card-layout="three_short_cards"
              >
                <article className="beginner-summary-card" data-beginner-summary-card="what_it_is">
                  <h3>What it is</h3>
                  <p>
                    <InlineGlossaryText
                      text={asset.beginnerSummary.whatItIs}
                      matches={inlineGlossaryMatches}
                      contexts={backendGlossaryContexts}
                      sourceSection="beginner_summary.what_it_is"
                    />{" "}
                    <CitationChip citation={firstClaimCitation} />
                  </p>
                </article>
                <article className="beginner-summary-card" data-beginner-summary-card="why_people_look">
                  <h3>Why people look at it</h3>
                  <p>
                    <InlineGlossaryText
                      text={asset.beginnerSummary.whyPeopleConsiderIt}
                      matches={inlineGlossaryMatches}
                      contexts={backendGlossaryContexts}
                      sourceSection="beginner_summary.why_people_look"
                    />
                  </p>
                </article>
                <article className="beginner-summary-card caution-card" data-beginner-summary-card="main_caution">
                  <h3>Main thing to be careful about</h3>
                  <p>
                    <InlineGlossaryText
                      text={asset.beginnerSummary.mainCatch}
                      matches={inlineGlossaryMatches}
                      contexts={backendGlossaryContexts}
                      sourceSection="beginner_summary.main_caution"
                    />
                  </p>
                </article>
              </div>
            </section>

            <section
              className="plain-panel stable-section"
              aria-labelledby="beginner-top-risks"
              data-beginner-stable-recent-separation="stable"
              data-beginner-top-risks
              data-prd-section="top_risks"
            >
              <div className="section-heading">
                <p className="eyebrow">Exactly three shown first</p>
                <h2 id="beginner-top-risks">Top 3 Risks</h2>
              </div>
              <FreshnessLabel label="Top risks as of" value={asset.freshness.factsAsOf} state="fresh" />
              <div className="risk-grid" data-beginner-top-risk-count={asset.topRisks.slice(0, 3).length}>
                {asset.topRisks.slice(0, 3).map((risk) => {
                  const citation = getCitationById(asset, risk.citationIds[0]);
                  return (
                    <article className="risk-card" key={risk.title}>
                      <h3>
                        <InlineGlossaryText
                          text={risk.title}
                          matches={inlineGlossaryMatches}
                          contexts={backendGlossaryContexts}
                          sourceSection="top_risks.title"
                        />
                      </h3>
                      <p>
                        <InlineGlossaryText
                          text={risk.plainEnglishExplanation}
                          matches={inlineGlossaryMatches}
                          contexts={backendGlossaryContexts}
                          sourceSection="top_risks.explanation"
                        />
                      </p>
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
              data-prd-section="key_facts"
            >
              <div className="section-heading">
                <p className="eyebrow">Key facts</p>
                <h2 id="beginner-details">Key Facts</h2>
              </div>
              <FreshnessLabel label="Stable facts as of" value={asset.freshness.factsAsOf} state="fresh" />
              <dl className="fact-list">
                {asset.facts.map((fact) => {
                  const citation = fact.citationId ? getCitationById(asset, fact.citationId) : undefined;
                  return (
                    <div key={fact.label}>
                      <dt>
                        <InlineGlossaryText
                          text={fact.label}
                          matches={inlineGlossaryMatches}
                          contexts={backendGlossaryContexts}
                          sourceSection="key_facts.label"
                        />
                      </dt>
                      <dd>
                        <InlineGlossaryText
                          text={fact.value}
                          matches={inlineGlossaryMatches}
                          contexts={backendGlossaryContexts}
                          sourceSection="key_facts.value"
                        />{" "}
                        {citation ? <CitationChip citation={citation} label={citationLabel(fact.citationId ?? "")} /> : null}
                      </dd>
                    </div>
                  );
                })}
              </dl>
            </section>

            <section
              className="plain-panel stable-section"
              aria-labelledby="beginner-what-it-does-or-holds"
              data-beginner-stable-recent-separation="stable"
              data-prd-section="what_it_does_or_holds"
              data-asset-what-section-id={whatItDoesOrHoldsSection?.sectionId ?? "primary_claim_fallback"}
            >
              <div className="section-heading">
                <p className="eyebrow">Stable facts</p>
                <h2 id="beginner-what-it-does-or-holds">
                  {asset.assetType === "etf" ? "What It Holds" : "What It Does"}
                </h2>
              </div>
              <div className="state-row">
                <FreshnessLabel
                  label={asset.assetType === "etf" ? "Holdings as of" : "Business facts as of"}
                  value={
                    asset.assetType === "etf"
                      ? asset.freshness.holdingsAsOf ?? "Unknown in local fixture"
                      : asset.freshness.factsAsOf
                  }
                  state={asset.assetType === "etf" && !asset.freshness.holdingsAsOf ? "unknown" : "fresh"}
                />
                {whatItDoesOrHoldsSection ? (
                  <span className="state-pill" data-evidence-state={whatItDoesOrHoldsSection.evidenceState}>
                    Evidence: {whatItDoesOrHoldsSection.evidenceState.replaceAll("_", " ")}
                  </span>
                ) : null}
              </div>
              <p>
                <InlineGlossaryText
                  text={whatItDoesOrHoldsSection?.beginnerSummary ?? firstClaim.claimText}
                  matches={inlineGlossaryMatches}
                  contexts={backendGlossaryContexts}
                  sourceSection="what_it_does_or_holds.summary"
                />{" "}
                {!whatItDoesOrHoldsSection ? <CitationChip citation={firstClaimCitation} /> : null}
              </p>
              {whatItDoesOrHoldsItems.length ? (
                <div className="stock-section-items" data-asset-what-it-does-or-holds-items={whatItDoesOrHoldsItems.length}>
                  {whatItDoesOrHoldsItems.map((item) => (
                    <article className="stock-section-item" key={item.itemId} data-asset-what-item-id={item.itemId}>
                      <div className="stock-item-heading">
                        <h3>
                          <InlineGlossaryText
                            text={item.title}
                            matches={inlineGlossaryMatches}
                            contexts={backendGlossaryContexts}
                            sourceSection="what_it_does_or_holds.item_title"
                          />
                        </h3>
                        <span className="state-pill compact-state" data-evidence-state={item.evidenceState}>
                          {item.evidenceState.replaceAll("_", " ")}
                        </span>
                      </div>
                      <p>
                        <InlineGlossaryText
                          text={item.summary}
                          matches={inlineGlossaryMatches}
                          contexts={backendGlossaryContexts}
                          sourceSection="what_it_does_or_holds.item_summary"
                        />
                      </p>
                      <span className="chip-row">
                        {item.citationIds.map((citationId) => {
                          const citation = getCitationById(asset, citationId);
                          return citation ? (
                            <CitationChip key={citationId} citation={citation} label={citationLabel(citationId)} />
                          ) : null;
                        })}
                      </span>
                    </article>
                  ))}
                </div>
              ) : null}
            </section>

            <WeeklyNewsPanel focus={weeklyNewsFocus} citations={mergedCitations} />

            <AIComprehensiveAnalysisPanel analysis={aiComprehensiveAnalysis} citations={mergedCitations} />
          </>
        }
        deepDiveSections={
          <>
            {hasStockPrdSections ? (
              <AssetStockSections
                asset={asset}
                glossaryMatches={inlineGlossaryMatches}
                glossaryContexts={backendGlossaryContexts}
              />
            ) : hasEtfPrdSections ? (
              <AssetEtfSections
                asset={asset}
                glossaryMatches={inlineGlossaryMatches}
                glossaryContexts={backendGlossaryContexts}
              />
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
            )}

          </>
        }
        afterDeepDive={
          <section id="ask-about-this-asset" className="asset-section-region" data-prd-section="ask_about_this_asset">
            <AssetChatPanel ticker={asset.ticker} assetName={asset.name} />
          </section>
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
                  helper: "Includes page sections, citation IDs, freshness labels, disclaimer, and licensing scope.",
                  contract: assetPageExportContract
                },
                {
                  kind: "link",
                  controlId: "asset-source-list",
                  label: "Open source-list Markdown export",
                  href: assetSourceListExportUrl(asset.ticker),
                  helper: "Includes source titles, publishers, URLs, dates, retrieved timestamps, and allowed excerpts.",
                  contract: assetSourceListExportContract
                }
              ]}
            />
            <p className="source-gap-note">
              Key source documents stay compact on the asset page. Open the source-list view for the full source drawer
              metadata, related claim context, source-use policy, and allowed excerpts.
            </p>
            <div
              className="asset-source-index"
              aria-label={`${asset.ticker} key source documents`}
              data-asset-source-index
              data-asset-source-entry-count={renderedDrawerEntries.length}
              data-asset-source-full-drawers="dedicated-source-list"
              data-asset-source-drawer-repetition="removed"
            >
              {renderedDrawerEntries.map((entry) => (
                <article
                  key={entry.source.source_document_id}
                  id={`source-${entry.source.source_document_id}`}
                  className="asset-source-index-card"
                  data-asset-source-index-entry
                  data-source-document-id={entry.source.source_document_id}
                  data-source-drawer-state={entry.drawerState}
                  data-source-freshness-state={entry.source.freshness_state}
                  data-source-use-policy={entry.source.source_use_policy}
                >
                  <div className="source-title-row">
                    <div>
                      <p className="eyebrow">{entry.source.source_type}</p>
                      <h3>{entry.source.title}</h3>
                    </div>
                    {entry.source.isOfficial ? <span className="source-badge">Official source</span> : null}
                  </div>
                  <dl className="source-meta compact-source-meta">
                    <div>
                      <dt>Publisher</dt>
                      <dd>{entry.source.publisher}</dd>
                    </div>
                    <div>
                      <dt>Freshness</dt>
                      <dd>{entry.source.freshness_state}</dd>
                    </div>
                    <div>
                      <dt>Source-use policy</dt>
                      <dd>{entry.source.source_use_policy}</dd>
                    </div>
                    <div>
                      <dt>Related claims</dt>
                      <dd>{entry.contexts.length || 1}</dd>
                    </div>
                  </dl>
                  <a
                    href={`/assets/${asset.ticker}/sources#source-${entry.source.source_document_id}`}
                    data-asset-source-list-link
                  >
                    Open full source details
                  </a>
                </article>
              ))}
            </div>
          </>
        }
        helperRail={
          <>
            <section className="plain-panel helper-rail-panel" aria-labelledby="helper-rail-actions">
              <div className="section-heading">
                <p className="eyebrow">Page tools</p>
                <h2 id="helper-rail-actions">Asset helpers</h2>
              </div>
              <div className="helper-action-list" data-helper-rail-action-list>
                <a href="#ask-about-this-asset" data-helper-rail-action="ask">
                  Ask about this asset
                </a>
                <a href="#compare-this-asset" data-helper-rail-action="compare">
                  Compare this asset
                </a>
                <a href="#asset-sources" data-helper-rail-action="sources">
                  View sources
                </a>
              </div>
            </section>

            <section className="plain-panel helper-rail-panel" aria-labelledby="helper-rail-freshness">
              <div className="section-heading">
                <p className="eyebrow">Freshness summary</p>
                <h2 id="helper-rail-freshness">Freshness</h2>
              </div>
              <div className="section-stack">
                <FreshnessLabel label="Page last updated" value={asset.freshness.pageLastUpdatedAt} state="fresh" />
                <FreshnessLabel label="Facts as of" value={asset.freshness.factsAsOf} state="fresh" />
                <FreshnessLabel
                  label="Weekly focus as of"
                  value={weeklyNewsFocus.window.asOfDate}
                  state={
                    weeklyNewsFocus.state === "available"
                      ? "fresh"
                      : weeklyNewsFocus.state === "no_high_signal"
                        ? "insufficient_evidence"
                        : weeklyNewsFocus.state === "suppressed"
                          ? "unavailable"
                          : "unknown"
                  }
                />
              </div>
            </section>

            <div id="compare-this-asset" data-helper-rail-comparison-access>
              <ComparisonSuggestions model={comparisonSuggestions} />
            </div>

            <section className="plain-panel helper-rail-panel" aria-labelledby="helper-rail-sources">
              <div className="section-heading">
                <p className="eyebrow">Key sources</p>
                <h2 id="helper-rail-sources">Source access</h2>
              </div>
              <p className="source-gap-note" data-helper-rail-source-access>
                Full source drawers live in the source-list view so this learning page stays focused.
              </p>
              <ul className="helper-source-list" aria-label="Key source documents">
                {keySourceTitles.map((title) => (
                  <li key={title}>{title}</li>
                ))}
              </ul>
            </section>
          </>
        }
        footerContent={
          <section
            className="plain-panel"
            aria-labelledby="beginner-educational-framing"
            data-beginner-educational-framing
            data-prd-section="educational_disclaimer"
          >
            <div className="section-heading">
              <p className="eyebrow">Educational framing</p>
              <h2 id="beginner-educational-framing">Educational suitability</h2>
            </div>
            <p>{asset.suitabilitySummary.mayFit}</p>
            <p>{asset.suitabilitySummary.mayNotFit}</p>
            <p>{asset.suitabilitySummary.learnNext}</p>
          </section>
        }
      />
    </main>
  );
}
