import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const webRoot = join(root, "apps/web");

function read(path) {
  const webPath = join(webRoot, path);
  if (existsSync(webPath)) {
    return readFileSync(webPath, "utf8");
  }
  return readFileSync(join(root, path), "utf8");
}

function exists(path) {
  assert.equal(
    existsSync(join(webRoot, path)) || existsSync(join(root, path)),
    true,
    `${path} should exist in apps/web or the repo root`
  );
}

function includes(path, marker) {
  assert.match(read(path), new RegExp(marker), `${path} should include ${marker}`);
}

function includesAll(path, markers, label) {
  const source = read(path);
  for (const marker of markers) {
    assert.ok(source.includes(marker), `${path} should include ${marker} for ${label}`);
  }
}

function orderedMarkers(path, markers, label) {
  const source = read(path);
  let previousIndex = -1;
  for (const marker of markers) {
    const index = source.indexOf(marker);
    assert.notEqual(index, -1, `${path} should include ${marker} for ${label}`);
    assert.ok(index > previousIndex, `${path} should keep ${marker} in order for ${label}`);
    previousIndex = index;
  }
}

[
  "app/page.tsx",
  "app/assets/[ticker]/page.tsx",
  "app/assets/[ticker]/sources/page.tsx",
  "app/compare/page.tsx",
  "components/AIComprehensiveAnalysisPanel.tsx",
  "components/AssetChatPanel.tsx",
  "components/AssetEtfSections.tsx",
  "components/AssetStockSections.tsx",
  "components/AssetModeLayout.tsx",
  "components/CitationChip.tsx",
  "components/ComparisonSuggestions.tsx",
  "components/ComparisonSourceDetails.tsx",
  "components/ExportControls.tsx",
  "components/SourceDrawer.tsx",
  "components/FreshnessLabel.tsx",
  "components/GlossaryPopover.tsx",
  "components/InlineGlossaryText.tsx",
  "components/WeeklyNewsPanel.tsx",
  "lib/assetDetails.ts",
  "lib/apiEndpoints.ts",
  "lib/assetChat.ts",
  "lib/assetGlossary.ts",
  "lib/assetOverview.ts",
  "lib/assetWeeklyNews.ts",
  "lib/compare.ts",
  "lib/compareSuggestions.ts",
  "lib/exportControls.ts",
  "lib/fixtures.ts",
  "lib/glossary.ts",
  "lib/trustMetrics.ts",
  "lib/sourceDrawer.ts",
  "styles/globals.css"
].forEach(exists);

includesAll("app/layout.tsx", [
  "data-global-navigation-workflow=\"single-search-separate-compare\"",
  "data-nav-primary-entry=\"single-asset-search\"",
  "data-nav-secondary-entry=\"separate-comparison-workflow\"",
  "href=\"/compare\""
], "global navigation search-first and neutral comparison entry");
assert.equal(
  read("app/layout.tsx").includes("/compare?left=") || read("app/layout.tsx").includes("/compare?right="),
  false,
  "Global navigation should expose the neutral comparison builder instead of a default pair"
);
assert.equal(
  read("app/layout.tsx").toLowerCase().includes("glossary"),
  false,
  "Global navigation should not promote glossary as a top-level MVP workflow"
);
includesAll("app/page.tsx", [
  "data-home-workflow-baseline=\"single-asset-search-first\"",
  "data-home-primary-workflow=\"single-supported-stock-or-etf-search\"",
  "SearchBox",
  "Understand a stock or ETF in plain English",
  "data-home-workflow-card=\"single-asset-search\"",
  "data-home-workflow-card=\"separate-comparison\"",
  "data-home-workflow-card=\"source-backed-learning\"",
  "contextual glossary help",
  "/compare"
], "home single-asset-first route workflow");
includesAll("components/SearchBox.tsx", [
  "data-home-primary-action=\"single-asset-search\"",
  "data-search-support-state-idle-visible=\"false\"",
  "data-search-support-state-labels={V04_SUPPORT_STATE_CHIPS.join",
  "data-search-comparison-result",
  "data-search-special-autocomplete-result",
  "data-search-comparison-route",
  "data-search-open-comparison-route",
  "data-search-supported-result",
  "data-search-ingestion-needed-result",
  "data-search-unsupported-result",
  "data-search-out-of-scope-result",
  "data-search-unknown-result",
  "data-search-no-invented-facts"
], "home search support-state and comparison redirect markers");
orderedMarkers("components/SearchBox.tsx", [
  "data-search-comparison-result",
  "data-search-supported-result",
  "data-search-ambiguous-result",
  "data-search-ingestion-needed-result",
  "data-search-unsupported-result",
  "data-search-out-of-scope-result",
  "data-search-unknown-result"
], "search route-level result states");
includesAll("lib/search.ts", [
  "comparison_route",
  "/compare?left=",
  "can_open_generated_page: false",
  "can_answer_chat: false",
  "can_compare: true",
  "Comparison is a separate workflow",
  "We found this ticker, but it is not supported in v1.",
  "blocked_capabilities: EMPTY_BLOCKED_CAPABILITIES"
], "deterministic search routing and blocked-state contracts");
assert.equal(
  read("app/page.tsx").includes("name=\"left\"") || read("app/page.tsx").includes("name=\"right\""),
  false,
  "Home route should not expose two comparison-builder inputs"
);
assert.equal(
  read("app/page.tsx").includes("data-home-workflow-card=\"glossary\"") ||
    read("app/page.tsx").includes("Glossary for this page"),
  false,
  "Home route should not promote glossary as a primary MVP workflow"
);

orderedMarkers("app/assets/[ticker]/page.tsx", [
  "data-prd-section=\"beginner_summary\"",
  "data-prd-section=\"top_risks\"",
  "data-prd-section=\"key_facts\"",
  "data-prd-section=\"what_it_does_or_holds\"",
  "<WeeklyNewsPanel",
  "<AIComprehensiveAnalysisPanel",
  "deepDiveSections=",
  "data-prd-section=\"ask_about_this_asset\"",
  "sourceTools=",
  "data-prd-section=\"educational_disclaimer\""
], "supported asset page PRD section order");
includesAll("app/assets/[ticker]/page.tsx", [
  "supported-asset-page-learning-flow-v1",
  "data-beginner-stable-recent-separation=\"stable\"",
  "data-beginner-summary-card-count=\"3\"",
  "data-beginner-top-risk-count",
  "data-asset-source-full-drawers=\"dedicated-source-list\"",
  "data-asset-source-drawer-repetition=\"removed\"",
  "data-asset-source-list-link",
  "AssetChatPanel",
  "ExportControls",
  "InlineGlossaryText"
], "asset route stable facts, sources, chat, export, and contextual glossary markers");
includesAll("components/WeeklyNewsPanel.tsx", [
  "data-weekly-news-configured-max",
  "data-weekly-news-selected-count",
  "data-weekly-news-evidence-limited-state",
  "data-weekly-news-empty-behavior",
  "data-weekly-news-limited-verified-set",
  "No major Weekly News Focus items found",
  "Source quality:",
  "Source-use policy:"
], "Weekly News Focus evidence-limited markers");
includesAll("components/AIComprehensiveAnalysisPanel.tsx", [
  "data-ai-analysis-minimum-weekly-news-items",
  "data-ai-analysis-weekly-news-selected-count",
  "data-ai-analysis-threshold-state",
  "What Changed This Week",
  "Market Context",
  "Business/Fund Context",
  "Risk Context",
  "fabricated analysis"
], "AI Comprehensive Analysis threshold and separation markers");

includesAll("app/assets/[ticker]/sources/page.tsx", [
  "supported-source-list-inspection-flow-v1",
  "source-list-blocked-or-limited-flow-v1",
  "data-source-list-state",
  "data-source-list-source-count",
  "data-source-list-freshness-overview",
  "data-source-list-source-use-policies",
  "data-source-list-allowlist-statuses",
  "data-source-list-full-text-export-count",
  "Source access is limited to supported, same-asset evidence packs",
  "does not create generated"
], "source-list route boundaries and source-use markers");
includesAll("components/SourceDrawer.tsx", [
  "data-source-drawer-mobile-presentation=\"bottom-sheet\"",
  "data-governed-golden-source-drawer=\"api-backed-source-groups\"",
  "data-source-drawer-close-control=\"native-details-summary\"",
  "data-source-use-policy",
  "data-source-allowlist-status",
  "allowedExcerptNote",
  "Source metadata is suppressed",
  "Supporting passage",
  "Related claim context"
], "source drawer citation metadata and mobile behavior markers");
includesAll("components/CitationChip.tsx", [
  "data-governed-golden-citation-binding=\"same-asset-source\""
], "governed golden citation binding marker");
includesAll("components/FreshnessLabel.tsx", [
  "data-governed-golden-freshness-label=\"api-backed-section-state\""
], "governed golden freshness marker");
includesAll("lib/assetOverview.ts", [
  "GOVERNED_GOLDEN_OVERVIEW_RENDERING_PROOF",
  "persisted knowledge-pack records plus generated-output cache validation"
], "governed golden overview API proof marker");
includesAll("lib/sourceDrawer.ts", [
  "GOVERNED_GOLDEN_SOURCE_DRAWER_RENDERING_PROOF",
  "allowed excerpts, and source-use policies"
], "governed golden source drawer API proof marker");
includesAll("lib/exportControls.ts", [
  "GOVERNED_GOLDEN_EXPORT_RENDERING_PROOF",
  "citations, source metadata, allowed excerpts, freshness labels, and disclaimers"
], "governed golden export API proof marker");
includesAll("components/GlossaryPopover.tsx", [
  "data-glossary-desktop-interaction=\"hover-click-focus-escape\"",
  "data-glossary-mobile-presentation=\"bottom-sheet\"",
  "data-glossary-close-control=\"button\"",
  "data-glossary-asset-context",
  "data-glossary-asset-citation-ids",
  "data-glossary-source-references",
  "Generic-only definition",
  "Definition unavailable for this glossary term"
], "contextual glossary interaction and evidence-boundary markers");

includesAll("components/AssetChatPanel.tsx", [
  "data-asset-chat-helper-role=\"bounded-asset-specific-helper\"",
  "data-asset-chat-scope=\"selected-asset-knowledge-pack\"",
  "data-asset-chat-general-finance-chatbot=\"false\"",
  "data-asset-chat-mobile-presentation=\"bottom-sheet-or-full-screen\"",
  "data-asset-chat-no-raw-transcript-analytics=\"true\"",
  "data-asset-chat-advice-redirect-before-answer=\"true\"",
  "data-asset-chat-comparison-redirect=\"/compare\"",
  "data-asset-chat-no-live-external=\"true\"",
  "data-chat-session-contract",
  "data-chat-session-browser-persistence=\"none\""
], "asset chat helper, safety, accountless, and no-live-call markers");
includesAll("app/compare/page.tsx", [
  "separate-comparison-workflow-v1",
  "data-prd-compare-builder-state",
  "data-compare-builder-generates-output=\"false\"",
  "data-compare-builder-live-external-calls=\"false\"",
  "data-compare-builder-suggestions=\"examples-not-recommendations\"",
  "data-prd-compare-result-layout=\"source-backed-deterministic-pack\"",
  "data-stock-etf-relationship-schema",
  "data-stock-etf-basket-structure=\"single-company-vs-etf-basket\""
], "comparison route builder, result, and stock-vs-ETF markers");
includesAll("components/ExportControls.tsx", [
  "data-export-supported-scope=\"markdown-json-citations-sources-freshness-disclaimer\"",
  "data-export-unrestricted-raw-text=\"false\"",
  "data-export-restricted-provider-payloads=\"false\"",
  "data-export-hidden-prompts=\"false\"",
  "data-export-raw-model-reasoning=\"false\"",
  "data-export-secret-exposure=\"false\"",
  "data-export-control-supported-formats=\"markdown-json\"",
  "data-export-control-scope=\"citations-sources-freshness-disclaimer\""
], "export scope and restricted-content markers");

includes("app/page.tsx", "SearchBox");
includes("app/page.tsx", "Understand a stock or ETF in plain English");
includes("app/page.tsx", "Search a U.S. stock or non-leveraged U.S. equity ETF");
includes("app/page.tsx", "single-asset-search");
includes("app/page.tsx", "separate-comparison");
includes("app/page.tsx", "VOO vs QQQ");
includes("app/page.tsx", "/compare");
includes("app/page.tsx", "lightweight-next-steps");
includes("app/page.tsx", "home-next-steps");
includes("app/assets/[ticker]/page.tsx", "Stable facts");
includes("app/assets/[ticker]/page.tsx", "Stale and unknown treatment");
includes("app/assets/[ticker]/page.tsx", "AssetLearningLayout");
includes("app/assets/[ticker]/page.tsx", "WeeklyNewsPanel");
includes("app/assets/[ticker]/page.tsx", "AIComprehensiveAnalysisPanel");
includes("app/assets/[ticker]/page.tsx", "data-prd-layout-marker");
includes("app/assets/[ticker]/page.tsx", "supported-asset-page-learning-flow-v1");
includes("app/assets/[ticker]/page.tsx", "header,beginner_summary,top_risks,key_facts,what_it_does_or_holds,weekly_news_focus,ai_comprehensive_analysis,deep_dive,ask_about_this_asset,sources,educational_disclaimer");
includes("app/assets/[ticker]/page.tsx", "data-prd-section=\"beginner_summary\"");
includes("app/assets/[ticker]/page.tsx", "data-prd-section=\"top_risks\"");
includes("app/assets/[ticker]/page.tsx", "data-prd-section=\"key_facts\"");
includes("app/assets/[ticker]/page.tsx", "data-prd-section=\"what_it_does_or_holds\"");
includes("app/assets/[ticker]/page.tsx", "data-prd-section=\"ask_about_this_asset\"");
includes("app/assets/[ticker]/page.tsx", "data-prd-section=\"educational_disclaimer\"");
includes("app/assets/[ticker]/page.tsx", "data-asset-what-section-id");
includes("app/assets/[ticker]/page.tsx", "data-helper-rail-source-access");
includes("app/assets/[ticker]/page.tsx", "data-beginner-primary-claim");
includes("app/assets/[ticker]/page.tsx", "data-beginner-summary-card-count=\"3\"");
includes("app/assets/[ticker]/page.tsx", "data-beginner-summary-card=\"what_it_is\"");
includes("app/assets/[ticker]/page.tsx", "data-beginner-summary-card=\"why_people_look\"");
includes("app/assets/[ticker]/page.tsx", "data-beginner-summary-card=\"main_caution\"");
includes("app/assets/[ticker]/page.tsx", "data-beginner-top-risk-count");
includes("app/assets/[ticker]/page.tsx", "data-beginner-stable-recent-separation");
includes("app/assets/[ticker]/page.tsx", "data-beginner-educational-framing");
includes("components/AssetHeader.tsx", "data-asset-header-layout");
includes("components/AssetHeader.tsx", "data-prd-section");
includes("components/AssetHeader.tsx", "data-asset-header-actions=\"compare,export,sources\"");
includes("components/AssetHeader.tsx", "Compare this asset");
includes("components/AssetHeader.tsx", "Export");
includes("components/AssetHeader.tsx", "View sources");
assert.equal(
  read("app/assets/[ticker]/page.tsx").includes("<SourceDrawer"),
  false,
  "Asset pages should not repeat full source drawer sections inline"
);
includes("app/assets/[ticker]/page.tsx", "data-asset-source-index");
includes("app/assets/[ticker]/page.tsx", "data-asset-source-entry-count");
includes("app/assets/[ticker]/page.tsx", "data-asset-source-full-drawers=\"dedicated-source-list\"");
includes("app/assets/[ticker]/page.tsx", "data-asset-source-drawer-repetition=\"removed\"");
includes("app/assets/[ticker]/page.tsx", "data-asset-source-index-entry");
includes("app/assets/[ticker]/page.tsx", "data-asset-source-list-link");
includes("app/assets/[ticker]/page.tsx", "Open full source details");
includes("app/assets/[ticker]/page.tsx", "InlineGlossaryText");
includes("app/assets/[ticker]/page.tsx", "inlineGlossaryMatches");
includes("app/assets/[ticker]/page.tsx", "sourceSection=\"beginner_summary.what_it_is\"");
includes("app/assets/[ticker]/page.tsx", "sourceSection=\"key_facts.label\"");
includes("app/assets/[ticker]/page.tsx", "sourceSection=\"what_it_does_or_holds.summary\"");
includes("app/assets/[ticker]/page.tsx", "fetchSupportedAssetGlossaryContexts");
includes("app/assets/[ticker]/page.tsx", "data-asset-glossary-rendering");
includes("app/assets/[ticker]/page.tsx", "beginnerGlossaryGroupsByAssetType");
assert.equal(
  read("app/assets/[ticker]/page.tsx").includes("data-beginner-glossary-area"),
  false,
  "Asset pages should not collect glossary terms into one standalone glossary area"
);
assert.equal(
  read("app/assets/[ticker]/page.tsx").includes("Glossary for this page"),
  false,
  "Asset pages should not render a standalone glossary section in the MVP reading flow"
);
includes("app/assets/[ticker]/page.tsx", "AssetChatPanel");
includes("app/assets/[ticker]/page.tsx", "fetchSupportedAssetDetails");
includes("app/assets/[ticker]/page.tsx", "fetchSupportedAssetOverview");
includes("app/assets/[ticker]/page.tsx", "fetchSupportedAssetWeeklyNews");
includes("app/assets/[ticker]/page.tsx", "fetchSupportedSourceDrawerResponse");
includes("app/assets/[ticker]/page.tsx", "data-asset-details-rendering");
includes("app/assets/[ticker]/page.tsx", "data-asset-overview-rendering");
includes("app/assets/[ticker]/page.tsx", "data-asset-source-drawer-rendering");
includes("app/assets/[ticker]/page.tsx", "data-asset-weekly-news-rendering");
includes("app/assets/[ticker]/page.tsx", "getWeeklyNewsFocusFixture");
includes("app/assets/[ticker]/page.tsx", "getAIComprehensiveAnalysisFixture");
includes("app/assets/[ticker]/page.tsx", "assetPageExportUrl");
includes("app/assets/[ticker]/page.tsx", "assetSourceListExportUrl");
includes("app/assets/[ticker]/page.tsx", "fetchSupportedAssetExportContract");
includes("app/assets/[ticker]/page.tsx", "data-asset-page-export-contract");
includes("app/assets/[ticker]/page.tsx", "data-asset-source-list-export-contract");
includes("app/assets/[ticker]/page.tsx", "Key source documents");
includes("app/assets/[ticker]/page.tsx", "getAssetComparisonSuggestions");
includes("app/assets/[ticker]/page.tsx", "ComparisonSuggestions");
includes("app/assets/[ticker]/page.tsx", "AssetEtfSections");
includes("app/assets/[ticker]/page.tsx", "AssetStockSections");
includes("app/assets/[ticker]/page.tsx", "hasEtfPrdSections");
includes("app/assets/[ticker]/page.tsx", "hasStockPrdSections");
includes("app/assets/[ticker]/sources/page.tsx", "SourceDrawer");
includes("app/assets/[ticker]/sources/page.tsx", "supported-source-list-inspection-flow-v1");
includes("app/assets/[ticker]/sources/page.tsx", "source-list-blocked-or-limited-flow-v1");
includes("app/assets/[ticker]/sources/page.tsx", "header,source_inspection_summary,freshness_source_use_overview,source_entries,educational_source_use_note");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-state");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-rendering");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-no-api-base-fallback");
includes("app/assets/[ticker]/sources/page.tsx", "deterministic_local_fixture");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-source-count");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-official-structured-count");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-freshness-overview");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-source-use-policies");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-allowlist-statuses");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-full-text-export-count");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-entry-count");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-educational-note");
includes("app/assets/[ticker]/sources/page.tsx", "Back to {asset.ticker} learning page");
includes("app/assets/[ticker]/sources/page.tsx", "fetchSupportedSourceDrawerResponse");
includes("app/assets/[ticker]/sources/page.tsx", "sourceListUnavailableMessage");
includes("app/assets/[ticker]/sources/page.tsx", "No source metadata is rendered because this ticker is recognized as unsupported");
includes("app/assets/[ticker]/sources/page.tsx", "No source metadata is rendered because this ticker is outside the Top-500 manifest-backed support scope");
includes("app/assets/[ticker]/sources/page.tsx", "source-list view");
includes("styles/globals.css", "source-list-summary-grid");
includes("styles/globals.css", "main\\[data-prd-source-list-marker\\]");
includes("components/SourceDrawer.tsx", "sourceDrawerStateFromSupportState");
includes("components/SourceDrawer.tsx", "allowedExcerptNote");
includes("components/SourceDrawer.tsx", "data-trust-metric-event");
includes("components/SourceDrawer.tsx", "source_drawer_usage");
includes("components/SourceDrawer.tsx", "citation_coverage");
includes("components/SourceDrawer.tsx", "freshness_accuracy");
includes("components/GlossaryPopover.tsx", "data-trust-metric-event");
includes("components/GlossaryPopover.tsx", "glossary_usage");
includes("components/ExportControls.tsx", "data-trust-metric-event");
includes("components/ExportControls.tsx", "export_usage");
includes("components/ExportControls.tsx", "data-trust-metric-citation-coverage-event");
includes("components/AssetChatPanel.tsx", "chat_answer_outcome");
includes("components/AssetChatPanel.tsx", "chat_safety_redirect");
includes("components/AssetChatPanel.tsx", "safety_redirect_rate");
includes("components/ComparisonSuggestions.tsx", "comparison_usage");
includes("app/compare/page.tsx", "data-trust-metric-left-ticker");
includes("app/compare/page.tsx", "data-trust-metric-right-ticker");
includes("lib/trustMetrics.ts", "trust-metrics-event-v1");
includes("lib/trustMetrics.ts", "/api/trust-metrics/catalog");
includes("lib/trustMetrics.ts", "validateTrustMetricsCatalogResponse");
includes("lib/trustMetrics.ts", "source_drawer_usage");
includes("lib/trustMetrics.ts", "glossary_usage");
includes("lib/trustMetrics.ts", "comparison_usage");
includes("lib/trustMetrics.ts", "export_usage");
includes("lib/trustMetrics.ts", "chat_answer_outcome");
includes("lib/trustMetrics.ts", "chat_safety_redirect");
includes("lib/trustMetrics.ts", "citation_coverage");
includes("lib/trustMetrics.ts", "freshness_accuracy");
includes("lib/trustMetrics.ts", "safety_redirect_rate");
includes("lib/trustMetrics.ts", "1970-01-01T00:00:00Z");
includes("lib/trustMetrics.ts", "validation_only");
includes("lib/trustMetrics.ts", "persistence_enabled");
includes("lib/trustMetrics.ts", "external_analytics_enabled");
includes("lib/trustMetrics.ts", "no_live_external_calls");
includes("lib/trustMetrics.ts", "buildTrustMetricSurfaceDescriptor");
includes("lib/assetOverview.ts", "/api/assets/");
includes("lib/assetOverview.ts", "/overview");
includes("lib/assetOverview.ts", "No API base URL is configured for supported asset overview fetches.");
includes("lib/assetOverview.ts", "type BackendOverviewSection");
includes("lib/assetOverview.ts", "sections: BackendOverviewSection\\[\\]");
includes("lib/assetOverview.ts", "toOverviewSection");
includes("lib/assetOverview.ts", "stockSections: backendSections");
includes("lib/assetOverview.ts", "etfSections: backendSections");
includesAll("app/assets/[ticker]/page.tsx", [
  "data-asset-overview-rendering={overviewRendering}",
  "data-asset-details-rendering={detailsRendering}",
  "data-asset-weekly-news-rendering={weeklyNewsRendering}",
  "data-asset-source-drawer-rendering={sourceDrawerRendering}",
  "data-asset-glossary-rendering={glossaryRendering}",
  "backend_contract",
  "local_fixture"
], "T-118 frontend API-backed rendering markers with deterministic fallback");
includesAll("lib/assetOverview.ts", [
  "isSupportedAssetOverviewResponse",
  "mergeAssetFixtureWithOverview",
  "Asset overview response did not match the expected backend response contract."
], "T-118 overview API contract validation");
includesAll("lib/sourceDrawer.ts", [
  "isAssetSourceDrawerResponse",
  "toSourceDrawerContractData",
  "allowedExcerptNote",
  "Source drawer response did not match the expected backend response contract."
], "T-118 source drawer API contract validation");
includes("lib/assetDetails.ts", "/api/assets/");
includes("lib/assetDetails.ts", "/details");
includes("lib/assetDetails.ts", "No API base URL is configured for supported asset detail fetches.");
includes("lib/assetWeeklyNews.ts", "/api/assets/");
includes("lib/assetWeeklyNews.ts", "/weekly-news");
includes("lib/assetWeeklyNews.ts", "No API base URL is configured for supported asset weekly-news fetches.");
includes("lib/sourceDrawer.ts", "asset-source-drawer-v1");
includes("lib/sourceDrawer.ts", "/api/assets/");
includes("lib/sourceDrawer.ts", "/sources");
includes("lib/sourceDrawer.ts", "sourceDrawerEntriesByDocumentId");
includes("lib/assetGlossary.ts", "glossary-asset-context-v1");
includes("lib/assetGlossary.ts", "/api/assets/");
includes("lib/assetGlossary.ts", "/glossary");
includes("lib/assetGlossary.ts", "No API base URL is configured for supported asset glossary fetches.");
includes("lib/assetGlossary.ts", "generic_definitions_are_not_evidence");
includes("lib/assetGlossary.ts", "restricted_text_exposed");
includes("lib/assetGlossary.ts", "supports_asset_specific_context");
includes("lib/assetGlossary.ts", "summary_allowed");
includes("app/compare/page.tsx", "Bottom line for beginners");
includes("app/compare/page.tsx", "ComparisonSourceDetails");
includes("app/compare/page.tsx", "comparisonExportUrl");
includes("app/compare/page.tsx", "data-export-unavailable-state");
includes("app/compare/page.tsx", "getComparisonCitationMetadata");
includes("app/compare/page.tsx", "getComparisonAvailabilityState");
includes("app/compare/page.tsx", "getComparePageSuggestions");
includes("app/compare/page.tsx", "ComparisonSuggestions");
includes("app/compare/page.tsx", "data-compare-availability-state");
includes("app/compare/page.tsx", "data-compare-rendered-state");
includes("app/compare/page.tsx", "data-compare-generated-section");
includes("app/compare/page.tsx", "data-compare-unavailable-state");
includes("app/compare/page.tsx", "fetchSupportedComparisonExportContract");
includes("app/compare/page.tsx", "comparisonExportContract");
includes("app/compare/page.tsx", "Backend comparison export contract validated");
includes("app/compare/page.tsx", "separate-comparison-workflow-v1");
includes("app/compare/page.tsx", "data-prd-compare-builder-state");
includes("app/compare/page.tsx", "data-compare-builder-generates-output=\"false\"");
includes("app/compare/page.tsx", "Compare two supported assets");
includes("app/compare/page.tsx", "One asset is selected");
includes("app/compare/page.tsx", "data-compare-builder-no-generated-output");
includes("app/compare/page.tsx", "data-compare-builder-selected-ticker");
includes("app/compare/page.tsx", "data-compare-builder-suggestions=\"examples-not-recommendations\"");
includes("app/compare/page.tsx", "data-prd-compare-result-layout=\"source-backed-deterministic-pack\"");
includes("app/compare/page.tsx", "header,selected_assets,beginner_bottom_line,stock_vs_etf_relationship_context,key_differences,export_controls,suggested_comparisons,source_metadata");
includes("app/compare/page.tsx", "data-prd-section=\"selected_assets\"");
includes("app/compare/page.tsx", "data-prd-section=\"beginner_bottom_line\"");
includes("app/compare/page.tsx", "data-prd-section=\"stock_vs_etf_relationship_context\"");
includes("app/compare/page.tsx", "data-prd-section=\"key_differences\"");
includes("app/compare/page.tsx", "data-prd-section=\"export_controls\"");
includes("app/compare/page.tsx", "data-prd-section=\"suggested_comparisons\"");
includes("app/compare/page.tsx", "data-prd-section=\"source_metadata\"");
includes("app/compare/page.tsx", "bottom_line_for_beginners");
includes("app/compare/page.tsx", "key_differences");
includes("app/compare/page.tsx", "source_documents");
includes("app/compare/page.tsx", "evidence_availability");
includes("components/AssetChatPanel.tsx", "Ask about this asset");
includes("components/AssetChatPanel.tsx", "data-chat-state");
includes("components/AssetChatPanel.tsx", "data-chat-citation-id");
includes("components/AssetChatPanel.tsx", "Chat source metadata");
includes("components/AssetChatPanel.tsx", "Save chat transcript");
includes("components/AssetChatPanel.tsx", "chat-transcript");
includes("components/AssetChatPanel.tsx", "Educational redirect");
includes("components/AssetChatPanel.tsx", "Comparison workflow redirect");
includes("components/AssetChatPanel.tsx", "Unsupported or unknown asset");
includes("components/AssetChatPanel.tsx", "Insufficient evidence");
includes("components/AssetChatPanel.tsx", "data-chat-session-contract");
includes("components/AssetChatPanel.tsx", "data-chat-session-conversation-id");
includes("components/AssetChatPanel.tsx", "data-chat-session-lifecycle");
includes("components/AssetChatPanel.tsx", "data-chat-session-export-available");
includes("components/AssetChatPanel.tsx", "data-chat-session-expires-at");
includes("components/AssetChatPanel.tsx", "data-chat-session-browser-persistence=\"none\"");
includes("components/AssetChatPanel.tsx", "data-chat-starter-group");
includes("components/AssetChatPanel.tsx", "data-chat-starter-intent");
includes("components/AssetChatPanel.tsx", "data-asset-chat-helper-role=\"bounded-asset-specific-helper\"");
includes("components/AssetChatPanel.tsx", "data-asset-chat-scope=\"selected-asset-knowledge-pack\"");
includes("components/AssetChatPanel.tsx", "data-asset-chat-general-finance-chatbot=\"false\"");
includes("components/AssetChatPanel.tsx", "data-asset-chat-mobile-presentation=\"bottom-sheet-or-full-screen\"");
includes("components/AssetChatPanel.tsx", "data-asset-chat-internal-scroll=\"true\"");
includes("components/AssetChatPanel.tsx", "data-asset-chat-helper-affordance=\"sticky-asset-context-header\"");
includes("components/AssetChatPanel.tsx", "data-asset-chat-no-raw-transcript-analytics=\"true\"");
includes("components/AssetChatPanel.tsx", "data-asset-chat-advice-redirect-before-answer=\"true\"");
includes("components/AssetChatPanel.tsx", "data-asset-chat-comparison-redirect=\"/compare\"");
includes("components/AssetChatPanel.tsx", "data-asset-chat-no-live-external=\"true\"");
includes("components/AssetChatPanel.tsx", "data-asset-chat-no-overlap=\"in-flow-bottom-sheet-style\"");
includes("components/AssetChatPanel.tsx", "data-asset-chat-scroll-region=\"mobile-internal-scroll\"");
includes("components/AssetChatPanel.tsx", "data-asset-chat-answer-order=\"redirect-label-before-answer-content\"");
includes("components/AssetChatPanel.tsx", "not a general finance chatbot");
includes("components/AssetChatPanel.tsx", "transcript text is not used for product");
includes("components/AssetChatPanel.tsx", "business-model");
includes("components/AssetChatPanel.tsx", "holdings-exposure");
includes("components/AssetChatPanel.tsx", "top-risk");
includes("components/AssetChatPanel.tsx", "recent-developments");
includes("components/AssetChatPanel.tsx", "advice-boundary");
includes("components/AssetChatPanel.tsx", "business model work");
includes("components/AssetChatPanel.tsx", "fund exposure");
includes("components/AssetChatPanel.tsx", "without a personal recommendation");
includes("components/AssetModeLayout.tsx", "AssetLearningLayout");
includes("components/AssetModeLayout.tsx", "data-asset-learning-layout");
includes("components/AssetModeLayout.tsx", "data-asset-section-region");
includes("components/AssetModeLayout.tsx", "data-beginner-section-region");
includes("components/AssetModeLayout.tsx", "data-deep-dive-section-region");
includes("components/AssetModeLayout.tsx", "data-prd-learning-flow");
includes("components/AssetModeLayout.tsx", "data-prd-section-order");
includes("components/AssetModeLayout.tsx", "data-mobile-sticky-actions=\"ask-compare-sources\"");
includes("components/AssetModeLayout.tsx", "data-mobile-actions-no-overlap=\"in-flow-sticky\"");
includes("components/AssetModeLayout.tsx", "data-asset-helper-rail");
includes("components/AssetModeLayout.tsx", "data-helper-rail-tools=\"ask,compare,freshness,sources\"");
includes("components/AssetModeLayout.tsx", "data-prd-section=\"deep_dive\"");
includes("components/AssetModeLayout.tsx", "data-prd-section=\"sources\"");
includes("components/AssetModeLayout.tsx", "Deep Dive");
assert.equal(read("components/AssetModeLayout.tsx").includes("Beginner Mode"), false, "Asset layout should not expose a visible Beginner Mode wrapper");
assert.equal(read("components/AssetModeLayout.tsx").includes("Deep-Dive Mode"), false, "Asset layout should not expose a visible Deep-Dive Mode wrapper");
includes("components/WeeklyNewsPanel.tsx", "Weekly News Focus");
includes("components/WeeklyNewsPanel.tsx", "data-weekly-news-state");
includes("components/WeeklyNewsPanel.tsx", "data-weekly-news-configured-max");
includes("components/WeeklyNewsPanel.tsx", "data-weekly-news-selected-count");
includes("components/WeeklyNewsPanel.tsx", "data-weekly-news-suppressed-candidate-count");
includes("components/WeeklyNewsPanel.tsx", "data-weekly-news-evidence-limited-state");
includes("components/WeeklyNewsPanel.tsx", "data-weekly-news-empty-behavior");
includes("components/WeeklyNewsPanel.tsx", "data-weekly-news-limited-verified-set");
includes("components/WeeklyNewsPanel.tsx", "data-weekly-news-item-count");
includes("components/WeeklyNewsPanel.tsx", "data-beginner-weekly-news-focus");
includes("components/WeeklyNewsPanel.tsx", "data-beginner-recent-developments");
includes("components/WeeklyNewsPanel.tsx", "Source quality:");
includes("components/WeeklyNewsPanel.tsx", "Source-use policy:");
includes("components/WeeklyNewsPanel.tsx", "No major Weekly News Focus items found");
includes("components/AIComprehensiveAnalysisPanel.tsx", "AI Comprehensive Analysis");
includes("components/AIComprehensiveAnalysisPanel.tsx", "data-ai-analysis-state");
includes("components/AIComprehensiveAnalysisPanel.tsx", "data-ai-analysis-available");
includes("components/AIComprehensiveAnalysisPanel.tsx", "data-ai-analysis-minimum-weekly-news-items");
includes("components/AIComprehensiveAnalysisPanel.tsx", "data-ai-analysis-weekly-news-selected-count");
includes("components/AIComprehensiveAnalysisPanel.tsx", "data-ai-analysis-threshold-state");
includes("components/AIComprehensiveAnalysisPanel.tsx", "data-ai-analysis-evidence-threshold");
includes("components/AIComprehensiveAnalysisPanel.tsx", "What Changed This Week");
includes("components/AIComprehensiveAnalysisPanel.tsx", "Market Context");
includes("components/AIComprehensiveAnalysisPanel.tsx", "Business/Fund Context");
includes("components/AIComprehensiveAnalysisPanel.tsx", "Risk Context");
includes("components/AIComprehensiveAnalysisPanel.tsx", "data-ai-analysis-section-order");
includes("components/AIComprehensiveAnalysisPanel.tsx", "fabricated analysis");
includes("components/ExportControls.tsx", "data-export-controls");
includes("components/ExportControls.tsx", "data-export-relative-api");
includes("components/ExportControls.tsx", "data-export-no-live-external");
includes("components/ExportControls.tsx", "data-export-supported-scope=\"markdown-json-citations-sources-freshness-disclaimer\"");
includes("components/ExportControls.tsx", "data-export-mobile-behavior=\"compact-stacked-controls\"");
includes("components/ExportControls.tsx", "data-export-mobile-no-overlap=\"in-flow-compact-panel\"");
includes("components/ExportControls.tsx", "data-export-unrestricted-raw-text=\"false\"");
includes("components/ExportControls.tsx", "data-export-restricted-provider-payloads=\"false\"");
includes("components/ExportControls.tsx", "data-export-hidden-prompts=\"false\"");
includes("components/ExportControls.tsx", "data-export-raw-model-reasoning=\"false\"");
includes("components/ExportControls.tsx", "data-export-secret-exposure=\"false\"");
includes("components/ExportControls.tsx", "data-export-control");
includes("components/ExportControls.tsx", "data-export-href");
includes("components/ExportControls.tsx", "data-export-contract-rendering");
includes("components/ExportControls.tsx", "data-export-contract-source");
includes("components/ExportControls.tsx", "data-export-contract-marker");
includes("components/ExportControls.tsx", "data-export-control-mobile-behavior=\"compact-full-width\"");
includes("components/ExportControls.tsx", "data-export-control-supported-formats=\"markdown-json\"");
includes("components/ExportControls.tsx", "data-export-control-scope=\"citations-sources-freshness-disclaimer\"");
includes("components/ExportControls.tsx", "data-export-contract-left-ticker");
includes("components/ExportControls.tsx", "data-export-contract-right-ticker");
includes("components/ExportControls.tsx", "data-export-contract-comparison-id");
includes("components/ExportControls.tsx", "Backend export contract validated");
includes("components/ExportControls.tsx", "Local fallback rendering");
includes("components/ExportControls.tsx", "data-export-post-url");
includes("components/ExportControls.tsx", "data-chat-export-contract-source");
includes("components/ExportControls.tsx", "data-chat-export-conversation-id");
includes("components/ExportControls.tsx", "data-chat-export-session-lifecycle");
includes("components/ExportControls.tsx", "data-chat-export-session-export-available");
includes("components/ExportControls.tsx", "data-chat-export-validation-schema");
includes("components/ExportControls.tsx", "data-chat-export-binding-scope");
includes("components/ExportControls.tsx", "data-chat-export-citation-count");
includes("components/ExportControls.tsx", "data-chat-export-source-count");
includes("components/ExportControls.tsx", "data-chat-export-safe-session-records");
includes("components/ExportControls.tsx", "data-chat-export-used-existing-chat-contract");
includes("components/ExportControls.tsx", "data-chat-export-no-raw-transcript-analytics=\"true\"");
includes("components/ExportControls.tsx", "data-chat-export-no-hidden-prompts=\"true\"");
includes("components/ExportControls.tsx", "data-chat-export-no-raw-model-reasoning=\"true\"");
includes("components/ExportControls.tsx", "data-chat-export-mobile-result=\"internal-scroll\"");
includes("components/ExportControls.tsx", "data-export-copy-markdown");
includes("components/ExportControls.tsx", "data-export-rendered-markdown");
includes("components/ComparisonSuggestions.tsx", "data-comparison-suggestions");
includes("components/ComparisonSuggestions.tsx", "data-comparison-suggestion-selected-ticker");
includes("components/ComparisonSuggestions.tsx", "data-comparison-suggestion-state");
includes("components/ComparisonSuggestions.tsx", "data-comparison-suggestion-target");
includes("components/ComparisonSuggestions.tsx", "data-comparison-suggestion-url");
includes("components/ComparisonSuggestions.tsx", "data-comparison-suggestion-availability-source");
includes("components/ComparisonSuggestions.tsx", "data-comparison-suggestion-example-only");
includes("components/ComparisonSuggestions.tsx", "data-comparison-no-local-pack");
includes("components/ComparisonSuggestions.tsx", "data-comparison-requested-availability-state");
includes("lib/compareSuggestions.ts", "localComparisonPairs");
includes("lib/compareSuggestions.ts", "VOO");
includes("lib/compareSuggestions.ts", "QQQ");
includes("lib/compareSuggestions.ts", "buildSuggestion\\(rightTicker, leftTicker, \\{ exampleOnly: false \\}\\)");
includes("lib/compareSuggestions.ts", "No local source-backed comparison pack");
includes("lib/compareSuggestions.ts", "not facts about the requested pair");
includes("lib/compareSuggestions.ts", "requestedAvailabilityState");
includes("components/AssetStockSections.tsx", "data-stock-prd-sections");
includes("components/AssetStockSections.tsx", "data-stock-section-id");
includes("components/AssetStockSections.tsx", "data-shared-prd-section-shell");
includes("components/AssetStockSections.tsx", "data-deep-dive-duplicate-sections-filtered=\"top_risks,recent_developments,educational_suitability\"");
includes("components/AssetStockSections.tsx", "data-stock-stable-recent-separation");
includes("components/AssetStockSections.tsx", "data-stock-top-risk-count");
includes("components/AssetStockSections.tsx", "InlineGlossaryText");
includes("components/AssetStockSections.tsx", "glossaryMatches");
includes("components/AssetStockSections.tsx", "No citation chip is shown because this item is an explicit evidence gap");
includes("components/AssetEtfSections.tsx", "data-etf-prd-sections");
includes("components/AssetEtfSections.tsx", "data-etf-section-id");
includes("components/AssetEtfSections.tsx", "data-shared-prd-section-shell");
includes("components/AssetEtfSections.tsx", "data-deep-dive-duplicate-sections-filtered=\"etf_specific_risks,recent_developments,educational_suitability\"");
includes("components/AssetEtfSections.tsx", "data-etf-stable-recent-separation");
includes("components/AssetEtfSections.tsx", "data-etf-top-risk-count");
includes("components/AssetEtfSections.tsx", "InlineGlossaryText");
includes("components/AssetEtfSections.tsx", "glossaryMatches");
includes("components/AssetEtfSections.tsx", "No citation chip is shown because this ETF item is an explicit evidence gap");
includes("lib/assetChat.ts", "/api/assets/");
includes("lib/assetChat.ts", "/chat");
includes("lib/assetChat.ts", "publicApiEndpoint");
includes("lib/assetChat.ts", "conversation_id");
includes("lib/assetChat.ts", "chat-session-contract-v1");
includes("lib/assetChat.ts", "export_available");
includes("lib/exportControls.ts", "/api/assets/");
includes("lib/exportControls.ts", "publicApiEndpoint");
includes("lib/exportControls.ts", "requiredApiEndpoint");
includes("lib/exportControls.ts", "/export\\?export_format=");
includes("lib/exportControls.ts", "/sources/export\\?export_format=");
includes("lib/exportControls.ts", "fetchSupportedAssetExportContract");
includes("lib/exportControls.ts", "fetchSupportedComparisonExportContract");
includes("lib/exportControls.ts", "asset_page");
includes("lib/exportControls.ts", "asset_source_list");
includes("lib/exportControls.ts", "comparison");
includes("lib/exportControls.ts", "export-validation-v1");
includes("lib/exportControls.ts", "same_asset");
includes("lib/exportControls.ts", "same_comparison_pack");
includes("lib/exportControls.ts", "No API base URL is configured for supported asset export contract fetches.");
includes("lib/exportControls.ts", "No API base URL is configured for supported comparison export contract fetches.");
includes("lib/exportControls.ts", "same_asset_citation_bindings_only");
includes("lib/exportControls.ts", "same_asset_source_bindings_only");
includes("lib/exportControls.ts", "same_comparison_pack_citation_bindings_only");
includes("lib/exportControls.ts", "same_comparison_pack_source_bindings_only");
includes("lib/exportControls.ts", "used_existing_overview_contract");
includes("lib/exportControls.ts", "used_existing_comparison_contract");
includes("lib/exportControls.ts", "no_live_external_calls");
includes("lib/exportControls.ts", "/api/compare/export\\?");
includes("lib/exportControls.ts", "/chat/export");
includes("lib/exportControls.ts", "postChatTranscriptExport");
includes("lib/exportControls.ts", "isSupportedChatSessionMarkdownExport");
includes("lib/exportControls.ts", "chat_transcript");
includes("lib/exportControls.ts", "session_contract");
includes("lib/exportControls.ts", "single_turn_fallback");
includes("lib/exportControls.ts", "local_accountless_chat_session");
includes("lib/exportControls.ts", "used_existing_chat_contract");
includes("lib/exportControls.ts", "no_factual_evidence");
includes("lib/exportControls.ts", "safe session turn records");
includes("lib/compare.ts", "source_documents");
includes("lib/compare.ts", "publicApiEndpoint\\(\"/api/compare\"\\)");
includes("lib/compare.ts", "c_fact_voo_benchmark");
includes("lib/compare.ts", "c_fact_qqq_benchmark");
includes("lib/compare.ts", "src_voo_fact_sheet_fixture");
includes("lib/compare.ts", "src_qqq_fact_sheet_fixture");
includes("lib/compare.ts", "evidence_availability");
includes("lib/compare.ts", "availability_state");
includes("lib/compare.ts", "eligible_not_cached");
includes("lib/compare.ts", "out_of_scope");
includes("lib/compare.ts", "no_local_pack");
includes("lib/compare.ts", "source_use_policy");
includes("lib/compare.ts", "permitted_operations");
includes("components/ComparisonSourceDetails.tsx", "Comparison source metadata");
includes("components/ComparisonSourceDetails.tsx", "data-comparison-source-document-id");
includes("components/ComparisonSourceDetails.tsx", "Official source");
includes("components/ComparisonSourceDetails.tsx", "Published or as of");
includes("components/ComparisonSourceDetails.tsx", "Related comparison claims");
includes("components/ComparisonSourceDetails.tsx", "Supporting passage");
includes("components/ComparisonSourceDetails.tsx", "data-comparison-source-quality");
includes("components/ComparisonSourceDetails.tsx", "data-comparison-source-use-policy");
includes("components/ComparisonSourceDetails.tsx", "data-comparison-source-asset");
includes("components/SourceDrawer.tsx", "data-source-document-id");
includes("components/SourceDrawer.tsx", "data-source-drawer-mobile-presentation=\"bottom-sheet\"");
includes("components/SourceDrawer.tsx", "data-source-drawer-close-control=\"native-details-summary\"");
includes("components/SourceDrawer.tsx", "source-summary-title");
includes("components/SourceDrawer.tsx", "Published or as of");
includes("components/SourceDrawer.tsx", "Related claim context");
includes("components/SourceDrawer.tsx", "Supporting passage");
includes("components/SourceDrawer.tsx", "Official source");
includes("components/SourceDrawer.tsx", "URL");
includes("components/CitationChip.tsx", "data-source-document-id");
includes("components/CitationChip.tsx", "Open source details");
includes("styles/globals.css", "@media \\(max-width: 620px\\)");
includes("styles/globals.css", "max-height: min\\(76vh, 640px\\)");
includes("styles/globals.css", "overscroll-behavior: contain");
includes("styles/globals.css", "source-summary-title");
includes("styles/globals.css", ".asset-mobile-actions");
includes("styles/globals.css", "position: sticky");
includes("styles/globals.css", "grid-template-columns: repeat\\(3, minmax\\(0, 1fr\\)\\)");
includes("styles/globals.css", "overflow-x: hidden");
includes("styles/globals.css", "overflow-wrap: anywhere");
includes("styles/globals.css", "white-space: normal");
includes("styles/globals.css", ".asset-chat-panel");
includes("styles/globals.css", ".asset-chat-scroll-region");
includes("styles/globals.css", ".asset-chat-helper-header");
includes("styles/globals.css", "max-height: min\\(82vh, 720px\\)");
includes("styles/globals.css", ".export-controls");
includes("styles/globals.css", ".export-result");
includes("styles/globals.css", "max-height: min\\(58vh, 520px\\)");
includes("styles/globals.css", ".asset-helper-rail");
includes("styles/globals.css", ".asset-source-index");
includes("styles/globals.css", ".asset-source-index-card");
includes("styles/globals.css", ".compact-source-meta");
includes("styles/globals.css", "max-height: calc\\(100vh - 36px\\)");
includes("styles/globals.css", ".compare-builder-form");
includes("styles/globals.css", ".selected-builder-card");
includes("styles/globals.css", ".relationship-badge-grid");
includes("styles/globals.css", ".stock-etf-basket-structure");
includes("styles/globals.css", ".source-list-summary-grid");
includes("styles/globals.css", ".comparison-suggestion-list");
includes("styles/globals.css", "scroll-margin-top: 88px");
includes("components/SearchBox.tsx", "data-search-state");
includes("components/SearchBox.tsx", "resolveLocalSearchResponse");
includes("components/SearchBox.tsx", "resolveSearchResponse");
includes("components/SearchBox.tsx", "data-search-supported-result");
includes("components/SearchBox.tsx", "data-search-ingestion-needed-result");
includes("components/SearchBox.tsx", "data-search-eligible-not-cached-result");
includes("components/SearchBox.tsx", "data-search-multi-result");
includes("components/SearchBox.tsx", "data-search-ambiguous-result");
includes("components/SearchBox.tsx", "data-search-disambiguation-required");
includes("components/SearchBox.tsx", "data-search-unsupported-result");
includes("components/SearchBox.tsx", "data-search-out-of-scope-result");
includes("components/SearchBox.tsx", "data-search-unknown-result");
includes("components/SearchBox.tsx", "data-search-result-link");
includes("components/SearchBox.tsx", "data-search-support-classification");
includes("components/SearchBox.tsx", "data-search-open-generated-page");
includes("components/SearchBox.tsx", "data-search-can-open-generated-page");
includes("components/SearchBox.tsx", "Search a ticker or name, like VOO, QQQ, or Apple");
includes("components/SearchBox.tsx", "Examples only, not recommendations");
includes("components/SearchBox.tsx", "data-home-primary-action=\"single-asset-search\"");
includes("components/SearchBox.tsx", "data-search-support-state-idle-visible=\"false\"");
includes("components/SearchBox.tsx", "data-search-support-state-labels={V04_SUPPORT_STATE_CHIPS.join");
includes("components/SearchBox.tsx", "result-state-chip");
includes("components/SearchBox.tsx", "data-search-comparison-result");
includes("components/SearchBox.tsx", "data-search-special-autocomplete-result");
includes("components/SearchBox.tsx", "data-search-comparison-route");
includes("components/SearchBox.tsx", "data-search-open-comparison-route");
includes("components/SearchBox.tsx", "Pending ingestion");
includes("components/SearchBox.tsx", "Out of scope");
includes("components/SearchBox.tsx", "No supported stock or ETF found for");
includes("components/SearchBox.tsx", "No generated asset page, grounded chat, or comparison is available today");
includes("components/SearchBox.tsx", "No facts are invented for this ticker or name");
const searchBoxSource = read("components/SearchBox.tsx");
assert.equal(searchBoxSource.includes("support-state-legend"), false, "Idle home search should not render the full support-state legend");
assert.ok(
  searchBoxSource.indexOf("data-search-result-state-label") < searchBoxSource.indexOf("export function SearchBox"),
  "Support-state chips should be part of actual search result identity"
);
includes("lib/search.ts", "comparison_route");
includes("lib/search.ts", "/compare\\?left=");
includes("lib/search.ts", "VOO, QQQ, AAPL, NVDA, and SOXX");
includes("lib/search.ts", "We found this ticker, but it is not supported in v1.");
includes("lib/search.ts", "Learn the Ticker currently supports U.S.-listed common stocks in the Top-500 manifest and ETFs in the approved supported ETF manifest.");
for (const blockedFallbackMarker of [
  "ARKK",
  "BND",
  "GLD",
  "AOR",
  "VXX",
  "active_etf",
  "fixed_income_etf",
  "commodity_etf",
  "multi_asset_etf",
  "etf_like_product_scope"
]) {
  includes("lib/search.ts", blockedFallbackMarker);
}
includesAll("lib/apiEndpoints.ts", [
  "NEXT_PUBLIC_API_BASE_URL",
  "API_BASE_URL",
  "http://127.0.0.1:8000",
  "publicApiEndpoint",
  "requiredApiEndpoint"
], "local browser API helpers prefer configured FastAPI and keep a relative fallback");
const searchRouteSource = read("lib/search.ts");
assert.ok(
  searchRouteSource.indexOf("function comparisonRouteResult") < searchRouteSource.indexOf("export async function resolveSearchResponse"),
  "A vs B search routing should be defined before backend-preferred search resolution"
);
assert.ok(
  searchRouteSource.indexOf("const comparison = comparisonRouteResult(raw_query)") <
    searchRouteSource.indexOf("return await fetchBackendSearchResponse"),
  "A vs B search patterns should route to the separate comparison workflow before backend search"
);
includesAll("lib/search.ts", [
  "comparisonTickerFromToken",
  "status: \"comparison\"",
  "support_classification: \"comparison_route\"",
  "comparison_route: route",
  "comparison_left_ticker: left",
  "comparison_right_ticker: right",
  "can_open_generated_page: false",
  "can_answer_chat: false",
  "Comparison is a separate workflow. Open the comparison page"
], "AAPL vs VOO search pattern routes to compare without changing home into a comparison builder");
includesAll("next.config.mjs", [
  "NEXT_PUBLIC_API_BASE_URL",
  "API_BASE_URL",
  "/api/:path*",
  "http://127.0.0.1:8000"
], "local Next API proxy rewrite to FastAPI backend");
includes("components/FreshnessLabel.tsx", "data-freshness-state");
includes("components/GlossaryPopover.tsx", "data-glossary-term");
includes("components/GlossaryPopover.tsx", "data-glossary-visible-label");
includes("components/GlossaryPopover.tsx", "data-glossary-placement");
includes("components/GlossaryPopover.tsx", "glossary-trigger-inline");
includes("components/GlossaryPopover.tsx", "data-glossary-category");
includes("components/GlossaryPopover.tsx", "data-glossary-definition");
includes("components/GlossaryPopover.tsx", "data-glossary-why-it-matters");
includes("components/GlossaryPopover.tsx", "data-glossary-beginner-mistake");
includes("components/GlossaryPopover.tsx", "data-glossary-available");
includes("components/GlossaryPopover.tsx", "data-glossary-asset-context");
includes("components/GlossaryPopover.tsx", "data-glossary-asset-citation-ids");
includes("components/GlossaryPopover.tsx", "data-glossary-source-references");
includes("components/GlossaryPopover.tsx", "data-glossary-uncertainty-labels");
includes("components/GlossaryPopover.tsx", "Generic-only definition");
includes("components/GlossaryPopover.tsx", "Definition unavailable for this glossary term");
includes("components/GlossaryPopover.tsx", "aria-expanded");
includes("components/GlossaryPopover.tsx", "role=\"dialog\"");
includes("components/GlossaryPopover.tsx", "data-glossary-desktop-interaction=\"hover-click-focus-escape\"");
includes("components/GlossaryPopover.tsx", "data-glossary-mobile-presentation=\"bottom-sheet\"");
includes("components/GlossaryPopover.tsx", "data-glossary-close-control=\"button\"");
includes("components/GlossaryPopover.tsx", "data-glossary-trigger-mode=\"hover-click-focus\"");
includes("components/GlossaryPopover.tsx", "onMouseEnter");
includes("components/GlossaryPopover.tsx", "onMouseLeave");
includes("components/GlossaryPopover.tsx", "onFocus");
includes("components/GlossaryPopover.tsx", "onBlur");
includes("components/GlossaryPopover.tsx", "event.key === \"Escape\"");
includes("components/GlossaryPopover.tsx", "data-glossary-visible-term-context");
includes("components/GlossaryPopover.tsx", "data-glossary-bottom-sheet-height");
includes("components/GlossaryPopover.tsx", "data-glossary-internal-scroll=\"true\"");
includes("components/InlineGlossaryText.tsx", "data-glossary-inline-region");
includes("components/InlineGlossaryText.tsx", "data-glossary-inline-source-section");
includes("components/InlineGlossaryText.tsx", "data-glossary-inline-term-count");
includes("components/InlineGlossaryText.tsx", "placement=\"inline\"");
includes("components/InlineGlossaryText.tsx", "label=\\{segment\\.text\\}");
includes("styles/globals.css", ".glossary-popover");
includes("styles/globals.css", ".glossary-inline-text");
includes("styles/globals.css", "\\.glossary-wrap\\[data-glossary-placement=\"inline\"\\]");
includes("styles/globals.css", "max-height: min\\(74vh, 620px\\)");
includes("styles/globals.css", "position: fixed");
includes("styles/globals.css", "bottom: 0");
includes("styles/globals.css", ".glossary-card-header");
includes("styles/globals.css", ".glossary-close-button");

const glossarySource = read("lib/glossary.ts");
const requiredGlossaryTerms = [
  "expense ratio",
  "AUM",
  "market cap",
  "P/E ratio",
  "forward P/E",
  "dividend yield",
  "revenue",
  "gross margin",
  "operating margin",
  "EPS",
  "free cash flow",
  "debt",
  "benchmark",
  "index",
  "holdings",
  "top 10 concentration",
  "sector exposure",
  "country exposure",
  "tracking error",
  "tracking difference",
  "NAV",
  "premium/discount",
  "bid-ask spread",
  "liquidity",
  "rebalancing",
  "market risk",
  "concentration risk",
  "credit risk",
  "interest-rate risk"
];
for (const term of requiredGlossaryTerms) {
  assert.match(glossarySource, new RegExp(`term: "${term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"`), `Glossary should include ${term}`);
}
assert.ok(
  (glossarySource.match(/definition:/g) ?? []).length >= requiredGlossaryTerms.length,
  "Each required glossary term should have a definition"
);
assert.ok(
  (glossarySource.match(/whyItMatters:/g) ?? []).length >= requiredGlossaryTerms.length,
  "Each required glossary term should explain why it matters"
);
assert.ok(
  (glossarySource.match(/beginnerMistake:/g) ?? []).length >= requiredGlossaryTerms.length,
  "Each required glossary term should include a beginner mistake"
);
for (const marker of [
  "stock-business-metrics",
  "stock-valuation-risk",
  "etf-fund-basics",
  "etf-exposure-risk",
  "etf-trading-tracking",
  "\"market cap\", \"revenue\", \"operating margin\", \"EPS\", \"free cash flow\", \"debt\"",
  "\"expense ratio\", \"AUM\", \"benchmark\", \"index\", \"holdings\"",
  "\"bid-ask spread\", \"premium/discount\", \"NAV\", \"liquidity\", \"tracking error\", \"tracking difference\""
]) {
  assert.match(glossarySource, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `Glossary grouping should include ${marker}`);
}
for (const tickerSpecificMarker of ["AAPL", "VOO", "QQQ", "Apple Inc.", "Vanguard S&P 500 ETF", "Invesco QQQ Trust"]) {
  assert.equal(glossarySource.includes(tickerSpecificMarker), false, `Glossary should not add asset-specific claim ${tickerSpecificMarker}`);
}

const assetPage = read("app/assets/[ticker]/page.tsx");
const comparePage = read("app/compare/page.tsx");
assert.equal(
  comparePage.includes('query?.left?.toUpperCase() ?? "VOO"'),
  false,
  "Compare page should not silently default an empty builder to VOO"
);
assert.equal(
  comparePage.includes('query?.right?.toUpperCase() ?? "QQQ"'),
  false,
  "Compare page should not silently default an empty builder to QQQ"
);
assert.ok(
  comparePage.indexOf("if (!leftTicker && !rightTicker)") < comparePage.indexOf("fetchComparisonResponse(leftTicker, rightTicker)"),
  "Compare page should branch to the empty builder before fetching a comparison"
);
assert.ok(
  comparePage.indexOf("if (!leftTicker || !rightTicker)") < comparePage.indexOf("fetchComparisonResponse(leftTicker, rightTicker)"),
  "Compare page should branch to one-side-selected builder states before fetching a comparison"
);
assert.ok(
  comparePage.indexOf('data-prd-section="selected_assets"') <
    comparePage.indexOf('data-prd-section="beginner_bottom_line"'),
  "Comparison results should show selected assets before the beginner bottom line"
);
assert.ok(
  comparePage.indexOf('data-prd-section="beginner_bottom_line"') <
    comparePage.indexOf("<StockEtfRelationshipSection"),
  "Stock-vs-ETF results should place relationship context after the beginner bottom line"
);
assert.ok(
  comparePage.indexOf("<StockEtfRelationshipSection") <
    comparePage.indexOf('data-prd-section="key_differences"'),
  "Stock-vs-ETF relationship context should stay separate before generic key differences"
);
assert.ok(
  comparePage.indexOf('data-prd-section="key_differences"') <
    comparePage.indexOf('data-prd-section="export_controls"'),
  "Comparison results should render key differences before export controls"
);
assert.ok(
  comparePage.indexOf('data-prd-section="export_controls"') <
    comparePage.indexOf('data-prd-section="suggested_comparisons"'),
  "Comparison results should render export controls before suggested comparisons"
);
assert.ok(
  comparePage.indexOf('data-prd-section="suggested_comparisons"') <
    comparePage.indexOf('data-prd-section="source_metadata"'),
  "Comparison results should render source metadata after suggested comparisons"
);
assert.ok(
  assetPage.indexOf("beginnerSections=") < assetPage.indexOf("deepDiveSections="),
  "Asset page should pass beginner sections before Deep Dive"
);
assert.ok(
  assetPage.indexOf("data-prd-section=\"beginner_summary\"") < assetPage.indexOf("data-prd-section=\"top_risks\""),
  "Supported asset page should render Beginner Summary before Top 3 Risks"
);
assert.ok(
  assetPage.indexOf("data-prd-section=\"top_risks\"") < assetPage.indexOf("data-prd-section=\"key_facts\""),
  "Supported asset page should render Top 3 Risks before Key Facts"
);
assert.ok(
  assetPage.indexOf("data-prd-section=\"key_facts\"") < assetPage.indexOf("data-prd-section=\"what_it_does_or_holds\""),
  "Supported asset page should render Key Facts before What It Does or What It Holds"
);
assert.ok(
  assetPage.indexOf("data-prd-section=\"what_it_does_or_holds\"") < assetPage.indexOf("<WeeklyNewsPanel"),
  "Supported asset page should render What It Does or What It Holds before Weekly News Focus"
);
assert.ok(
  assetPage.indexOf("data-beginner-top-risks") < assetPage.indexOf("<WeeklyNewsPanel"),
  "Beginner section should show top risks before Weekly News Focus"
);
assert.ok(
  assetPage.indexOf("<WeeklyNewsPanel") < assetPage.indexOf("<AIComprehensiveAnalysisPanel"),
  "Weekly News Focus should render before AI Comprehensive Analysis"
);
assert.ok(
  assetPage.indexOf("<AIComprehensiveAnalysisPanel") < assetPage.indexOf("deepDiveSections="),
  "AI Comprehensive Analysis should render before Deep Dive"
);
assert.ok(
  assetPage.indexOf("deepDiveSections=") < assetPage.indexOf("afterDeepDive="),
  "Deep Dive should render before Ask about this asset"
);
assert.ok(
  assetPage.indexOf("afterDeepDive=") < assetPage.indexOf("sourceTools="),
  "Ask about this asset should render before Sources"
);
assert.ok(
  assetPage.indexOf("sourceTools=") < assetPage.indexOf("footerContent="),
  "Sources should render before the educational disclaimer"
);
assert.ok(
  assetPage.indexOf("<AIComprehensiveAnalysisPanel") < assetPage.indexOf("data-beginner-educational-framing"),
  "Timely context should render before educational disclaimer"
);
assert.ok(
  assetPage.indexOf("data-beginner-stable-recent-separation=\"stable\"") <
    assetPage.indexOf("<WeeklyNewsPanel"),
  "Beginner section should keep stable facts before timely-context modules"
);
assert.ok(
  assetPage.lastIndexOf("AssetChatPanel") > assetPage.indexOf("afterDeepDive=") &&
    assetPage.lastIndexOf("AssetChatPanel") < assetPage.indexOf("sourceTools="),
  "Asset page should keep chat access after Deep Dive and before Sources"
);

const fixtures = read("lib/fixtures.ts");
for (const ticker of ["VOO", "QQQ", "AAPL"]) {
  assert.match(fixtures, new RegExp(`${ticker}: \\{`), `${ticker} fixture should exist`);
}

const assetFixturesBlock = fixtures.slice(
  fixtures.indexOf("export const assetFixtures"),
  fixtures.indexOf("export const unsupportedAssets")
);
const aaplFixture = assetFixturesBlock.slice(
  assetFixturesBlock.indexOf("AAPL: {"),
  assetFixturesBlock.indexOf("}\n};", assetFixturesBlock.indexOf("AAPL: {"))
);
for (const sectionId of [
  "business_overview",
  "products_services",
  "strengths",
  "financial_quality",
  "valuation_context",
  "top_risks",
  "recent_developments",
  "educational_suitability"
]) {
  assert.match(aaplFixture, new RegExp(`sectionId: "${sectionId}"`), `AAPL fixture should include stock section ${sectionId}`);
}
for (const marker of [
  "c_fact_aapl_products_services_detail",
  "c_fact_aapl_business_quality_strength",
  "c_fact_aapl_revenue_trend",
  "c_fact_aapl_valuation_limitation",
  "c_recent_aapl_none",
  "src_aapl_xbrl_fixture",
  "src_aapl_valuation_limitation",
  "src_aapl_recent_review",
  "business_segments",
  "financial_quality_detail_gap",
  "valuation_metrics_gap",
  "no_major_recent_development"
]) {
  assert.match(aaplFixture, new RegExp(marker), `AAPL stock fixture should include ${marker}`);
}
const vooFixture = assetFixturesBlock.slice(
  assetFixturesBlock.indexOf("VOO: {"),
  assetFixturesBlock.indexOf("  QQQ:", assetFixturesBlock.indexOf("VOO: {"))
);
const qqqFixture = assetFixturesBlock.slice(
  assetFixturesBlock.indexOf("QQQ: {"),
  assetFixturesBlock.indexOf("  AAPL:", assetFixturesBlock.indexOf("QQQ: {"))
);
assert.equal(vooFixture.includes("stockSections"), false, "VOO should not receive stock PRD section rendering");
assert.equal(qqqFixture.includes("stockSections"), false, "QQQ should not receive stock PRD section rendering");
assert.equal(aaplFixture.includes("etfSections"), false, "AAPL should not receive ETF PRD section rendering");

for (const [ticker, fixture] of [
  ["VOO", vooFixture],
  ["QQQ", qqqFixture]
]) {
  for (const sectionId of [
    "fund_objective_role",
    "holdings_exposure",
    "construction_methodology",
    "cost_trading_context",
    "etf_specific_risks",
    "similar_assets_alternatives",
    "recent_developments",
    "educational_suitability"
  ]) {
    assert.match(fixture, new RegExp(`sectionId: "${sectionId}"`), `${ticker} fixture should include ETF section ${sectionId}`);
  }
  for (const marker of [
    `c_fact_${ticker.toLowerCase()}_benchmark`,
    `c_fact_${ticker.toLowerCase()}_holdings_exposure_detail`,
    `c_fact_${ticker.toLowerCase()}_construction_methodology`,
    `c_fact_${ticker.toLowerCase()}_trading_data_limitation`,
    `c_chk_${ticker.toLowerCase()}_risks_001`,
    `c_recent_${ticker.toLowerCase()}_none`,
    `src_${ticker.toLowerCase()}_fact_sheet_fixture`,
    `src_${ticker.toLowerCase()}_holdings_fixture`,
    `src_${ticker.toLowerCase()}_prospectus_fixture`,
    `src_${ticker.toLowerCase()}_trading_limitation`,
    `src_${ticker.toLowerCase()}_recent_review`,
    "holdings_detail_gap",
    "methodology_detail_gap",
    "bid_ask_spread_gap",
    "average_volume_gap",
    "premium_discount_gap",
    "no_major_recent_development"
  ]) {
    assert.match(fixture, new RegExp(marker), `${ticker} ETF fixture should include ${marker}`);
  }
  assert.match(fixture, /top-10 weights/, `${ticker} ETF fixture should show top-10 weight gap`);
  assert.match(fixture, /sector exposure/, `${ticker} ETF fixture should show sector exposure gap`);
  assert.match(fixture, /country exposure/, `${ticker} ETF fixture should show country exposure gap`);
  assert.match(fixture, /largest-position data/, `${ticker} ETF fixture should show largest-position gap`);
}
assert.match(vooFixture, /S&P 500 Index/, "VOO ETF fixture should include its benchmark");
assert.match(vooFixture, /Broad U\.S\. large-company ETF/, "VOO ETF fixture should include its broad ETF role");
assert.match(vooFixture, /stale_fee_snapshot_gap/, "VOO ETF fixture should preserve stale fee snapshot state");
assert.match(qqqFixture, /Nasdaq-100 Index/, "QQQ ETF fixture should include its benchmark");
assert.match(qqqFixture, /Narrower growth-oriented ETF/, "QQQ ETF fixture should include its narrower growth-oriented ETF role");
assert.match(qqqFixture, /insufficient_evidence/, "QQQ ETF fixture should preserve insufficient evidence state");
assert.equal(vooFixture.includes("src_qqq_"), false, "VOO ETF fixture should not cross-bind QQQ sources");
assert.equal(qqqFixture.includes("src_voo_"), false, "QQQ ETF fixture should not cross-bind VOO sources");
assert.equal(aaplFixture.includes("src_voo_") || aaplFixture.includes("src_qqq_"), false, "AAPL fixture should not bind ETF sources");

const riskBlocks = [...fixtures.matchAll(/topRisks: \[([\s\S]*?)\],\n    facts:/g)];
assert.equal(riskBlocks.length, 3, "Each asset fixture should expose a topRisks block");
for (const block of riskBlocks) {
  const count = (block[1].match(/plainEnglishExplanation:/g) ?? []).length;
  assert.equal(count, 3, "Each asset fixture should show exactly three top risks first");
}

for (const marker of [
  "c_voo_profile",
  "c_qqq_profile",
  "c_aapl_profile",
  "weeklyNewsFocusFixtures",
  "aiComprehensiveAnalysisFixtures",
  "weekly-news-focus-v1",
  "ai-comprehensive-analysis-v1",
  "configuredMaxItemCount",
  "selectedItemCount",
  "suppressedCandidateCount",
  "evidenceLimitedState",
  "minimumWeeklyNewsItemCount",
  "weeklyNewsSelectedItemCount",
  "c_weekly_qqq_methodology",
  "c_weekly_qqq_sponsor_update",
  "src_qqq_weekly_methodology",
  "src_qqq_weekly_sponsor_update",
  "What Changed This Week",
  "Market Context",
  "Business/Fund Context",
  "Risk Context",
  "no_high_signal",
  "suppressed",
  "available",
  "freshnessState",
  "No supported stock or ETF found",
  "No facts are invented",
  "Apple Inc.",
  "Vanguard S&P 500 ETF",
  "S&P 500",
  "Invesco QQQ Trust",
  "Nasdaq-100",
  "beginner",
  "expense ratio"
]) {
  assert.match(fixtures + read("components/SearchBox.tsx") + read("lib/glossary.ts"), new RegExp(marker));
}

const frontendSource = [
  read("app/page.tsx"),
  read("app/assets/[ticker]/page.tsx"),
  read("app/compare/page.tsx"),
  read("components/AIComprehensiveAnalysisPanel.tsx"),
  read("components/AssetChatPanel.tsx"),
  read("components/AssetEtfSections.tsx"),
  read("components/AssetStockSections.tsx"),
  read("components/AssetModeLayout.tsx"),
  read("components/ComparisonSuggestions.tsx"),
  read("components/ComparisonSourceDetails.tsx"),
  read("components/ExportControls.tsx"),
  read("components/GlossaryPopover.tsx"),
  read("components/SearchBox.tsx"),
  read("components/SourceDrawer.tsx"),
  read("components/WeeklyNewsPanel.tsx"),
  read("lib/assetChat.ts"),
  read("lib/assetGlossary.ts"),
  read("lib/compare.ts"),
  read("lib/compareSuggestions.ts"),
  read("lib/exportControls.ts"),
  read("lib/fixtures.ts"),
  read("lib/glossary.ts"),
  read("lib/trustMetrics.ts")
].join("\n");

for (const forbidden of [
  "you should buy",
  "buy now",
  "definitely buy",
  "you should sell",
  "price target is",
  "allocate 20%",
  "put 50%"
]) {
  assert.equal(frontendSource.toLowerCase().includes(forbidden), false, `Frontend copy must not include ${forbidden}`);
}

assert.match(
  read("lib/assetChat.ts"),
  /resolvedFetcher\(endpoint/,
  "Chat helper should call the local relative chat endpoint through an injectable fetcher"
);
assert.match(
  read("lib/exportControls.ts"),
  /fetcher\(endpoint/,
  "Chat transcript export helper should call the local relative export endpoint through an injectable fetcher"
);
assert.equal(
  read("lib/assetChat.ts").includes("https://") ||
    read("lib/assetChat.ts").includes("http://") ||
    read("lib/assetGlossary.ts").includes("https://") ||
    read("lib/assetGlossary.ts").includes("http://") ||
    read("components/AssetChatPanel.tsx").includes("https://") ||
    read("components/AssetChatPanel.tsx").includes("http://") ||
    read("lib/exportControls.ts").includes("https://") ||
    read("lib/exportControls.ts").includes("http://") ||
    read("lib/trustMetrics.ts").includes("https://") ||
    read("lib/trustMetrics.ts").includes("http://") ||
    read("components/ExportControls.tsx").includes("https://") ||
    read("components/ExportControls.tsx").includes("http://"),
  false,
  "Frontend chat and export integration should not add live external calls"
);

const exportControlsSource = read("lib/exportControls.ts") + read("components/ExportControls.tsx");
for (const marker of [
  "/api/assets/${encodedTicker}/export?export_format=${exportFormat}",
  "/api/assets/${encodedTicker}/sources/export?export_format=${exportFormat}",
  "/api/compare/export?${params.toString()}",
  "/api/assets/${encodeTicker(ticker)}/chat/export",
  "export_format: EXPORT_FORMAT",
  "conversation_id",
  "session_contract",
  "single_turn_fallback",
  "export-validation-v1",
  "used_existing_chat_contract",
  "no_factual_evidence",
  "safe session turn records",
  "citation IDs",
  "source metadata",
  "freshness/as-of dates",
  "educational disclaimer",
  "licensing scope",
  "full source documents",
  "restricted provider payloads",
  "live external download URLs"
]) {
  assert.ok(exportControlsSource.includes(marker), `Export controls should include ${marker}`);
}

const packageJson = JSON.parse(read("package.json"));
assert.deepEqual(Object.keys(packageJson.dependencies).sort(), ["next", "react", "react-dom"]);
assert.deepEqual(
  Object.keys(packageJson.devDependencies).sort(),
  ["@types/node", "@types/react", "@types/react-dom", "typescript"]
);

const rootPackageJson = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));
assert.deepEqual(rootPackageJson.workspaces, ["apps/web"]);
for (const scriptName of ["dev", "build", "start", "typecheck"]) {
  assert.match(rootPackageJson.scripts[scriptName], /--workspace apps\/web/);
}

assert.equal(read("components/SearchBox.tsx").includes("fetch("), false, "Home search should stay local");
includes("lib/search.ts", "/api/search");
includes("lib/search.ts", "No API base URL is configured for search fetches.");
includes("lib/search.ts", "backendSearchEndpoint");
includes("lib/search.ts", "resolveLocalSearchResponse");
orderedMarkers("lib/search.ts", [
  "return await fetchBackendSearchResponse",
  "return resolveLocalSearchResponse"
], "backend search preference before fixture fallback");
includesAll("app/assets/[ticker]/page.tsx", [
  "fetchSupportedAssetOverview(fallbackAsset?.ticker ?? ticker, fallbackAsset)",
  "LimitedAssetStatePage",
  "data-asset-pending-ingestion-state",
  "data-asset-no-generated-output-for-blocked-state",
  "buildEmptyWeeklyNewsFocus",
  "buildSuppressedAnalysis"
], "dynamic backend asset page and limited-state fallback");
includes("app/assets/[ticker]/sources/page.tsx", "resolveSearchResponse");
assert.equal(
  read("components/SearchBox.tsx").includes("https://") || read("components/SearchBox.tsx").includes("http://"),
  false,
  "Home search should not add live external calls"
);
assert.equal(
  read("app/assets/[ticker]/page.tsx").includes("fetch("),
  false,
  "Asset page should delegate backend overview fetches through a narrow adapter"
);
assert.equal(read("app/assets/[ticker]/page.tsx").includes("/api/assets/"), false, "Asset page should not inline backend overview APIs");
assert.equal(
  read("lib/assetOverview.ts").includes("/api/assets/"),
  true,
  "Overview adapter should align with the backend overview contract"
);
assert.equal(read("components/AssetModeLayout.tsx").includes("fetch("), false, "Mode layout should stay fixture-backed");
assert.equal(read("components/AssetEtfSections.tsx").includes("fetch("), false, "ETF sections should stay fixture-backed");
assert.equal(read("components/AssetStockSections.tsx").includes("fetch("), false, "Stock sections should stay fixture-backed");
assert.equal(read("components/GlossaryPopover.tsx").includes("fetch("), false, "Glossary popover should stay static");
assert.equal(read("lib/glossary.ts").includes("fetch("), false, "Glossary catalog should stay static");
assert.equal(read("lib/trustMetrics.ts").includes("fetch("), false, "Trust-metrics helper should not call catalog APIs");
assert.match(
  read("lib/assetGlossary.ts"),
  /fetcher\(endpoint/,
  "Asset glossary adapter should call the backend glossary contract through an injectable fetcher"
);

const compareSource = [
  read("app/compare/page.tsx"),
  read("components/ComparisonSuggestions.tsx"),
  read("components/ComparisonSourceDetails.tsx"),
  read("lib/compare.ts"),
  read("lib/compareSuggestions.ts")
].join("\n");

assert.equal(compareSource.includes("fetcher("), true, "Compare page should call the deterministic comparison adapter route");
assert.equal(compareSource.includes("/api/compare"), true, "Compare page should align with the backend comparison contract");
assert.equal(read("app/compare/page.tsx").includes("getPrimarySource"), false, "Compare chips must not use a primary asset source fallback");
assert.equal(compareSource.includes("src_aapl_10k_fixture"), true, "Stock-vs-ETF compare source metadata should include same-pack AAPL evidence");
assert.equal(compareSource.includes("src_aapl_xbrl_fixture"), false, "Stock-vs-ETF compare source metadata should stay limited to the verified AAPL comparison source");
assert.match(compareSource, /No factual citation chips or source drawers/, "Unavailable compare states must avoid factual citation UI");

for (const marker of [
  "stock-etf-relationship-v1",
  "direct_holding",
  "sector_or_theme",
  "broad_market_context",
  "weak_relationship",
  "data-stock-etf-comparison-type",
  "data-stock-etf-stock-ticker",
  "data-stock-etf-etf-ticker",
  "data-stock-etf-relationship-state",
  "data-stock-etf-evidence-state",
  "data-relationship-badge",
  "comparison_type",
  "stock_ticker",
  "etf_ticker",
  "relationship_state",
  "evidence_boundary",
  "data-stock-etf-basket-structure",
  "single-company-vs-etf-basket",
  "Verified holding membership, partial overlap evidence",
  "Exact holding weight, top-10 concentration, sector exposure, and full overlap are unavailable",
  "c_compare_aapl_company_profile",
  "c_compare_voo_aapl_top_holding"
]) {
  assert.ok(compareSource.includes(marker), `Stock-vs-ETF comparison should include ${marker}`);
}
assert.equal(
  compareSource.includes("holding_verified"),
  false,
  "Frontend comparison rendering should not expose the old frontend-only holding_verified relationship state"
);
assert.ok(
  read("app/compare/page.tsx").includes(
    "getComparePageSuggestions(\n    comparison.left_asset.ticker,\n    comparison.right_asset.ticker,\n    comparison\n  )"
  ),
  "Compare page suggestions should use the actual fetched comparison response availability"
);

const comparisonSuggestionSource = read("components/ComparisonSuggestions.tsx") + read("lib/compareSuggestions.ts");
for (const marker of [
  "data-comparison-suggestions",
  "data-comparison-suggestion-selected-ticker",
  "data-comparison-suggestion-state",
  "data-comparison-suggestion-target",
  "data-comparison-suggestion-url",
  "data-comparison-no-local-pack",
  "local_comparison_available",
  "no_local_comparison_pack",
  "unavailable_with_fixture_examples",
  "data-comparison-suggestion-availability-source",
  "data-comparison-suggestion-example-only",
  "backend_aligned_local_contract",
  "Backend-aligned comparison available",
  "Fixture example, not the requested pair",
  "benchmark, cost, holdings breadth, and beginner role",
  "peer list, citation chips, source documents",
  "not facts about the requested pair"
]) {
  assert.ok(comparisonSuggestionSource.includes(marker), `Comparison suggestions should include ${marker}`);
}
assert.match(
  comparisonSuggestionSource,
  /localComparisonPairs = \[\s*\["VOO", "QQQ"\] as const,\s*\["AAPL", "VOO"\] as const\s*\]/,
  "Only the VOO/QQQ and AAPL/VOO local comparison pairs should be suggested"
);
assert.match(
  comparisonSuggestionSource,
  /buildSuggestion\(leftTicker, rightTicker, \{ exampleOnly: false \}\)/,
  "VOO should keep the VOO to QQQ relative comparison direction"
);
assert.match(
  comparisonSuggestionSource,
  /buildSuggestion\(rightTicker, leftTicker, \{ exampleOnly: false \}\)/,
  "QQQ should keep the QQQ to VOO relative comparison direction"
);
assert.ok(
  comparisonSuggestionSource.includes("stock-vs-ETF relationship view"),
  "Comparison suggestions should describe the stock-vs-ETF route only when a local pack exists"
);
assert.equal(comparisonSuggestionSource.includes("fetch("), false, "Comparison suggestions should stay local");
assert.equal(comparisonSuggestionSource.includes("/api/compare"), false, "Comparison suggestions should not call compare APIs");
assert.equal(
  comparisonSuggestionSource.includes("https://") || comparisonSuggestionSource.includes("http://"),
  false,
  "Comparison suggestions should not include live external URLs"
);
assert.equal(
  read("backend/comparison.py").includes("ComparisonSuggestions") ||
    read("backend/comparison.py").includes("compareSuggestions"),
  false,
  "Frontend comparison suggestions should not modify backend comparison contracts"
);

const backendMain = read("backend/main.py");
for (const marker of [
  "@app.get(\"/api/assets/{ticker}/export\"",
  "@app.get(\"/api/assets/{ticker}/sources/export\"",
  "@app.post(\"/api/compare/export\"",
  "@app.get(\"/api/compare/export\"",
  "@app.post(\"/api/assets/{ticker}/chat/export\""
]) {
  assert.ok(backendMain.includes(marker), `Backend export contract route should remain present: ${marker}`);
}

function toBool(value) {
  return ["1", "true", "yes", "on"].includes(String(value).toLowerCase());
}

function makeTimeout(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function localDurablePrereqStatus() {
  const databaseUrl = (process.env.DATABASE_URL || "").trim();
  const namespace = (process.env.LOCAL_DURABLE_OBJECT_NAMESPACE || "").trim();
  const enabled = toBool(process.env.LOCAL_DURABLE_REPOSITORIES_ENABLED);
  const blockers = [];

  if (!enabled) {
    blockers.push("Set LOCAL_DURABLE_REPOSITORIES_ENABLED=true");
  }
  if (!databaseUrl) {
    blockers.push("Set DATABASE_URL to a local durable repository DSN");
  }
  if (!namespace) {
    blockers.push("Set LOCAL_DURABLE_OBJECT_NAMESPACE");
  }

  const unsafeNamespace = [
    "://",
    "signed",
    "signature=",
    "token=",
    "secret",
    "password",
    "public/",
    "/public/",
  ];
  if (namespace && unsafeNamespace.some((marker) => namespace.toLowerCase().includes(marker))) {
    blockers.push("Use a placeholder-only non-public LOCAL_DURABLE_OBJECT_NAMESPACE");
  }

  return {
    enabled,
    databaseUrlConfigured: Boolean(databaseUrl),
    namespaceConfigured: Boolean(namespace),
    blockers,
  };
}

function normalizeSmokeBase(value, fallbackPort) {
  if (!value) {
    return `http://127.0.0.1:${fallbackPort}`;
  }
  try {
    const parsed = value.includes("://") ? new URL(value) : new URL(`http://${value}`);
    const normalizedPort = parsed.port || fallbackPort;
    return `${parsed.protocol}//${parsed.hostname}:${normalizedPort}`;
  } catch {
    return `http://127.0.0.1:${fallbackPort}`;
  }
}

const localBrowserSmokeEnabled = toBool(process.env.LEARN_TICKER_LOCAL_BROWSER_SMOKE);
const localDurableBrowserSmokeEnabled = toBool(process.env.LEARN_TICKER_LOCAL_DURABLE_SMOKE);
const localFreshDataSliceSmokeEnabled = toBool(process.env.LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE);

const localFreshDataSliceStocks = ["AAPL", "MSFT", "NVDA"];
const localFreshDataSliceEtfs = ["VOO", "SPY", "VTI", "QQQ", "XLK"];
const localFreshDataSliceBlockedTickers = ["TQQQ", "ARKK", "BND", "GLD"];
const localFreshDataSliceSupportedTickers = [
  ...localFreshDataSliceStocks,
  ...localFreshDataSliceEtfs,
];
const localFreshDataSliceRepresentativeTickers = [
  { ticker: "AAPL", assetType: "stock" },
  { ticker: "VOO", assetType: "etf" },
];

function localFreshDataSlicePrereqStatus() {
  const blockers = [];

  if (!toBool(process.env.LEARN_TICKER_LOCAL_BROWSER_SMOKE)) {
    blockers.push("Set LEARN_TICKER_LOCAL_BROWSER_SMOKE=1");
  }
  if (!(process.env.LEARN_TICKER_LOCAL_WEB_BASE || "").trim()) {
    blockers.push("Set LEARN_TICKER_LOCAL_WEB_BASE for the already-running local web service");
  }
  if (!(process.env.LEARN_TICKER_LOCAL_API_BASE || "").trim()) {
    blockers.push("Set LEARN_TICKER_LOCAL_API_BASE for the already-running local API service");
  }
  if ((process.env.DATA_POLICY_MODE || "").trim() !== "lightweight") {
    blockers.push("Set DATA_POLICY_MODE=lightweight");
  }
  if (!toBool(process.env.LIGHTWEIGHT_LIVE_FETCH_ENABLED)) {
    blockers.push("Set LIGHTWEIGHT_LIVE_FETCH_ENABLED=true");
  }
  if (!toBool(process.env.LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED)) {
    blockers.push("Set LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true");
  }
  if (!(process.env.SEC_EDGAR_USER_AGENT || "").trim()) {
    blockers.push("Set SEC_EDGAR_USER_AGENT to a placeholder contact user agent");
  }

  return blockers;
}

function reportLocalFreshDataSlicePrereqBlockers(blockers) {
  console.error("Local fresh-data slice browser/API smoke is blocked by missing prerequisites:");
  for (const blocker of blockers) {
    console.error(`- ${blocker}`);
  }
  console.error(
    "Start already-running web/API services with the listed env vars; no secret values or raw payloads are required in this output."
  );
}

const runOptionalLocalDurableSmoke = async ({ webBase, apiBase, requestWithLog }) => {
  const prereqs = localDurablePrereqStatus();
  if (prereqs.blockers.length > 0) {
    console.log("Local durable browser smoke is blocked by missing prerequisites:");
    for (const blocker of prereqs.blockers) {
      console.log(`- ${blocker}`);
    }
    console.log(
      "Start web/API with local-durable connection settings to run local-durable smoke checks."
    );
    return;
  }

  const durableSmokeFailures = [];
  try {
    const durableAssetResponse = await requestWithLog("GET", `${webBase}/assets/VOO`);
    const durableAssetBody = await durableAssetResponse.text();
    assert.equal(durableAssetResponse.status, 200, "Local durable VOO asset page should be reachable");
    assert.equal(
      durableAssetBody.includes("data-prd-section=\"beginner_summary\""),
      true,
      "Local durable VOO asset page should keep stable beginner markers"
    );
    assert.equal(
      durableAssetBody.includes("data-asset-source-list-link"),
      true,
      "Local durable VOO page should expose source-list route"
    );

    const [durableChatResponse, durableChatBody] = await requestWithLog(
      "POST",
      `${webBase}/api/assets/VOO/chat`,
      {
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: "How does this fund track risk?" }),
      }
    ).then(async (response) => [response, await response.text()]);
    assert.equal(durableChatResponse.status, 200, "Local durable VOO chat should route through API proxy");
    assert.equal(durableChatBody.includes("<!DOCTYPE html>"), false, "Local durable chat endpoint should return JSON");

    const [durableAssetExportResponse, durableAssetExportBody] = await requestWithLog(
      "GET",
      `${webBase}/api/assets/VOO/export?export_format=json`
    ).then(async (response) => [response, await response.text()]);
    assert.equal(durableAssetExportResponse.status, 200, "Local durable asset export should route through API proxy");
    assert.equal(
      durableAssetExportBody.includes("<!DOCTYPE html>"),
      false,
      "Local durable asset export should return JSON/structured payload"
    );

    const [durableSourceExportResponse, durableSourceExportBody] = await requestWithLog(
      "GET",
      `${webBase}/api/assets/VOO/sources/export?export_format=json`
    ).then(async (response) => [response, await response.text()]);
    assert.equal(durableSourceExportResponse.status, 200, "Local durable source export should route through API proxy");
    assert.equal(
      durableSourceExportBody.includes("<!DOCTYPE html>"),
      false,
      "Local durable source export should return JSON/structured payload"
    );

    const durableSourceListResponse = await requestWithLog("GET", `${webBase}/assets/VOO/sources`);
    const durableSourceListBody = await durableSourceListResponse.text();
    assert.equal(durableSourceListResponse.status, 200, "Local durable source list route should be reachable");
    assert.equal(
      durableSourceListBody.includes("supported-source-list-inspection-flow-v1"),
      true,
      "Local durable source list page should keep required markers"
    );

    const durableCompareResponse = await requestWithLog("GET", `${webBase}/compare?left=VOO&right=QQQ`);
    const durableCompareBody = await durableCompareResponse.text();
    assert.equal(durableCompareResponse.status, 200, "Local durable compare route should render");
    assert.equal(
      durableCompareBody.includes("data-compare-comparison-type=\"etf_vs_etf\""),
      true,
      "Local durable ETF-vs-ETF compare page should keep ETF comparison type"
    );
    assert.equal(
      durableCompareBody.includes("data-stock-etf-basket-structure=\"single-company-vs-etf-basket\""),
      false,
      "Local durable ETF-vs-ETF compare page should not show stock-vs-ETF relationship structure"
    );

    const durableStockEtfCompareResponse = await requestWithLog("GET", `${webBase}/compare?left=AAPL&right=VOO`);
    const durableStockEtfCompareBody = await durableStockEtfCompareResponse.text();
    assert.equal(durableStockEtfCompareResponse.status, 200, "Local durable stock-vs-ETF compare route should render");
    assert.equal(
      durableStockEtfCompareBody.includes("data-stock-etf-basket-structure=\"single-company-vs-etf-basket\""),
      true,
      "Local durable stock-vs-ETF compare page should keep relationship-badge structure"
    );
    assert.equal(
      durableStockEtfCompareBody.includes("data-stock-etf-relationship-state=\"direct_holding\""),
      true,
      "Local durable stock-vs-ETF compare page should keep the direct holding relationship state"
    );

    const durableCompareExportResponse = await requestWithLog(
      "GET",
      `${webBase}/api/compare/export?left_ticker=AAPL&right_ticker=VOO&export_format=json`
    );
    assert.equal(durableCompareExportResponse.status, 200, "Local durable stock-vs-ETF compare export should route through API path");

    const durableCorsResponse = await requestWithLog(
      "GET",
      `${apiBase}/api/search?q=VOO`,
      { headers: { Origin: webBase } }
    );
    assert.equal(durableCorsResponse.ok, true, "Local durable CORS probe should succeed");
    const durableCorsHeader = durableCorsResponse.headers.get("access-control-allow-origin") || "";
    assert.equal(
      durableCorsHeader === "*" || durableCorsHeader.includes("127.0.0.1") || durableCorsHeader.includes("localhost"),
      true,
      "Local durable API response should allow local origin"
    );

    const outOfScopeResponse = await requestWithLog("GET", `${webBase}/api/search?q=GME`);
    assert.equal(outOfScopeResponse.status, 200, "Out-of-scope search should resolve through API proxy");
    const outOfScopeBody = await outOfScopeResponse.json();
    assert.equal(outOfScopeBody.state.status, "out_of_scope", "Out-of-scope assets should remain blocked");
    assert.equal(outOfScopeBody.results[0].can_open_generated_page, false, "Blocked out-of-scope assets cannot open generated pages");
    assert.equal(outOfScopeBody.results[0].can_answer_chat, false, "Blocked out-of-scope assets cannot open chat");
    assert.equal(outOfScopeBody.results[0].can_compare, false, "Blocked out-of-scope assets cannot compare");

    const unknownResponse = await requestWithLog("GET", `${webBase}/api/search?q=ZZZZ`);
    assert.equal(unknownResponse.status, 200, "Unknown search should resolve through API proxy");
    const unknownBody = await unknownResponse.json();
    assert.equal(unknownBody.state.status, "unknown", "Unknown tickers should remain unknown");
    assert.equal(unknownBody.results[0].can_open_generated_page, false, "Unknown tickers cannot open generated pages");
    assert.equal(unknownBody.results[0].can_answer_chat, false, "Unknown tickers cannot open chat");

    const knownSearchResponse = await requestWithLog(
      "GET",
      `${webBase}/api/search?q=VOO%20vs%20QQQ`
    );
    const knownSearchBody = await knownSearchResponse.json();
    assert.equal(knownSearchResponse.status, 200, "Backend comparison search should resolve");
    assert.match(
      JSON.stringify(knownSearchBody),
      /comparison_route|\"can_compare\":true/,
      "Comparison-style local search should remain routed as comparison-capable"
    );
  } catch (error) {
    durableSmokeFailures.push(`Local durable smoke checks failed: ${error}`);
  }

  if (durableSmokeFailures.length > 0) {
    console.error("Local durable smoke blockers were not resolvable with current environment:");
    for (const item of durableSmokeFailures) {
      console.error(`- ${item}`);
    }
    process.exit(1);
  }
  console.log("Local durable browser smoke checks passed.");
  console.log(
    `Local durable smoke prereqs: DATABASE_URL=${prereqs.databaseUrlConfigured ? "set" : "missing"}, `
    + `LOCAL_DURABLE_OBJECT_NAMESPACE=${prereqs.namespaceConfigured ? "set" : "missing"}, `
    + `LOCAL_DURABLE_REPOSITORIES_ENABLED=${prereqs.enabled ? "true" : "false"}`
  );
};

if (localBrowserSmokeEnabled) {
  const webBase = normalizeSmokeBase(
    process.env.LEARN_TICKER_LOCAL_WEB_BASE || process.env.WEB_BASE,
    "3000"
  );
  const apiBase = normalizeSmokeBase(
    process.env.LEARN_TICKER_LOCAL_API_BASE || process.env.API_BASE,
    "8000"
  );
  if (localFreshDataSliceSmokeEnabled) {
    const prereqBlockers = localFreshDataSlicePrereqStatus();
    if (prereqBlockers.length > 0) {
      reportLocalFreshDataSlicePrereqBlockers(prereqBlockers);
      process.exit(1);
    }
  }
  const smokeFailures = [];
  const networkEvents = [];

  const requestWithLog = async (method, target, options = {}) => {
    const url = new URL(target);
    const headers = { ...options.headers };
    try {
      const response = await Promise.race([
        fetch(url, { method, ...options, headers }),
        makeTimeout(7000).then(() => {
          throw new Error(`Request timeout after 7000ms for ${method} ${target}`);
        }),
      ]);
      networkEvents.push({
        method,
        target: url.toString(),
        status: response.status,
        redirected: response.redirected,
      });
      return response;
    } catch (error) {
      networkEvents.push({
        method,
        target: url.toString(),
        error: String(error),
      });
      throw error;
    }
  };

  const assertPathMarkers = (html, markers, label) => {
    for (const marker of markers) {
      assert.equal(html.includes(marker), true, `${label} should include ${marker}`);
    }
  };

  const assertNoHtmlFallback = (body, label) => {
    assert.equal(body.includes("<!DOCTYPE html>"), false, `${label} should return backend JSON, not a Next HTML fallback`);
  };

  const assertNoPersonalAdviceText = (body, label) => {
    const normalized = body.toLowerCase();
    for (const forbidden of [
      "you should buy",
      "you should sell",
      "you should hold",
      "buy now",
      "sell now",
      "price target is",
      "allocate 20%",
      "put 50%"
    ]) {
      assert.equal(normalized.includes(forbidden), false, `${label} should not include advice phrase: ${forbidden}`);
    }
  };

  const requestJsonWithLog = async (method, target, options = {}, label = target) => {
    const response = await requestWithLog(method, target, options);
    const body = await response.text();
    assertNoHtmlFallback(body, label);
    const contentType = response.headers.get("content-type") || "";
    assert.match(contentType, /application\/json/i, `${label} should return JSON content`);

    let payload;
    try {
      payload = JSON.parse(body);
    } catch (error) {
      throw new Error(`${label} returned non-JSON payload: ${error}`);
    }
    return [response, payload, body];
  };

  const assertCorsAllowsLocalWebOrigin = (response, label) => {
    const corsHeader = response.headers.get("access-control-allow-origin") || "";
    assert.equal(
      corsHeader === "*" || corsHeader === webBase || corsHeader.includes("127.0.0.1") || corsHeader.includes("localhost"),
      true,
      `${label} should allow the configured local web origin`
    );
  };

  const assertAaplVooComparePayload = (payload, label) => {
    assert.equal(payload?.left_asset?.ticker, "AAPL", `${label} should keep AAPL as the left asset`);
    assert.equal(payload?.right_asset?.ticker, "VOO", `${label} should keep VOO as the right asset`);
    assert.equal(payload?.state?.status, "supported", `${label} should be supported`);
    assert.equal(payload?.comparison_type, "stock_vs_etf", `${label} should be stock-vs-ETF`);
    assert.equal(
      payload?.evidence_availability?.schema_version,
      "comparison-evidence-availability-v1",
      `${label} should include evidence availability metadata`
    );
    assert.equal(
      payload?.evidence_availability?.availability_state,
      "available",
      `${label} should be evidence-backed and available`
    );
    assert.equal(
      payload?.stock_etf_relationship?.schema_version,
      "stock-etf-relationship-v1",
      `${label} should include the stock-vs-ETF relationship schema`
    );
    assert.equal(
      payload?.stock_etf_relationship?.relationship_state,
      "direct_holding",
      `${label} should verify direct holding membership`
    );
    assert.equal(
      payload?.stock_etf_relationship?.basket_structure?.overlap_or_membership_state,
      "direct_holding",
      `${label} should keep the single-company-vs-ETF-basket direct holding state`
    );
    assert.ok(
      payload?.stock_etf_relationship?.badges?.some((badge) => badge.marker === "relationship_state" && badge.relationship_state === "direct_holding"),
      `${label} should include a direct-holding relationship badge`
    );
    assert.ok(
      payload?.stock_etf_relationship?.badges?.some((badge) => badge.marker === "evidence_boundary"),
      `${label} should include an evidence-boundary relationship badge`
    );
    assert.ok(Array.isArray(payload?.citations) && payload.citations.length > 0, `${label} should include citations`);
    assert.ok(Array.isArray(payload?.source_documents) && payload.source_documents.length > 0, `${label} should include source documents`);
    assert.ok(
      payload.source_documents.every((source) => source.source_use_policy && source.url && source.supporting_passage),
      `${label} source documents should expose source-use policy, URL, and allowed supporting passage metadata`
    );
    const sourceReferenceAssets = new Set(
      (payload?.evidence_availability?.source_references ?? []).map((sourceReference) => sourceReference.asset_ticker)
    );
    assert.equal(sourceReferenceAssets.has("AAPL"), true, `${label} should include AAPL source-reference metadata`);
    assert.equal(sourceReferenceAssets.has("VOO"), true, `${label} should include VOO source-reference metadata`);
    assert.equal(JSON.stringify(payload).includes("holding_verified"), false, `${label} should not expose the old frontend-only holding_verified state`);
  };

  const assertAaplVooExportPayload = (payload, label) => {
    assert.equal(payload?.content_type, "comparison", `${label} should be a comparison export`);
    assert.equal(payload?.export_state, "available", `${label} should be available`);
    assert.equal(payload?.left_asset?.ticker, "AAPL", `${label} should keep AAPL as the left export asset`);
    assert.equal(payload?.right_asset?.ticker, "VOO", `${label} should keep VOO as the right export asset`);
    assert.equal(payload?.metadata?.comparison_type, "stock_vs_etf", `${label} should preserve stock-vs-ETF metadata`);
    assert.equal(payload?.export_validation?.binding_scope, "same_comparison_pack", `${label} should validate same-pack bindings`);
    assert.equal(
      payload?.export_validation?.diagnostics?.same_comparison_pack_citation_bindings_only,
      true,
      `${label} should bind citations to the same comparison pack`
    );
    assert.equal(
      payload?.export_validation?.diagnostics?.same_comparison_pack_source_bindings_only,
      true,
      `${label} should bind sources to the same comparison pack`
    );
    assert.ok(Array.isArray(payload?.citations) && payload.citations.length > 0, `${label} should include citations`);
    assert.ok(Array.isArray(payload?.source_documents) && payload.source_documents.length > 0, `${label} should include sources`);
    assert.ok(
      (payload?.sections ?? []).some((section) => section.section_id === "stock_etf_relationship_context"),
      `${label} should include stock-vs-ETF relationship context`
    );
    assert.match(payload?.disclaimer ?? "", /not investment, financial, legal, or tax advice/i, `${label} should preserve the educational disclaimer`);
    assert.match(payload?.disclaimer ?? "", /not a recommendation to buy, sell, or hold/i, `${label} should preserve no-advice framing`);
    assertNoPersonalAdviceText(`${payload?.rendered_markdown ?? ""}\n${payload?.disclaimer ?? ""}`, label);
  };

  const assertAaplVooChatRedirectPayload = (payload, label) => {
    assert.equal(payload?.safety_classification, "compare_route_redirect", `${label} should be a compare-route redirect`);
    assert.equal(payload?.compare_route_suggestion?.schema_version, "chat-compare-route-v1", `${label} should include compare-route metadata`);
    assert.equal(payload?.compare_route_suggestion?.left_ticker, "AAPL", `${label} should preserve the submitted left ticker`);
    assert.equal(payload?.compare_route_suggestion?.right_ticker, "VOO", `${label} should preserve the submitted right ticker`);
    assert.equal(payload?.compare_route_suggestion?.route, "/compare?left=AAPL&right=VOO", `${label} should route to the comparison page`);
    assert.equal(
      payload?.compare_route_suggestion?.comparison_availability_state,
      "available",
      `${label} should report available comparison evidence`
    );
    assert.equal(
      payload?.compare_route_suggestion?.diagnostics?.generated_multi_asset_chat_answer,
      false,
      `${label} should not generate a multi-asset factual chat answer`
    );
    assert.deepEqual(payload?.citations ?? [], [], `${label} should not include factual citations in the redirect body`);
    assert.deepEqual(payload?.source_documents ?? [], [], `${label} should not include factual source documents in the redirect body`);
    assert.match(payload?.direct_answer ?? "", /comparison workflow/i, `${label} should direct the user to comparison workflow`);
    assertNoPersonalAdviceText(JSON.stringify(payload), label);
  };

  const assertNoRawPayloadOrSecretExposure = (payload, label) => {
    const serialized = JSON.stringify(payload);
    if (payload && "raw_payload_exposed" in payload) {
      assert.equal(payload.raw_payload_exposed, false, `${label} should not expose raw payload values`);
    }
    assert.equal(/"raw_payload_exposed"\s*:\s*true/.test(serialized), false, `${label} should not mark raw payload exposure`);
    for (const source of payload?.sources ?? []) {
      if (source && "raw_payload_exposed" in source) {
        assert.equal(source.raw_payload_exposed, false, `${label} source metadata should not expose raw payloads`);
      }
    }
    if (payload?.diagnostics && "raw_payload_exposed" in payload.diagnostics) {
      assert.equal(payload.diagnostics.raw_payload_exposed, false, `${label} diagnostics should not expose raw payloads`);
    }
    for (const forbidden of [
      "BEGIN PRIVATE KEY",
      "Bearer ",
      "Authorization",
      "OPENROUTER_API_KEY",
      "FMP_API_KEY",
      "ALPHA_VANTAGE_API_KEY",
      "FINNHUB_API_KEY",
      "TIINGO_API_KEY",
      "EODHD_API_KEY",
      "sk-",
      "xoxb-",
      "ghp_",
      "hidden prompt",
      "raw model reasoning",
      "unrestricted provider payload",
    ]) {
      assert.equal(serialized.includes(forbidden), false, `${label} should not expose ${forbidden}`);
    }
  };

  const sourceLabelsFor = (payload) => new Set((payload?.sources ?? []).map((source) => source.source_label));
  const factEvidenceStatesFor = (payload) => new Set([
    ...(payload?.facts ?? []).map((fact) => fact.evidence_state),
    ...(payload?.gaps ?? []).map((gap) => gap.evidence_state),
  ]);

  const assertFreshDataCommonPayload = (payload, ticker, label) => {
    assert.equal(payload?.schema_version, "lightweight-asset-fetch-v1", `${label} should use the lightweight fresh-data schema`);
    assert.equal(payload?.ticker, ticker, `${label} should return the requested ticker`);
    assert.equal(payload?.data_policy_mode, "lightweight", `${label} should run in lightweight data mode`);
    assert.ok(payload?.freshness?.page_last_updated_at, `${label} should include page freshness metadata`);
    assert.ok(
      payload?.freshness?.facts_as_of || payload?.freshness?.holdings_as_of || payload?.freshness?.freshness_state,
      `${label} should include as-of or freshness-state metadata`
    );
    assertNoRawPayloadOrSecretExposure(payload, label);
  };

  const assertRenderableFreshDataPayload = (payload, expectedAssetType, label) => {
    const labels = sourceLabelsFor(payload);
    const evidenceStates = factEvidenceStatesFor(payload);

    assert.equal(payload?.asset?.asset_type, expectedAssetType, `${label} should preserve ${expectedAssetType} identity`);
    assert.equal(payload?.generated_output_eligible, true, `${label} should be generated-output eligible for local MVP rendering`);
    assert.ok(["supported", "partial"].includes(payload?.fetch_state), `${label} should be renderable from supported or partial evidence`);
    assert.ok(["supported", "partial"].includes(payload?.page_render_state), `${label} should expose a renderable page state`);
    assert.ok(Array.isArray(payload?.sources) && payload.sources.length > 0, `${label} should include source metadata`);
    assert.ok(Array.isArray(payload?.citations) && payload.citations.length > 0, `${label} should include citations`);
    assert.ok(Array.isArray(payload?.facts) && payload.facts.length > 0, `${label} should include normalized facts`);
    assert.ok(
      payload.sources.every((source) => source.source_document_id && source.title && source.source_use_policy && source.freshness_state),
      `${label} source metadata should be source-drawer ready`
    );
    assert.ok(
      payload.citations.every((citation) => citation.citation_id && citation.source_document_id && citation.freshness_state),
      `${label} citation metadata should bind to source documents`
    );
    assert.ok(
      payload.citations.length > 0 || evidenceStates.has("partial") || evidenceStates.has("unavailable"),
      `${label} should include citations or explicit partial/unavailable evidence states`
    );

    if (expectedAssetType === "stock") {
      assert.equal(payload.fetch_state, "supported", `${label} should expose supported stock fresh-data state`);
      assert.equal(payload.page_render_state, "supported", `${label} should expose supported stock render state`);
      assert.equal(
        labels.has("official") || payload.sources.some((source) => source.is_official || /SEC|U\.S\. SEC/i.test(`${source.publisher} ${source.title}`)),
        true,
        `${label} should expose official SEC/source labels where the API provides them`
      );
      if ((payload?.diagnostics?.official_source_count ?? 0) > 0) {
        assert.equal(labels.has("official"), true, `${label} should label official sources as official`);
      }
    }

    if (expectedAssetType === "etf") {
      assert.equal(payload.fetch_state, "partial", `${label} should expose partial ETF fresh-data state until issuer evidence is complete`);
      assert.equal(payload.page_render_state, "partial", `${label} should expose partial ETF render state`);
      assert.equal(
        labels.has("partial") || (payload?.source_priority ?? []).includes("local_manifest_scope_signal"),
        true,
        `${label} should expose ETF manifest/scope or partial source labeling`
      );
      assert.equal(
        evidenceStates.has("partial") || evidenceStates.has("unavailable") || (payload?.gaps ?? []).length > 0,
        true,
        `${label} should show partial/unavailable labels for missing issuer evidence`
      );
      assert.ok(payload?.freshness?.holdings_as_of || payload?.freshness?.facts_as_of, `${label} should include ETF as-of metadata`);
    }

    if (labels.has("provider_derived") || (payload?.diagnostics?.provider_fallback_source_count ?? 0) > 0) {
      assert.equal(labels.has("provider_derived"), true, `${label} should label provider fallback sources as provider_derived`);
    }
  };

  const assertBlockedFreshDataPayload = (payload, ticker, label) => {
    assertFreshDataCommonPayload(payload, ticker, label);
    assert.ok(["unsupported", "out_of_scope", "unknown"].includes(payload?.fetch_state), `${label} should stay blocked`);
    assert.equal(payload?.generated_output_eligible, false, `${label} should remain generated-output ineligible`);
    assert.equal(payload?.sources?.length ?? 0, 0, `${label} should not expose source documents`);
    assert.equal(payload?.citations?.length ?? 0, 0, `${label} should not expose citations`);
    assert.equal(payload?.facts?.length ?? 0, 0, `${label} should not expose facts`);
    assert.equal(payload?.diagnostics?.blocked_generated_output, true, `${label} should report generated output blocked`);
  };

  const assertSearchContractPayload = (payload, ticker, expectedAssetType, label) => {
    const serialized = JSON.stringify(payload);
    assert.match(serialized, new RegExp(`"${ticker}"`), `${label} should include ${ticker}`);
    const firstResult = (payload?.results ?? []).find((result) => result.ticker === ticker) || (payload?.results ?? [])[0];
    assert.ok(firstResult, `${label} should include a search result`);
    assert.equal(firstResult.ticker, ticker, `${label} should return the requested ticker result`);
    assert.equal(firstResult.asset_type, expectedAssetType, `${label} should preserve ${expectedAssetType} identity`);
    assert.equal(firstResult.can_open_generated_page, true, `${label} should open a generated local-MVP page`);
    assert.equal(firstResult.can_answer_chat, true, `${label} should allow asset-bounded chat for supported rows`);
    assert.equal(firstResult.can_compare, true, `${label} should allow supported comparison entry`);
  };

  const assertBlockedSearchPayload = (payload, ticker, label) => {
    const firstResult = (payload?.results ?? []).find((result) => result.ticker === ticker) || (payload?.results ?? [])[0];
    assert.ok(firstResult, `${label} should include a blocked search result`);
    assert.equal(firstResult.ticker, ticker, `${label} should return the requested blocked ticker`);
    assert.equal(firstResult.can_open_generated_page, false, `${label} should not open generated pages`);
    assert.equal(firstResult.can_answer_chat, false, `${label} should not allow generated chat answers`);
    assert.equal(firstResult.can_compare, false, `${label} should not allow generated comparisons`);
    assert.ok(
      ["unsupported", "out_of_scope", "unknown", "unavailable", "pending_review"].includes(payload?.state?.status),
      `${label} should expose a non-supported search state`
    );
  };

  const assertOverviewContractPayload = (payload, ticker, expectedAssetType, label) => {
    assert.equal(payload?.asset?.ticker, ticker, `${label} should preserve ticker identity`);
    assert.equal(payload?.asset?.asset_type, expectedAssetType, `${label} should preserve ${expectedAssetType} identity`);
    assert.equal(payload?.state?.status, "supported", `${label} should use the supported overview contract state`);
    assert.ok(payload?.freshness?.page_last_updated_at, `${label} should expose freshness metadata`);
    assert.ok(Array.isArray(payload?.citations) && payload.citations.length > 0, `${label} should include citation chips`);
    assert.ok(Array.isArray(payload?.source_documents) && payload.source_documents.length > 0, `${label} should include source documents`);
    assert.ok(Array.isArray(payload?.top_risks) && payload.top_risks.length === 3, `${label} should preserve exactly three top risks`);
    assert.ok(Array.isArray(payload?.sections) && payload.sections.length > 0, `${label} should include detail sections`);
  };

  const assertDetailsContractPayload = (payload, ticker, expectedAssetType, label) => {
    assert.equal(payload?.asset?.ticker, ticker, `${label} should preserve ticker identity`);
    assert.equal(payload?.asset?.asset_type, expectedAssetType, `${label} should preserve ${expectedAssetType} identity`);
    assert.equal(payload?.state?.status, "supported", `${label} should use the supported details contract state`);
    assert.ok(payload?.freshness?.page_last_updated_at, `${label} should expose details freshness metadata`);
    assert.ok(payload?.facts && Object.keys(payload.facts).length > 0, `${label} should include detail facts`);
    assert.ok(Array.isArray(payload?.citations) && payload.citations.length > 0, `${label} should include details citations`);
  };

  const assertSourcesContractPayload = (payload, ticker, label) => {
    assert.equal(payload?.schema_version, "asset-source-drawer-v1", `${label} should use the source drawer schema`);
    assert.equal(payload?.asset?.ticker, ticker, `${label} should preserve ticker identity`);
    assert.equal(payload?.drawer_state, "available", `${label} should have available source drawer metadata`);
    assert.ok(Array.isArray(payload?.sources) && payload.sources.length > 0, `${label} should include source records`);
    assert.ok(Array.isArray(payload?.source_groups) && payload.source_groups.length > 0, `${label} should include source groups`);
    assert.ok(Array.isArray(payload?.citation_bindings) && payload.citation_bindings.length > 0, `${label} should include citation bindings`);
    assert.ok(Array.isArray(payload?.related_claims) && payload.related_claims.length > 0, `${label} should include related claims`);
  };

  const runOptionalFreshDataSliceSmoke = async () => {
    const prereqBlockers = localFreshDataSlicePrereqStatus();
    if (prereqBlockers.length > 0) {
      reportLocalFreshDataSlicePrereqBlockers(prereqBlockers);
      process.exit(1);
    }

    const sliceSmokeFailures = [];

    for (const ticker of localFreshDataSliceSupportedTickers) {
      const expectedAssetType = localFreshDataSliceStocks.includes(ticker) ? "stock" : "etf";
      try {
        const [proxyResponse, proxyPayload] = await requestJsonWithLog(
          "GET",
          `${webBase}/api/assets/${encodeURIComponent(ticker)}/fresh-data`,
          {},
          `${ticker} frontend proxy fresh-data API`
        );
        assert.equal(proxyResponse.status, 200, `${ticker} frontend proxy fresh-data API should return 200`);
        assertFreshDataCommonPayload(proxyPayload, ticker, `${ticker} frontend proxy fresh-data API`);
        assertRenderableFreshDataPayload(proxyPayload, expectedAssetType, `${ticker} frontend proxy fresh-data API`);

        const [directResponse, directPayload] = await requestJsonWithLog(
          "GET",
          `${apiBase}/api/assets/${encodeURIComponent(ticker)}/fresh-data`,
          { headers: { Origin: webBase } },
          `${ticker} direct FastAPI fresh-data API`
        );
        assert.equal(directResponse.status, 200, `${ticker} direct FastAPI fresh-data API should return 200`);
        assertCorsAllowsLocalWebOrigin(directResponse, `${ticker} direct FastAPI fresh-data API`);
        assertFreshDataCommonPayload(directPayload, ticker, `${ticker} direct FastAPI fresh-data API`);
        assertRenderableFreshDataPayload(directPayload, expectedAssetType, `${ticker} direct FastAPI fresh-data API`);
      } catch (error) {
        sliceSmokeFailures.push(`${ticker} supported fresh-data probe failed: ${error}`);
      }
    }

    for (const ticker of localFreshDataSliceBlockedTickers) {
      try {
        const [proxyResponse, proxyPayload] = await requestJsonWithLog(
          "GET",
          `${webBase}/api/assets/${encodeURIComponent(ticker)}/fresh-data`,
          {},
          `${ticker} frontend proxy blocked fresh-data API`
        );
        assert.equal(proxyResponse.status, 200, `${ticker} frontend proxy blocked fresh-data API should return 200`);
        assertBlockedFreshDataPayload(proxyPayload, ticker, `${ticker} frontend proxy blocked fresh-data API`);

        const [directResponse, directPayload] = await requestJsonWithLog(
          "GET",
          `${apiBase}/api/assets/${encodeURIComponent(ticker)}/fresh-data`,
          { headers: { Origin: webBase } },
          `${ticker} direct FastAPI blocked fresh-data API`
        );
        assert.equal(directResponse.status, 200, `${ticker} direct FastAPI blocked fresh-data API should return 200`);
        assertCorsAllowsLocalWebOrigin(directResponse, `${ticker} direct FastAPI blocked fresh-data API`);
        assertBlockedFreshDataPayload(directPayload, ticker, `${ticker} direct FastAPI blocked fresh-data API`);

        const [searchResponse, searchPayload] = await requestJsonWithLog(
          "GET",
          `${webBase}/api/search?q=${encodeURIComponent(ticker)}`,
          {},
          `${ticker} frontend proxy blocked search API`
        );
        assert.equal(searchResponse.status, 200, `${ticker} frontend proxy blocked search API should return 200`);
        assertBlockedSearchPayload(searchPayload, ticker, `${ticker} frontend proxy blocked search API`);
        assertNoRawPayloadOrSecretExposure(searchPayload, `${ticker} frontend proxy blocked search API`);
      } catch (error) {
        sliceSmokeFailures.push(`${ticker} blocked regression probe failed: ${error}`);
      }
    }

    for (const { ticker, assetType } of localFreshDataSliceRepresentativeTickers) {
      try {
        const [searchResponse, searchPayload] = await requestJsonWithLog(
          "GET",
          `${webBase}/api/search?q=${encodeURIComponent(ticker)}`,
          {},
          `${ticker} frontend proxy search contract`
        );
        assert.equal(searchResponse.status, 200, `${ticker} frontend proxy search contract should return 200`);
        assertSearchContractPayload(searchPayload, ticker, assetType, `${ticker} frontend proxy search contract`);
        assertNoRawPayloadOrSecretExposure(searchPayload, `${ticker} frontend proxy search contract`);

        const [overviewResponse, overviewPayload] = await requestJsonWithLog(
          "GET",
          `${webBase}/api/assets/${encodeURIComponent(ticker)}/overview`,
          {},
          `${ticker} frontend proxy overview contract`
        );
        assert.equal(overviewResponse.status, 200, `${ticker} frontend proxy overview contract should return 200`);
        assertOverviewContractPayload(overviewPayload, ticker, assetType, `${ticker} frontend proxy overview contract`);
        assertNoRawPayloadOrSecretExposure(overviewPayload, `${ticker} frontend proxy overview contract`);

        const [detailsResponse, detailsPayload] = await requestJsonWithLog(
          "GET",
          `${webBase}/api/assets/${encodeURIComponent(ticker)}/details`,
          {},
          `${ticker} frontend proxy details contract`
        );
        assert.equal(detailsResponse.status, 200, `${ticker} frontend proxy details contract should return 200`);
        assertDetailsContractPayload(detailsPayload, ticker, assetType, `${ticker} frontend proxy details contract`);
        assertNoRawPayloadOrSecretExposure(detailsPayload, `${ticker} frontend proxy details contract`);

        const [sourcesResponse, sourcesPayload] = await requestJsonWithLog(
          "GET",
          `${webBase}/api/assets/${encodeURIComponent(ticker)}/sources`,
          {},
          `${ticker} frontend proxy sources contract`
        );
        assert.equal(sourcesResponse.status, 200, `${ticker} frontend proxy sources contract should return 200`);
        assertSourcesContractPayload(sourcesPayload, ticker, `${ticker} frontend proxy sources contract`);
        assertNoRawPayloadOrSecretExposure(sourcesPayload, `${ticker} frontend proxy sources contract`);
      } catch (error) {
        sliceSmokeFailures.push(`${ticker} representative running-service contract probe failed: ${error}`);
      }
    }

    if (sliceSmokeFailures.length > 0) {
      console.error("Local fresh-data slice browser/API smoke detected blockers:");
      for (const item of sliceSmokeFailures) {
        console.error(`- ${item}`);
      }
      process.exit(1);
    }

    console.log(
      `Local fresh-data slice browser/API smoke passed for supported=${localFreshDataSliceSupportedTickers.join(",")} `
      + `and blocked=${localFreshDataSliceBlockedTickers.join(",")}.`
    );
  };

  const runOptionalBrowserSmoke = async () => {
    try {
      const [homeResponse, homeBody] = await requestWithLog("GET", `${webBase}/`).then(async (response) => [
        response,
        await response.text(),
      ]);
      assert.equal(homeResponse.ok, true, `Home page should be reachable via ${webBase}`);
      assert.equal(homeBody.includes("data-home-workflow-baseline"), true, "Home page should render the single-asset home markers");
      assert.equal(homeBody.includes("data-home-primary-workflow=\"single-supported-stock-or-etf-search\""), true, "Home page should keep one primary single-asset search action");
      assert.equal(
        homeBody.includes("name=\"left\"") || homeBody.includes("name=\"right\""),
        false,
        "Home page should not render two comparison-builder inputs"
      );
    } catch (error) {
      smokeFailures.push(`Home page smoke request failed: ${error}`);
    }

    try {
      const [searchViaFrontend, searchViaFrontendBody] = await requestWithLog(
        "GET",
        `${webBase}/api/search?q=VOO`
      ).then(async (response) => [response, await response.text()]);
      assert.equal(searchViaFrontend.status, 200, `Frontend-backed search should resolve on ${webBase}/api/search`);
      assert.match(searchViaFrontendBody, /comparison_route|search_results|can_compare/, `Search response should expose backend search routing fields`);

      const searchViaBackend = await requestWithLog(
        "GET",
        `${apiBase}/api/search?q=VOO%20vs%20QQQ`
      );
      assert.equal(searchViaBackend.status, 200, `Backend search should resolve VOO vs QQQ query`);
      const backendSearchBody = await searchViaBackend.text();
      assert.match(backendSearchBody, /\"can_compare\"|comparison_route/, "Backend comparison-route behavior should be present for VOO vs QQQ");
    } catch (error) {
      smokeFailures.push(`Search/comparison route smoke failed: ${error}`);
    }

    try {
      const assetResponse = await requestWithLog("GET", `${webBase}/assets/VOO`);
      const assetBody = await assetResponse.text();
      assert.equal(assetResponse.status, 200, "VOO asset page should be reachable from local web server");
      assertPathMarkers(
        assetBody,
        [
          "data-prd-section=\"beginner_summary\"",
          "data-prd-section=\"top_risks\"",
          "data-asset-source-list-link",
          "data-source-drawer-mobile-presentation=\"bottom-sheet\"",
          "data-glossary-desktop-interaction=\"hover-click-focus-escape\"",
          "data-glossary-mobile-presentation=\"bottom-sheet\"",
        ],
        "VOO asset page"
      );

      const [chatResponse, chatBody] = await requestWithLog(
        "POST",
        `${webBase}/api/assets/VOO/chat`,
        {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: "What does VOO track?" }),
        }
      ).then(async (response) => [response, await response.text()]);
      assert.equal(chatResponse.status, 200, "VOO chat endpoint should stay API-backed and not Next 404");
      assert.equal(chatBody.includes("<!DOCTYPE html>"), false, "VOO chat should return JSON response");
      assert.equal(chatBody.length > 0, true, "VOO chat should return response payload");

      const [assetExportResponse, assetExportBody] = await requestWithLog(
        "GET",
        `${webBase}/api/assets/VOO/export?export_format=markdown`
      ).then(async (response) => [response, await response.text()]);
      assert.equal(assetExportResponse.status, 200, "VOO export endpoint should stay API-backed and not Next 404");
      assert.equal(assetExportBody.includes("<!DOCTYPE html>"), false, "VOO asset export should return JSON/structured payload");

      const [sourceExportResponse, sourceExportBody] = await requestWithLog(
        "GET",
        `${webBase}/api/assets/VOO/sources/export?export_format=json`
      ).then(async (response) => [response, await response.text()]);
      assert.equal(sourceExportResponse.status, 200, "VOO source-list export endpoint should stay API-backed and not Next 404");
      assert.equal(sourceExportBody.includes("<!DOCTYPE html>"), false, "VOO source-list export should return JSON/structured payload");

      const sourcePageResponse = await requestWithLog("GET", `${webBase}/assets/VOO/sources`);
      const sourcePageBody = await sourcePageResponse.text();
      assert.equal(sourcePageResponse.status, 200, "VOO source list page should be reachable from local web server");
      assertPathMarkers(
        sourcePageBody,
        [
          "supported-source-list-inspection-flow-v1",
          "data-source-list-state",
          "data-source-list-source-use-policies",
          "data-source-list-source-count",
        ],
        "VOO source-list page"
      );
    } catch (error) {
      smokeFailures.push(`API-backed asset/chat/export/source smoke failed: ${error}`);
    }

    try {
      const compareResponse = await requestWithLog("GET", `${webBase}/compare?left=VOO&right=QQQ`);
      const compareBody = await compareResponse.text();
      assert.equal(compareResponse.status, 200, "Compare route should render for VOO vs QQQ");
      assertPathMarkers(
        compareBody,
        [
          "separate-comparison-workflow-v1",
          "data-prd-compare-result-layout=\"source-backed-deterministic-pack\"",
          "data-compare-comparison-type=\"etf_vs_etf\"",
        ],
        "ETF-vs-ETF compare route page"
      );
      assert.equal(
        compareBody.includes("data-stock-etf-basket-structure=\"single-company-vs-etf-basket\""),
        false,
        "ETF-vs-ETF compare route should not render stock-vs-ETF basket structure"
      );

      const stockEtfCompareResponse = await requestWithLog("GET", `${webBase}/compare?left=AAPL&right=VOO`);
      const stockEtfCompareBody = await stockEtfCompareResponse.text();
      assert.equal(stockEtfCompareResponse.status, 200, "Compare route should render for AAPL vs VOO");
      assertPathMarkers(
        stockEtfCompareBody,
        [
          "data-compare-availability-state=\"available\"",
          "data-compare-comparison-type=\"stock_vs_etf\"",
          "data-stock-etf-relationship-schema=\"stock-etf-relationship-v1\"",
          "data-stock-etf-relationship-state=\"direct_holding\"",
          "data-stock-etf-overlap-state=\"direct_holding\"",
          "data-relationship-badge=\"relationship_state\"",
          "data-relationship-badge=\"evidence_boundary\"",
          "data-stock-etf-basket-structure=\"single-company-vs-etf-basket\"",
          "data-comparison-source-document-id",
          "data-comparison-source-use-policy",
          "data-comparison-source-asset=\"AAPL\"",
          "data-comparison-source-asset=\"VOO\"",
          "data-governed-golden-citation-binding",
        ],
        "Stock-vs-ETF compare route page"
      );
      assert.equal(
        stockEtfCompareBody.includes("data-compare-unavailable-state") ||
          stockEtfCompareBody.includes("No local comparison pack") ||
          stockEtfCompareBody.includes("Comparison evidence unavailable"),
        false,
        "AAPL vs VOO page should not render unsupported, unavailable, or no-local-pack copy"
      );

      const [stockEtfCompareApiResponse, stockEtfCompareApiPayload] = await requestJsonWithLog(
        "POST",
        `${webBase}/api/compare`,
        {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ left_ticker: "AAPL", right_ticker: "VOO" }),
        },
        "AAPL vs VOO frontend proxy compare API"
      );
      assert.equal(stockEtfCompareApiResponse.status, 200, "AAPL vs VOO compare API should route through the frontend proxy");
      assertAaplVooComparePayload(stockEtfCompareApiPayload, "AAPL vs VOO frontend proxy compare API");

      const compareCorsPreflightResponse = await requestWithLog(
        "OPTIONS",
        `${apiBase}/api/compare`,
        {
          headers: {
            Origin: webBase,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
          },
        }
      );
      assert.ok(
        [200, 204].includes(compareCorsPreflightResponse.status),
        "AAPL vs VOO compare CORS preflight should be allowed for the local web origin"
      );
      assertCorsAllowsLocalWebOrigin(compareCorsPreflightResponse, "AAPL vs VOO compare CORS preflight");

      const [stockEtfCompareDirectApiResponse, stockEtfCompareDirectApiPayload] = await requestJsonWithLog(
        "POST",
        `${apiBase}/api/compare`,
        {
          headers: { "Content-Type": "application/json", Origin: webBase },
          body: JSON.stringify({ left_ticker: "AAPL", right_ticker: "VOO" }),
        },
        "AAPL vs VOO direct FastAPI compare API"
      );
      assert.equal(stockEtfCompareDirectApiResponse.status, 200, "AAPL vs VOO direct compare API should return JSON");
      assertCorsAllowsLocalWebOrigin(stockEtfCompareDirectApiResponse, "AAPL vs VOO direct FastAPI compare API");
      assertAaplVooComparePayload(stockEtfCompareDirectApiPayload, "AAPL vs VOO direct FastAPI compare API");

      const [stockEtfExportResponse, stockEtfExportPayload] = await requestJsonWithLog(
        "GET",
        `${webBase}/api/compare/export?left_ticker=AAPL&right_ticker=VOO&export_format=json`,
        {},
        "AAPL vs VOO comparison export API"
      );
      assert.equal(stockEtfExportResponse.status, 200, "AAPL vs VOO comparison export should route through API path");
      assertAaplVooExportPayload(stockEtfExportPayload, "AAPL vs VOO comparison export API");

      const [chatCompareResponse, chatComparePayload] = await requestJsonWithLog(
        "POST",
        `${webBase}/api/assets/VOO/chat`,
        {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: "AAPL vs VOO" }),
        },
        "AAPL vs VOO asset-chat compare redirect"
      );
      assert.equal(chatCompareResponse.status, 200, "AAPL vs VOO chat compare redirect should route through API path");
      assertAaplVooChatRedirectPayload(chatComparePayload, "AAPL vs VOO asset-chat compare redirect");

      const compareExportResponse = await requestWithLog(
        "GET",
        `${webBase}/api/compare/export?left_ticker=VOO&right_ticker=QQQ&export_format=markdown`
      );
      assert.equal(compareExportResponse.status, 200, "Compare export endpoint should be reachable through API path");

      const corsProbeResponse = await requestWithLog(
        "GET",
        `${apiBase}/api/search?q=VOO`,
        { headers: { Origin: webBase } }
      );
      assert.equal(corsProbeResponse.ok, true, "Backend CORS probe should succeed");
      const corsHeader = corsProbeResponse.headers.get("access-control-allow-origin") || "";
      assert.equal(
        corsHeader === "*" || corsHeader.includes("127.0.0.1") || corsHeader.includes("localhost"),
        true,
        "Backend CORS headers should allow local web origin"
      );
    } catch (error) {
      smokeFailures.push(`Compare/API route smoke failed: ${error}`);
    }

    if (smokeFailures.length > 0) {
      console.error("Local browser smoke detected API/path failures:");
      for (const item of smokeFailures) {
        console.error(`- ${item}`);
      }
      console.error("Network events:");
      for (const event of networkEvents) {
        console.error(JSON.stringify(event));
      }
      process.exit(1);
    }
    console.log(`Local browser smoke checks passed for web=${webBase}, api=${apiBase}.`);
    console.log(`Local browser smoke recorded ${networkEvents.length} network events.`);

    if (localFreshDataSliceSmokeEnabled) {
      await runOptionalFreshDataSliceSmoke();
    } else {
      console.log(
        "Local fresh-data slice browser/API smoke is skipped by default. Set LEARN_TICKER_LOCAL_BROWSER_SMOKE=1 and LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1 with lightweight local-service env vars to run it."
      );
    }

    if (localDurableBrowserSmokeEnabled) {
      await runOptionalLocalDurableSmoke({ webBase, apiBase, requestWithLog });
    }
  };

  await runOptionalBrowserSmoke();
} else {
  console.log(
    "Local browser smoke is skipped by default. Set LEARN_TICKER_LOCAL_BROWSER_SMOKE=1 and optionally LEARN_TICKER_LOCAL_WEB_BASE/API_BASE to run localhost-only browser/API checks. Add LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1 for the T-144 fresh-data MVP slice checks."
  );
}

console.log("Frontend smoke checks passed.");
