import { notFound } from "next/navigation";
import { AssetHeader } from "../../../components/AssetHeader";
import { AIComprehensiveAnalysisPanel } from "../../../components/AIComprehensiveAnalysisPanel";
import { AssetChatPanel } from "../../../components/AssetChatPanel";
import { AssetDataDashboard, hasAssetDataDashboard } from "../../../components/AssetDataDashboard";
import { AssetEtfSections } from "../../../components/AssetEtfSections";
import { AssetStockSections } from "../../../components/AssetStockSections";
import { EconomicIndicatorsPanel } from "../../../components/EconomicIndicatorsPanel";
import { AssetLearningLayout } from "../../../components/AssetModeLayout";
import { CitationChip } from "../../../components/CitationChip";
import { CompactCitationSources, resolveAssetCitations } from "../../../components/CompactCitationSources";
import { ComparisonSuggestions } from "../../../components/ComparisonSuggestions";
import { ExportControls } from "../../../components/ExportControls";
import { FreshnessDisclosure, FreshnessLabel } from "../../../components/FreshnessLabel";
import { InlineGlossaryText, type InlineGlossaryMatch } from "../../../components/InlineGlossaryText";
import { MarketAIComprehensiveAnalysisPanel } from "../../../components/MarketAIComprehensiveAnalysisPanel";
import { MarketNewsPanel } from "../../../components/MarketNewsPanel";
import { WeeklyNewsPanel } from "../../../components/WeeklyNewsPanel";
import { fetchSupportedAssetDetails } from "../../../lib/assetDetails";
import { fetchSupportedAssetGlossaryContexts } from "../../../lib/assetGlossary";
import { fetchSupportedAssetOverview } from "../../../lib/assetOverview";
import { fetchSupportedSourceDrawerResponse, sourceDrawerEntriesByDocumentId } from "../../../lib/sourceDrawer";
import { fetchSupportedAssetWeeklyNews } from "../../../lib/assetWeeklyNews";
import { fetchEconomicIndicators } from "../../../lib/economicIndicators";
import { fetchMarketNews } from "../../../lib/marketNews";
import { optionalBackendFetcher } from "../../../lib/optionalBackendFetch";
import { beginnerGlossaryGroupsByAssetType, type GlossaryTermKey } from "../../../lib/glossary";
import { getAssetComparisonSuggestions } from "../../../lib/compareSuggestions";
import { resolveSearchResponse, type LocalSearchResponse } from "../../../lib/search";
import {
  assetPageExportUrl,
  assetSourceListExportUrl,
  type AssetExportContractValidation
} from "../../../lib/exportControls";
// fetchSupportedAssetExportContract is intentionally not called during asset-page SSR;
// export URLs remain available and validate through the backend when the user opens them.
import {
  getAIComprehensiveAnalysisFixture,
  assetFixtures,
  citationLabel,
  getCitationById,
  getCitationContextsForSource,
  getPrimarySource,
  getAssetFixture,
  toSourceDrawerDocument,
  getWeeklyNewsFocusFixture,
  economicIndicatorsPackFixture,
  marketAIComprehensiveAnalysisFixture,
  marketNewsFocusFixture,
  type AIComprehensiveAnalysisFixture,
  type AssetFixture,
  type EconomicIndicatorsPackFixture,
  type MarketAIComprehensiveAnalysisFixture,
  type MarketNewsFocusFixture,
  type WeeklyNewsFocusFixture
} from "../../../lib/fixtures";

type AssetPageProps = {
  params: Promise<{
    ticker: string;
  }>;
};

const OVERVIEW_FETCH_TIMEOUT_MS = 12_000;
const DETAILS_FETCH_TIMEOUT_MS = 5_000;
const DEFAULT_LIVE_SECTION_FETCH_TIMEOUT_MS = 5_000;
const LIVE_SECTION_FETCH_TIMEOUT_MS = readPositiveTimeoutMs(
  "NEXT_PUBLIC_LIVE_SECTION_FETCH_TIMEOUT_MS",
  DEFAULT_LIVE_SECTION_FETCH_TIMEOUT_MS
);

type BackendSectionRendering = "backend_contract" | "mixed_fallback" | "local_fixture";
type BackendSectionFailureReason =
  | "api_base_unconfigured"
  | "timeout_or_aborted"
  | "backend_status_error"
  | "invalid_contract"
  | "unexpected_error";
type BackendSectionReason = "backend_contract" | "partial_backend_contract" | BackendSectionFailureReason;

type BackendSectionFetchState = {
  sectionId: string;
  label: string;
  rendering: BackendSectionRendering;
  evidenceState: "live" | "partial" | "unavailable";
  reason: BackendSectionReason;
  message: string;
};

type BackendSectionFetchSuccess<T> = {
  data: T;
  state: BackendSectionFetchState;
};

type BackendSectionFetchFailure = {
  data: null;
  state: BackendSectionFetchState;
};

type BackendSectionFetchResult<T> = BackendSectionFetchSuccess<T> | BackendSectionFetchFailure;

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

function exportContractRendering(contract: AssetExportContractValidation | null) {
  return contract?.rendering ?? "deferred_until_opened";
}

function backendSectionLiveState(sectionId: string, label: string): BackendSectionFetchState {
  return {
    sectionId,
    label,
    rendering: "backend_contract",
    evidenceState: "live",
    reason: "backend_contract",
    message: "Backend evidence returned for this section."
  };
}

function backendSectionFallbackState(sectionId: string, label: string, error: unknown): BackendSectionFetchState {
  const reason = classifyBackendSectionFailure(error);
  return {
    sectionId,
    label,
    rendering: "local_fixture",
    evidenceState: reason === "api_base_unconfigured" ? "partial" : "unavailable",
    reason,
    message: backendSectionFallbackMessage(reason)
  };
}

async function fetchBackendSection<T>(
  sectionId: string,
  label: string,
  request: () => Promise<T>
): Promise<BackendSectionFetchResult<T>> {
  try {
    return {
      data: await request(),
      state: backendSectionLiveState(sectionId, label)
    };
  } catch (error) {
    return {
      data: null,
      state: backendSectionFallbackState(sectionId, label, error)
    };
  }
}

function classifyBackendSectionFailure(error: unknown): BackendSectionFailureReason {
  if (error instanceof Error) {
    const message = error.message.toLowerCase();
    if (message.includes("no api base url is configured")) {
      return "api_base_unconfigured";
    }
    if (error.name === "AbortError" || message.includes("aborted") || message.includes("timed out")) {
      return "timeout_or_aborted";
    }
    if (message.includes("request failed with status")) {
      return "backend_status_error";
    }
    if (message.includes("did not match the expected backend response contract")) {
      return "invalid_contract";
    }
  }
  return "unexpected_error";
}

function backendSectionFallbackMessage(reason: BackendSectionFailureReason) {
  if (reason === "api_base_unconfigured") {
    return "The live backend is not connected for this render, so this section is showing deterministic local fallback content.";
  }
  if (reason === "timeout_or_aborted") {
    return "The backend request did not finish before the page timeout, so this section is marked unavailable for live evidence.";
  }
  if (reason === "backend_status_error") {
    return "The backend returned an error for this section, so live evidence is unavailable on this render.";
  }
  if (reason === "invalid_contract") {
    return "The backend response did not match the expected contract, so this section is not treated as live evidence.";
  }
  return "Something went wrong loading this section, so live evidence is unavailable on this render.";
}

function sectionFallbackNoticeLead(state: BackendSectionFetchState) {
  if (state.reason === "api_base_unconfigured") {
    return "This section is using deterministic local fallback content because the live backend is not connected.";
  }
  if (state.reason === "timeout_or_aborted") {
    return "This section timed out before backend evidence returned.";
  }
  if (state.reason === "backend_status_error") {
    return "The backend returned an error for this section.";
  }
  if (state.reason === "invalid_contract") {
    return "The backend returned data, but it did not match the expected section contract.";
  }
  if (state.reason === "partial_backend_contract") {
    return "This section loaded with partial backend coverage.";
  }
  return "This section could not load backend evidence for this render.";
}

function readPositiveTimeoutMs(envName: string, fallbackMs: number) {
  const rawValue = process.env[envName]?.trim();
  if (!rawValue) {
    return fallbackMs;
  }
  const parsed = Number.parseInt(rawValue, 10);
  if (!Number.isFinite(parsed) || parsed < 1_000) {
    return fallbackMs;
  }
  return parsed;
}

function hasBackendSectionFallback(states: readonly BackendSectionFetchState[]) {
  return states.some((state) => state.rendering !== "backend_contract");
}

function AssetBackendEvidenceSummary({ states }: { states: readonly BackendSectionFetchState[] }) {
  const fallbackStates = states.filter((state) => state.rendering !== "backend_contract");

  if (!fallbackStates.length) {
    return (
      <section
        className="plain-panel stable-section"
        aria-labelledby="asset-backend-evidence-summary"
        data-asset-backend-evidence-summary
        data-asset-backend-evidence-summary-state="live"
      >
        <div className="section-heading-row">
          <div className="section-heading">
            <p className="eyebrow">Evidence availability</p>
            <h2 id="asset-backend-evidence-summary">Live backend evidence loaded</h2>
          </div>
          <div className="state-row">
            <span className="state-pill compact-state" data-evidence-state="live">
              live
            </span>
          </div>
        </div>
        <p className="notice-text">
          The asset overview and live page sections returned backend evidence for this render.
        </p>
      </section>
    );
  }

  return (
    <section
      className="plain-panel unknown-state"
      aria-labelledby="asset-backend-evidence-summary"
      data-asset-backend-evidence-summary
      data-asset-backend-evidence-summary-state="partial_or_unavailable"
      data-asset-backend-fallback-section-count={fallbackStates.length}
    >
      <div className="section-heading-row">
        <div className="section-heading">
          <p className="eyebrow">Evidence availability</p>
          <h2 id="asset-backend-evidence-summary">Some sections are using fallback content</h2>
        </div>
        <div className="state-row">
          <span className="state-pill compact-state" data-evidence-state="partial">
            partial
          </span>
        </div>
      </div>
      <p className="notice-text">
        This page can still be useful for learning, but the sections below should not be read as complete live backend
        evidence for this render.
      </p>
      <div className="section-stack" data-asset-backend-fallback-sections>
        {fallbackStates.map((state) => (
          <div
            key={state.sectionId}
            className="source-gap-note"
            data-asset-section-fetch-state={state.sectionId}
            data-asset-section-rendering={state.rendering}
            data-asset-section-failure-reason={state.reason}
          >
            <strong>{state.label}:</strong> {state.message}
          </div>
        ))}
      </div>
      <p className="source-gap-note" data-weekly-news-backend-failure-distinct-from-empty-state>
        Weekly News distinguishes a normal no-high-signal result from a backend failure or timeout. If Weekly News is
        listed above, its empty state is not proof that no high-signal items exist.
      </p>
    </section>
  );
}

function SectionFallbackNotice({ state }: { state: BackendSectionFetchState }) {
  if (state.rendering === "backend_contract") {
    return null;
  }

  return (
    <section
      className="plain-panel unknown-state"
      aria-label={`${state.label} evidence availability`}
      data-asset-section-fallback-notice={state.sectionId}
      data-asset-section-rendering={state.rendering}
      data-asset-section-failure-reason={state.reason}
      data-asset-section-evidence-state={state.evidenceState}
    >
      <div className="section-heading-row">
        <div className="section-heading">
          <p className="eyebrow">Section evidence state</p>
          <h2>{state.label}</h2>
        </div>
        <div className="state-row">
          <span className="state-pill compact-state" data-evidence-state={state.evidenceState}>
            {state.evidenceState}
          </span>
        </div>
      </div>
      <p className="notice-text">{sectionFallbackNoticeLead(state)}</p>
      <p className="source-gap-note">{state.message}</p>
      {state.sectionId === "weekly_news" ? (
        <p className="source-gap-note" data-weekly-news-fetch-failure-notice>
          This is different from a verified no-high-signal Weekly News result; the backend section did not return live
          evidence for this render.
        </p>
      ) : null}
    </section>
  );
}

export function generateStaticParams() {
  return Object.keys(assetFixtures).map((ticker) => ({ ticker }));
}

export default async function AssetPage({ params }: AssetPageProps) {
  const { ticker } = await params;
  const fallbackAsset = getAssetFixture(ticker);
  let asset: AssetFixture | null = fallbackAsset ?? null;
  let overviewRendering: "backend_contract" | "local_fixture" = "local_fixture";
  let detailsRendering: "backend_contract" | "local_fixture" = "local_fixture";
  let economicIndicatorsRendering: "backend_contract" | "local_fixture" = "local_fixture";
  let marketNewsRendering: "backend_contract" | "local_fixture" = "local_fixture";
  let weeklyNewsRendering: "backend_contract" | "local_fixture" = "local_fixture";
  let sourceDrawerRendering: "backend_contract" | "mixed_fallback" | "local_fixture" = "local_fixture";
  let glossaryRendering: "backend_contract" | "local_fixture" = "local_fixture";
  let assetPageExportContract: AssetExportContractValidation | null = null;
  let assetSourceListExportContract: AssetExportContractValidation | null = null;
  const backendApiConfigured = Boolean(process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || process.env.API_BASE_URL?.trim());
  let overviewFetchFailed = false;
  let overviewFetchState = backendSectionFallbackState(
    "asset_overview",
    "Asset overview",
    new Error("No API base URL is configured for supported asset overview fetches.")
  );
  let detailsFetchState = backendSectionFallbackState(
    "asset_details",
    "Asset details",
    new Error("No API base URL is configured for supported asset detail fetches.")
  );

  try {
    asset = await fetchSupportedAssetOverview(
      fallbackAsset?.ticker ?? ticker,
      fallbackAsset,
      optionalBackendFetcher(OVERVIEW_FETCH_TIMEOUT_MS)
    );
    overviewRendering = "backend_contract";
    overviewFetchState = backendSectionLiveState("asset_overview", "Asset overview");
  } catch (error) {
    overviewFetchFailed = true;
    overviewFetchState = backendSectionFallbackState("asset_overview", "Asset overview", error);
    asset = backendApiConfigured ? null : fallbackAsset ?? null;
  }

  if (!asset) {
    const search = await resolveSearchResponse(ticker);
    if (search.state.status === "unknown" && search.results[0]?.ticker === "") {
      notFound();
    }
    if (overviewFetchFailed && (search.state.status === "supported" || search.results[0]?.supported)) {
      return <RecoverableBackendAssetStatePage ticker={ticker} search={search} failureState={overviewFetchState} />;
    }
    return <LimitedAssetStatePage ticker={ticker} search={search} />;
  }

  try {
    asset = await fetchSupportedAssetDetails(asset.ticker, asset, optionalBackendFetcher(DETAILS_FETCH_TIMEOUT_MS));
    detailsRendering = "backend_contract";
    detailsFetchState = backendSectionLiveState("asset_details", "Asset details");
  } catch (error) {
    detailsRendering = "local_fixture";
    detailsFetchState = backendSectionFallbackState("asset_details", "Asset details", error);
  }

  let marketNewsFocus: MarketNewsFocusFixture = marketNewsFocusFixture;
  let marketAIComprehensiveAnalysis: MarketAIComprehensiveAnalysisFixture = marketAIComprehensiveAnalysisFixture;
  let economicIndicators: EconomicIndicatorsPackFixture = economicIndicatorsPackFixture;

  let weeklyNewsFocus = getWeeklyNewsFocusFixture(asset.ticker) ?? buildEmptyWeeklyNewsFocus(asset);
  let aiComprehensiveAnalysis = getAIComprehensiveAnalysisFixture(asset.ticker) ?? buildSuppressedAnalysis(asset, weeklyNewsFocus);

  const glossaryGroups = beginnerGlossaryGroupsByAssetType[asset.assetType];
  const dashboardGlossaryTerms: GlossaryTermKey[] = [
    "net assets",
    "AUM",
    "P/E ratio",
    "forward P/E",
    "EV/EBITDA",
    "NAV",
    "YTD return",
    "beta",
    "volume",
    "average volume",
    "day's range",
    "52 week range",
    "bid",
    "ask",
    "yield",
    "expense ratio"
  ];
  const additionalInlineGlossaryTerms: GlossaryTermKey[] =
    asset.assetType === "etf" ? ["market risk", ...dashboardGlossaryTerms] : dashboardGlossaryTerms;
  const glossaryTermsForBackend = [
    ...new Set<GlossaryTermKey>([...glossaryGroups.flatMap((group) => group.terms), ...additionalInlineGlossaryTerms])
  ];
  const inlineGlossaryMatches: InlineGlossaryMatch[] = [...glossaryTermsForBackend];
  inlineGlossaryMatches.push(
    { match: "Net assets / AUM", term: "net assets" },
    { match: "Net Assets", term: "net assets" },
    { match: "PE Ratio (TTM)", term: "P/E ratio" },
    { match: "P/E", term: "P/E ratio" },
    { match: "Forward P/E", term: "forward P/E" },
    { match: "EV/EBITDA", term: "EV/EBITDA" },
    { match: "NAV", term: "NAV" },
    { match: "YTD Daily Total Return", term: "YTD return" },
    { match: "YTD return", term: "YTD return" },
    { match: "Beta (5Y Monthly)", term: "beta" },
    { match: "Beta", term: "beta" },
    { match: "Avg. Volume", term: "average volume" },
    { match: "Average volume", term: "average volume" },
    { match: "Day's Range", term: "day's range" },
    { match: "52 Week Range", term: "52 week range" },
    { match: "Bid", term: "bid" },
    { match: "Ask", term: "ask" },
    { match: "Yield", term: "yield" },
    { match: "Expense Ratio (net)", term: "expense ratio" }
  );

  const [
    economicIndicatorsResult,
    marketNewsResult,
    weeklyNewsResult,
    sourceDrawerResult,
    glossaryContextsResult
  ] = await Promise.all([
    fetchBackendSection("economic_indicators", "Economic Indicators", () =>
      fetchEconomicIndicators(economicIndicators, optionalBackendFetcher(LIVE_SECTION_FETCH_TIMEOUT_MS))
    ),
    fetchBackendSection("market_news", "Market News Focus", () =>
      fetchMarketNews(marketNewsFocus, marketAIComprehensiveAnalysis, optionalBackendFetcher(LIVE_SECTION_FETCH_TIMEOUT_MS))
    ),
    fetchBackendSection("weekly_news", `Weekly News Focus: ${asset.ticker}`, () =>
      fetchSupportedAssetWeeklyNews(
        asset.ticker,
        weeklyNewsFocus,
        aiComprehensiveAnalysis,
        asset.assetType,
        optionalBackendFetcher(LIVE_SECTION_FETCH_TIMEOUT_MS)
      )
    ),
    fetchBackendSection("source_drawer", "Source drawer", () =>
      fetchSupportedSourceDrawerResponse(asset.ticker, optionalBackendFetcher(LIVE_SECTION_FETCH_TIMEOUT_MS))
    ),
    fetchBackendSection("glossary_context", "Glossary context", () =>
      fetchSupportedAssetGlossaryContexts(
        asset.ticker,
        glossaryTermsForBackend,
        optionalBackendFetcher(LIVE_SECTION_FETCH_TIMEOUT_MS)
      )
    )
  ]);

  if (economicIndicatorsResult.data) {
    economicIndicators = economicIndicatorsResult.data;
    economicIndicatorsRendering = "backend_contract";
  }

  if (marketNewsResult.data) {
    marketNewsFocus = marketNewsResult.data.marketNewsFocus;
    marketAIComprehensiveAnalysis = marketNewsResult.data.marketAIComprehensiveAnalysis;
    marketNewsRendering = "backend_contract";
  }

  if (weeklyNewsResult.data) {
    weeklyNewsFocus = weeklyNewsResult.data.weeklyNewsFocus;
    aiComprehensiveAnalysis = weeklyNewsResult.data.aiComprehensiveAnalysis;
    weeklyNewsRendering = "backend_contract";
  }

  if (glossaryContextsResult.data) {
    glossaryRendering = "backend_contract";
  }

  const backendEconomicIndicatorsState = economicIndicatorsResult.state;
  const backendMarketNewsState = marketNewsResult.state;
  const backendWeeklyNewsState = weeklyNewsResult.state;
  let backendSourceDrawerState = sourceDrawerResult.state;
  const backendGlossaryState = glossaryContextsResult.state;
  const backendGlossaryContexts = glossaryContextsResult.data;

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
    ...economicIndicators.citations,
    ...marketNewsFocus.citations,
    ...marketAIComprehensiveAnalysis.citations,
    ...weeklyNewsFocus.citations,
    ...aiComprehensiveAnalysis.citations
  ].filter((citation, index, collection) => collection.findIndex((entry) => entry.citationId === citation.citationId) === index);
  const mergedSources = [
    ...asset.sourceDocuments,
    ...economicIndicators.sourceDocuments,
    ...marketNewsFocus.sourceDocuments,
    ...marketAIComprehensiveAnalysis.sourceDocuments,
    ...weeklyNewsFocus.sourceDocuments,
    ...aiComprehensiveAnalysis.sourceDocuments
  ].filter(
    (source, index, collection) =>
      collection.findIndex((entry) => entry.sourceDocumentId === source.sourceDocumentId) === index
  );
  const timelyContextSourceDocumentIds = new Set([
    ...economicIndicators.sourceDocuments.map((source) => source.sourceDocumentId),
    ...marketNewsFocus.sourceDocuments.map((source) => source.sourceDocumentId),
    ...marketAIComprehensiveAnalysis.sourceDocumentIds,
    ...weeklyNewsFocus.sourceDocuments.map((source) => source.sourceDocumentId),
    ...aiComprehensiveAnalysis.sourceDocumentIds
  ]);
  const drawerSourceDocumentIds = new Set([...sectionSourceDocumentIds, ...timelyContextSourceDocumentIds]);
  const drawerSources = mergedSources
    .filter((source) => drawerSourceDocumentIds.has(source.sourceDocumentId))
    .map(toSourceDrawerDocument);
  const timelyContextClaimsBySourceDocumentId = new Map<string, string>([
    ...economicIndicators.items.flatMap((item) =>
      item.sourceDocumentIds.map(
        (sourceDocumentId) =>
          [
            sourceDocumentId,
            `Economic Indicators: ${item.name} was ${item.value}${item.unit ? ` ${item.unit}` : ""} for ${item.period}.`
          ] as const
      )
    ),
    ...marketNewsFocus.items.map((item) => [
      item.source.sourceDocumentId,
      `Market News Focus: ${item.title}. ${item.summary}`
    ] as const),
    ...weeklyNewsFocus.items.map((item) => [
      item.source.sourceDocumentId,
      `Weekly News Focus: ${asset.ticker}: ${item.title}. ${item.summary}`
    ] as const)
  ]);
  for (const sourceDocumentId of marketAIComprehensiveAnalysis.sourceDocumentIds) {
    if (!timelyContextClaimsBySourceDocumentId.has(sourceDocumentId)) {
      timelyContextClaimsBySourceDocumentId.set(
        sourceDocumentId,
        "AI Comprehensive Analysis: Market News Focus cites this source while keeping market-wide context separate from ticker-specific facts."
      );
    }
  }
  for (const sourceDocumentId of aiComprehensiveAnalysis.sourceDocumentIds) {
    if (!timelyContextClaimsBySourceDocumentId.has(sourceDocumentId)) {
      timelyContextClaimsBySourceDocumentId.set(
        sourceDocumentId,
        `AI Comprehensive Analysis cites this source while keeping timely context separate from stable facts for ${asset.ticker}.`
      );
    }
  }
  const comparisonSuggestions = getAssetComparisonSuggestions(asset.ticker);
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
  const backendDrawerEntries = sourceDrawerResult.data ? sourceDrawerEntriesByDocumentId(sourceDrawerResult.data) : null;
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
  const hasDashboard = hasAssetDataDashboard(asset);

  if (backendDrawerEntries) {
    const allRenderedDrawerEntriesBackendBacked = renderedDrawerEntries.every((entry) =>
      backendDrawerEntries.has(entry.source.source_document_id)
    );
    sourceDrawerRendering = allRenderedDrawerEntriesBackendBacked ? "backend_contract" : "mixed_fallback";
    if (!allRenderedDrawerEntriesBackendBacked) {
      backendSourceDrawerState = {
        ...backendSourceDrawerState,
        rendering: "mixed_fallback",
        evidenceState: "partial",
        reason: "partial_backend_contract",
        message: "The backend source drawer returned, but some source entries still use local fallback metadata."
      };
    }
  }

  const backendSectionStates = [
    overviewFetchState,
    detailsFetchState,
    backendEconomicIndicatorsState,
    backendMarketNewsState,
    backendWeeklyNewsState,
    backendSourceDrawerState,
    backendGlossaryState
  ];
  const backendEvidenceHasFallback = hasBackendSectionFallback(backendSectionStates);

  return (
    <main
      data-asset-overview-rendering={overviewRendering}
      data-asset-details-rendering={detailsRendering}
      data-asset-economic-indicators-rendering={economicIndicatorsRendering}
      data-asset-market-news-rendering={marketNewsRendering}
      data-asset-weekly-news-rendering={weeklyNewsRendering}
      data-asset-source-drawer-rendering={sourceDrawerRendering}
      data-asset-glossary-rendering={glossaryRendering}
      data-asset-page-export-contract={exportContractRendering(assetPageExportContract)}
      data-asset-source-list-export-contract={exportContractRendering(assetSourceListExportContract)}
      data-asset-backend-evidence-has-fallback={backendEvidenceHasFallback ? "true" : "false"}
      data-prd-layout-marker="supported-asset-page-learning-flow-v1"
      data-prd-section-order="header,beginner_summary,asset_data_dashboard,top_risks,key_facts_fallback,what_it_does_or_holds_fallback,economic_indicators,market_news_focus,market_ai_comprehensive_analysis,weekly_news_focus,ai_comprehensive_analysis,deep_dive,ask_about_this_asset,sources,educational_disclaimer"
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
              <div className="freshness-disclosure-row">
                <FreshnessDisclosure label="Page last updated" value={asset.freshness.pageLastUpdatedAt} state="fresh" />
                <FreshnessDisclosure label="Beginner overview as of" value={asset.freshness.factsAsOf} state="fresh" />
              </div>
            </section>

            <AssetBackendEvidenceSummary states={backendSectionStates} />

            <SectionFallbackNotice state={backendGlossaryState} />

            <AssetDataDashboard
              asset={asset}
              glossaryMatches={inlineGlossaryMatches}
              glossaryContexts={backendGlossaryContexts}
            />

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
              <div className="freshness-disclosure-row">
                <FreshnessDisclosure label="Top risks as of" value={asset.freshness.factsAsOf} state="fresh" />
              </div>
            </section>

            {!hasDashboard ? (
              <>
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
              <div className="freshness-disclosure-row">
                <FreshnessDisclosure label="Stable facts as of" value={asset.freshness.factsAsOf} state="fresh" />
              </div>
                </section>

                <section
                  className="plain-panel stable-section"
                  aria-labelledby="beginner-what-it-does-or-holds"
                  data-beginner-stable-recent-separation="stable"
                  data-prd-section="what_it_does_or_holds"
                  data-asset-what-section-id={whatItDoesOrHoldsSection?.sectionId ?? "primary_claim_fallback"}
                >
              <div className="section-heading-row">
                <div className="section-heading">
                  <p className="eyebrow">Stable facts</p>
                  <h2 id="beginner-what-it-does-or-holds">
                    {asset.assetType === "etf" ? "What It Holds" : "What It Does"}
                  </h2>
                </div>
                {whatItDoesOrHoldsSection ? (
                  <div className="state-row">
                    <span className="state-pill" data-evidence-state={whatItDoesOrHoldsSection.evidenceState}>
                      Evidence: {whatItDoesOrHoldsSection.evidenceState.replaceAll("_", " ")}
                    </span>
                  </div>
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
                      <div className="compact-source-row">
                        <CompactCitationSources
                          citations={resolveAssetCitations(asset, item.citationIds)}
                          label={`${item.title} sources`}
                        />
                      </div>
                    </article>
                  ))}
                </div>
              ) : null}
              <div className="freshness-disclosure-row">
                <FreshnessDisclosure
                  label={asset.assetType === "etf" ? "Holdings as of" : "Business facts as of"}
                  value={
                    asset.assetType === "etf"
                      ? asset.freshness.holdingsAsOf ?? "Unknown in current evidence"
                      : asset.freshness.factsAsOf
                  }
                  state={asset.assetType === "etf" && !asset.freshness.holdingsAsOf ? "unknown" : "fresh"}
                />
              </div>
                </section>
              </>
            ) : null}

            <SectionFallbackNotice state={backendEconomicIndicatorsState} />

            <EconomicIndicatorsPanel pack={economicIndicators} citations={mergedCitations} />

            <SectionFallbackNotice state={backendMarketNewsState} />

            <MarketNewsPanel focus={marketNewsFocus} citations={mergedCitations} />

            <MarketAIComprehensiveAnalysisPanel analysis={marketAIComprehensiveAnalysis} citations={mergedCitations} />

            <SectionFallbackNotice state={backendWeeklyNewsState} />

            <WeeklyNewsPanel focus={weeklyNewsFocus} citations={mergedCitations} assetTicker={asset.ticker} />

            <AIComprehensiveAnalysisPanel analysis={aiComprehensiveAnalysis} citations={mergedCitations} assetTicker={asset.ticker} />
          </>
        }
        deepDiveSections={
          <>
            <SectionFallbackNotice state={detailsFetchState} />

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
                <p>
                  Missing live facts are labeled instead of being filled in from model memory. This view uses only the
                  evidence currently available to the local source pack.
                </p>
                <div className="freshness-disclosure-row">
                  <FreshnessDisclosure label="Valuation context" value="Unknown in current evidence" state="unknown" />
                  <FreshnessDisclosure label="Live market quote" value="Unavailable by design" state="stale" />
                </div>
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
            <SectionFallbackNotice state={backendSourceDrawerState} />

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
              data-source-drawer-mobile-presentation="bottom-sheet"
            >
              {renderedDrawerEntries.map((entry) => (
                <details
                  key={entry.source.source_document_id}
                  id={`source-${entry.source.source_document_id}`}
                  className="asset-source-index-card"
                  data-asset-source-index-entry
                  data-source-document-id={entry.source.source_document_id}
                  data-source-drawer-state={entry.drawerState}
                  data-source-freshness-state={entry.source.freshness_state}
                  data-source-use-policy={entry.source.source_use_policy}
                >
                  <summary>
                    <span className="source-index-summary-copy">
                      <span className="eyebrow">{entry.source.source_type}</span>
                      <strong>{entry.source.title}</strong>
                    </span>
                    {entry.source.isOfficial ? <span className="source-badge">Official source</span> : null}
                  </summary>
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
                </details>
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
                <a href={assetPageExportUrl(asset.ticker)} data-helper-rail-action="export">
                  Export
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

function RecoverableBackendAssetStatePage({
  ticker,
  search,
  failureState
}: {
  ticker: string;
  search: LocalSearchResponse;
  failureState?: BackendSectionFetchState;
}) {
  const result = search.results[0];
  const titleTicker = result?.ticker || ticker.toUpperCase();
  const supportClassification = search.state.support_classification ?? result?.support_classification ?? "cached_supported";

  return (
    <main
      data-prd-layout-marker="asset-page-backend-temporarily-unavailable-v1"
      data-asset-overview-rendering="backend_unavailable"
      data-asset-dynamic-fallback-state="supported_backend_unavailable"
      data-asset-support-classification={supportClassification}
      data-asset-generated-page-blocked="false"
      data-asset-overview-failure-reason={failureState?.reason ?? "unknown"}
      data-asset-supported-backend-unavailable
    >
      <section className="plain-panel unknown-state" data-dynamic-asset-state="supported_backend_unavailable">
        <div className="section-heading">
          <p className="eyebrow">Backend data temporarily unavailable</p>
          <h1>{titleTicker} learning page</h1>
        </div>
        <div className="state-row">
          <span className="state-pill" data-evidence-state="supported">
            State: supported
          </span>
          <span className="state-pill" data-support-classification={supportClassification}>
            {supportClassification.replaceAll("_", " ")}
          </span>
        </div>
        <p className="source-gap-note">
          This asset is supported, but the local backend did not return a valid overview quickly enough for this page
          render. Try refreshing after the backend finishes its source-labeled fetch, or open search while the cache warms.
        </p>
        {failureState ? (
          <p className="source-gap-note" data-asset-overview-fetch-failure-notice>
            {failureState.message}
          </p>
        ) : null}
        <p className="source-gap-note" data-asset-supported-recoverable-backend-state>
          No generated facts are shown from frontend memory in this state; the page waits for a same-asset backend
          evidence response before rendering charts, tables, chat, comparisons, exports, or Weekly News Focus.
        </p>
        <nav className="source-list-nav" aria-label="Asset availability navigation">
          <a href="/">Back to search</a>
          <a href="/compare">Open comparison workflow</a>
        </nav>
      </section>
    </main>
  );
}

function LimitedAssetStatePage({ ticker, search }: { ticker: string; search: LocalSearchResponse }) {
  const result = search.results[0];
  const status = search.state.status;
  const supportClassification = search.state.support_classification ?? result?.support_classification ?? "unknown";
  const titleTicker = result?.ticker || ticker.toUpperCase();
  const stateLabel = status.replaceAll("_", " ");
  if (status === "supported" || result?.supported) {
    return <RecoverableBackendAssetStatePage ticker={ticker} search={search} />;
  }
  const message =
    search.state.blocked_explanation?.summary ??
    result?.blocked_explanation?.summary ??
    search.state.message ??
    "This asset page is unavailable in the current deterministic frontend fallback.";

  return (
    <main
      data-prd-layout-marker="asset-page-blocked-or-limited-flow-v1"
      data-asset-overview-rendering="local_fixture"
      data-asset-dynamic-fallback-state={status}
      data-asset-support-classification={supportClassification}
      data-asset-generated-page-blocked
    >
      <section className="plain-panel unknown-state" data-dynamic-asset-state={status}>
        <div className="section-heading">
          <p className="eyebrow">Asset availability</p>
          <h1>{titleTicker} learning page</h1>
        </div>
        <div className="state-row">
          <span className="state-pill" data-evidence-state={status}>
            State: {stateLabel}
          </span>
          <span className="state-pill" data-support-classification={supportClassification}>
            {supportClassification.replaceAll("_", " ")}
          </span>
        </div>
        <p className="source-gap-note">{message}</p>
        {result?.message ? <p className="source-gap-note">{result.message}</p> : null}
        {search.state.requires_ingestion || result?.requires_ingestion ? (
          <p className="source-gap-note" data-asset-pending-ingestion-state>
            This asset is eligible for a future ingestion workflow, but no generated page, chat answer, comparison, or
            risk summary is created from the frontend fallback.
          </p>
        ) : null}
        <p className="source-gap-note" data-asset-no-generated-output-for-blocked-state>
          Unsupported, out-of-scope, unknown, unavailable, and pending-ingestion states stay blocked until a same-asset
          backend evidence pack can support the learning page.
        </p>
        <nav className="source-list-nav" aria-label="Asset availability navigation">
          <a href="/">Back to search</a>
          <a href="/compare">Open comparison workflow</a>
        </nav>
      </section>
    </main>
  );
}

function buildEmptyWeeklyNewsFocus(asset: AssetFixture): WeeklyNewsFocusFixture {
  return {
    schemaVersion: "weekly-news-focus-v1",
    state: "no_high_signal",
    window: {
      asOfDate: asset.freshness.recentEventsAsOf,
      timezone: "America/New_York",
      previousMarketWeek: {
        start: null,
        end: null
      },
      currentWeekToDate: {
        start: null,
        end: null
      },
      newsWindowStart: asset.freshness.recentEventsAsOf,
      newsWindowEnd: asset.freshness.recentEventsAsOf,
      includesCurrentWeekToDate: false
    },
    configuredMaxItemCount: 8,
    selectedItemCount: 0,
    suppressedCandidateCount: 0,
    evidenceState: "no_high_signal",
    evidenceLimitedState: "empty",
    items: [],
    emptyState: {
      state: "no_high_signal",
      message: "No major Weekly News Focus items found in the backend-backed dynamic page fallback.",
      evidenceState: "no_high_signal",
      selectedItemCount: 0,
      suppressedCandidateCount: 0
    },
    citations: [],
    sourceDocuments: [],
    noLiveExternalCalls: true,
    stableFactsAreSeparate: true
  };
}

function buildSuppressedAnalysis(
  asset: AssetFixture,
  weeklyNewsFocus: WeeklyNewsFocusFixture
): AIComprehensiveAnalysisFixture {
  return {
    schemaVersion: "ai-comprehensive-analysis-v1",
    state: "suppressed",
    analysisAvailable: false,
    minimumWeeklyNewsItemCount: 2,
    weeklyNewsSelectedItemCount: weeklyNewsFocus.selectedItemCount,
    suppressionReason: "AI Comprehensive Analysis is suppressed until at least two approved Weekly News Focus items exist.",
    validationReasonCodes: [],
    sections: [],
    citationIds: [],
    sourceDocumentIds: [],
    weeklyNewsEventIds: [],
    canonicalFactCitationIds: asset.claims.flatMap((claim) => claim.citationIds).slice(0, 1),
    citations: [],
    sourceDocuments: [],
    noLiveExternalCalls: true,
    stableFactsAreSeparate: true
  };
}
