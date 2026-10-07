// Static contracts for retained financial reference components. Desktop workflows use Playwright.
import assert from "node:assert/strict";

import { readFileSync, existsSync } from "node:fs";

import { join } from "node:path";

const root = process.cwd();

const webRoot = join(root, "apps/desktop");

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
    `${path} should exist in apps/desktop or the repo root`
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
  "components/AIComprehensiveAnalysisPanel.tsx",
  "components/AssetChatPanel.tsx",
  "components/AssetEtfSections.tsx",
  "components/AssetStockSections.tsx",
  "components/EconomicIndicatorsPanel.tsx",
  "components/StructuredOverviewDisplays.tsx",
  "components/AssetModeLayout.tsx",
  "components/CitationChip.tsx",
  "components/ComparisonSuggestions.tsx",
  "components/ComparisonSourceDetails.tsx",
  "components/CompactCitationSourcesClient.tsx",
  "components/ExportControls.tsx",
  "components/SourceDrawer.tsx",
  "components/FreshnessLabel.tsx",
  "components/GenerationStateNote.tsx",
  "components/GlossaryPopover.tsx",
  "components/InlineGlossaryText.tsx",
  "components/MarketAIComprehensiveAnalysisPanel.tsx",
  "components/MarketNewsPanel.tsx",
  "components/WeeklyNewsPanel.tsx",
  "lib/assetDetails.ts",
  "lib/apiEndpoints.ts",
  "lib/assetChat.ts",
  "lib/assetGlossary.ts",
  "lib/assetOverview.ts",
  "lib/assetWeeklyNews.ts",
  "lib/compare.ts",
  "lib/compareSuggestions.ts",
  "lib/economicIndicators.ts",
  "lib/exportControls.ts",
  "lib/fixtures.ts",
  "lib/glossary.ts",
  "lib/marketNews.ts",
  "lib/trustMetrics.ts",
  "lib/sourceDrawer.ts",
  "lib/sourceDisplay.ts",
  "styles/globals.css"
].forEach(exists);

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

includesAll("components/WeeklyNewsPanel.tsx", [
  "data-weekly-news-configured-max",
  "data-weekly-news-selected-count",
  "data-weekly-news-scope=\"ticker\"",
  "data-weekly-news-evidence-limited-state",
  "data-weekly-news-empty-behavior",
  "data-weekly-news-limited-verified-set",
  "Weekly News Focus:",
  "No major Weekly News Focus items found",
  "Source quality",
  "Source-use policy"
], "Weekly News Focus evidence-limited markers");

includesAll("components/AIComprehensiveAnalysisPanel.tsx", [
  "data-ai-analysis-scope=\"ticker\"",
  "data-ai-analysis-minimum-weekly-news-items",
  "data-ai-analysis-weekly-news-selected-count",
  "data-ai-analysis-validation-reason-codes",
  "data-ai-analysis-threshold-state",
  "AI Comprehensive Analysis:",
  "What Changed This Week",
  "Market Context",
  "Business/Fund Context",
  "Risk Context",
  "fabricated analysis"
], "AI Comprehensive Analysis threshold and separation markers");

includesAll("components/MarketNewsPanel.tsx", [
  "Market News Focus",
  "data-market-news-focus",
  "data-market-news-configured-max",
  "data-market-news-selected-count",
  "data-market-news-reusable-across-tickers",
  "data-market-news-topic-bucket",
  "Source-use policy",
  "Supporting sources"
], "Market News Focus reusable market context markers");

includesAll("components/EconomicIndicatorsPanel.tsx", [
  "Economic Indicators",
  "data-economic-indicators",
  "data-economic-indicators-schema",
  "data-economic-indicators-region",
  "data-economic-indicators-official-count",
  "data-economic-indicators-market-reference-count",
  "data-economic-indicators-analysis-source",
  "Official historical actual",
  "Market reference"
], "Economic Indicators common context markers");

includesAll("components/MarketAIComprehensiveAnalysisPanel.tsx", [
  "AI Comprehensive Analysis: Market News Focus",
  "data-market-ai-comprehensive-analysis",
  "data-market-ai-analysis-minimum-market-news-items",
  "data-market-ai-analysis-selected-topic-buckets",
  "Macro & Policy",
  "Equity Market Drivers",
  "AI / Technology / Semiconductors",
  "Geopolitical & Energy Risks",
  "Credit / Liquidity / Sentiment",
  "Scenario Lens",
  "Practical Watchpoints"
], "Market AI Comprehensive Analysis thematic markers");

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
  "data-chat-session-browser-persistence=\"none\"",
  "Array.from(new Set(response.uncertainty))"
], "asset chat helper, safety, accountless, and no-live-call markers");

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

includes("components/AssetHeader.tsx", "data-asset-header-layout");

includes("components/AssetHeader.tsx", "data-prd-section");

includes("components/AssetHeader.tsx", "CompactCitationSources");

assert.equal(
  read("components/AssetHeader.tsx").includes("data-asset-header-actions"),
  false,
  "Asset hero should not repeat page tool actions"
);

assert.equal(
  read("components/AssetHeader.tsx").includes("data-asset-header-action"),
  false,
  "Asset hero should not render individual action links"
);

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

includesAll("components/SectionStateNote.tsx", [
  "data-asset-inline-section-state",
  "data-asset-section-state-placement=\"inside-panel\"",
  "data-asset-section-failure-reason",
  "data-weekly-news-fetch-failure-notice",
  "timeout_or_aborted",
  "partial_backend_contract"
], "inline section-state notes render inside owning panels");

includesAll("components/CitationChip.tsx", [
  "citationLabelFromSource",
  "return \"SEC\"",
  "return \"Issuer\"",
  "return \"Provider\"",
  "return \"Fixture\""
], "citation chips prefer source metadata labels before id-prefix labels");

includesAll("components/GenerationStateNote.tsx", [
  "data-generation-state",
  "data-generation-label",
  "data-generation-used-fallback",
  "live_generated",
  "deterministic_fallback",
  "live_timeout_fallback",
  "suppressed_insufficient_evidence",
  "backend_error"
], "generation-state markers render from the inline generation provenance component");

includesAll("components/EconomicIndicatorsPanel.tsx", [
  "data-economic-indicators-inline-source-state",
  "Live local official and market-reference indicator evidence",
  "Deterministic fixture indicators are shown"
], "economic indicator source state is inline in the single Economic Indicators section");

assert.equal(
  read("components/EconomicIndicatorsPanel.tsx").includes("Period / as of"),
  false,
  "Economic Indicators should move period/retrieved details into the source icon instead of a standalone column"
);

includesAll("components/CompactCitationSources.tsx", [
  "metadataRows",
  "uniqueBySourceDocumentId",
  "summaryLabel"
], "source icons carry compact evidence metadata rows without inflating source counts");

includesAll("components/CompactCitationSourcesClient.tsx", [
  "data-source-icon-metadata-rows",
  "data-compact-citation-metadata-count",
  "data-compact-citation-dismissible=\"outside-click-escape-close-button\"",
  "document.addEventListener(\"pointerdown\"",
  "event.key === \"Escape\"",
  "data-compact-citation-close-control=\"button\"",
  "onClick={() => setPopoverOpen(false)}",
  "data-citation-count"
], "source popovers can close from outside click, Escape, close button, and source links");

assert.equal(
  read("components/CompactCitationSources.tsx").includes("sourceCount + visibleMetadataRows.length"),
  false,
  "Source badge counts should count unique cited sources only, not metadata rows"
);

assert.equal(
  read("styles/globals.css").includes(".metadata-row span"),
  false,
  "Hero metadata chip CSS should not apply broad span styling to nested source popover content"
);

includesAll("styles/globals.css", [
  ".metadata-row > span",
  ".source-icon-disclosure-labeled summary",
  ".compact-citation-close",
  "max-height: calc(100vh - 128px)",
  "overflow-y: auto"
], "mobile-safe source popover and direct-child metadata chip styling");

includesAll("components/AssetHeader.tsx", [
  "summaryLabel=\"Sources\"",
  "showCount={false}"
], "hero source affordance is a labeled control instead of a bare count chip");

assert.equal(
  read("components/AssetDataDashboard.tsx").includes("Dashboard evidence details"),
  false,
  "Asset Data Dashboard should not repeat a section-level source icon when chart/table controls exist"
);

assert.equal(
  read("components/AssetDataDashboard.tsx").includes("${table.title} evidence details"),
  false,
  "Dashboard tables with row-level source icons should not repeat heading-level source icons"
);

includesAll("components/WeeklyNewsPanel.tsx", [
  "sourcePublisherLabel",
  "Provider/API",
  "itemHeadingTitle"
], "Weekly News headings and popovers expose publisher plus provider/API context");

includesAll("components/MarketNewsPanel.tsx", [
  "sourcePublisherLabel",
  "Provider/API"
], "Market News popovers expose publisher plus provider/API context");

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

includes("lib/marketNews.ts", "/api/market-news");

includes("lib/marketNews.ts", "No API base URL is configured for market-news fetches.");

includes("lib/marketNews.ts", "market-news-response-v1");

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

includes("components/AssetModeLayout.tsx", "data-helper-rail-tools=\"ask,compare,export,sources\"");

includes("components/AssetModeLayout.tsx", "data-prd-section=\"deep_dive\"");

includes("components/AssetModeLayout.tsx", "data-prd-section=\"sources\"");

includes("components/AssetModeLayout.tsx", "Deep Dive");

assert.equal(read("components/AssetModeLayout.tsx").includes("Beginner Mode"), false, "Asset layout should not expose a visible Beginner Mode wrapper");

assert.equal(read("components/AssetModeLayout.tsx").includes("Deep-Dive Mode"), false, "Asset layout should not expose a visible Deep-Dive Mode wrapper");

includes("components/WeeklyNewsPanel.tsx", "Weekly News Focus");

includes("components/WeeklyNewsPanel.tsx", "Weekly News Focus:");

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

includes("components/WeeklyNewsPanel.tsx", "Source quality");

includes("components/WeeklyNewsPanel.tsx", "Source-use policy");

includes("components/WeeklyNewsPanel.tsx", "No major Weekly News Focus items found");

includes("components/AIComprehensiveAnalysisPanel.tsx", "AI Comprehensive Analysis");

includes("components/AIComprehensiveAnalysisPanel.tsx", "AI Comprehensive Analysis:");

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

includes("components/MarketNewsPanel.tsx", "Market News Focus");

includes("components/MarketNewsPanel.tsx", "data-market-news-state");

includes("components/MarketNewsPanel.tsx", "data-market-news-item-count");

includes("components/MarketAIComprehensiveAnalysisPanel.tsx", "AI Comprehensive Analysis: Market News Focus");

includes("components/MarketAIComprehensiveAnalysisPanel.tsx", "data-market-ai-analysis-section-order");

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

includes("components/AssetStockSections.tsx", "data-dashboard-duplicate-sections-filtered");

includes("components/AssetStockSections.tsx", "provider_metric_tables");

includes("components/AssetStockSections.tsx", "data-deep-dive-table-chart-policy=\"exclude_table_or_chart_sections\"");

includes("components/AssetStockSections.tsx", "data-deep-dive-source-status-sections=\"products_services,strengths,market_reference,evidence_limits\"");

includes("components/AssetStockSections.tsx", "business_overview,financial_quality,valuation_context,price_chart");

includes("components/AssetStockSections.tsx", "data-stock-stable-recent-separation");

includes("components/AssetStockSections.tsx", "data-stock-top-risk-count");

includes("components/AssetStockSections.tsx", "InlineGlossaryText");

includes("components/AssetStockSections.tsx", "glossaryMatches");

includes("components/AssetStockSections.tsx", "No citation chip is shown because this item is an explicit evidence gap");

includes("components/AssetEtfSections.tsx", "data-etf-prd-sections");

includes("components/AssetEtfSections.tsx", "data-etf-section-id");

includes("components/AssetEtfSections.tsx", "data-shared-prd-section-shell");

includes("components/AssetEtfSections.tsx", "data-dashboard-duplicate-sections-filtered");

includes("components/AssetEtfSections.tsx", "fund_objective_role,holdings_exposure,sector_weightings,performance,price_chart");

includes("components/AssetEtfSections.tsx", "data-deep-dive-table-chart-policy=\"exclude_table_or_chart_sections\"");

includes("components/AssetEtfSections.tsx", "data-deep-dive-source-status-sections=\"construction_methodology,similar_assets_alternatives,evidence_limits\"");

includes("components/AssetEtfSections.tsx", "fund_objective_role,holdings_exposure,sector_weightings,performance,price_chart,cost_trading_context");

includes("components/AssetEtfSections.tsx", "data-etf-stable-recent-separation");

includes("components/AssetEtfSections.tsx", "data-etf-top-risk-count");

includes("components/AssetEtfSections.tsx", "InlineGlossaryText");

includes("components/AssetEtfSections.tsx", "glossaryMatches");

includes("components/AssetEtfSections.tsx", "No citation chip is shown because this ETF item is an explicit evidence gap");

includes("components/AssetDataDashboard.tsx", "data-asset-data-dashboard");

includes("components/AssetDataDashboard.tsx", "data-dashboard-holdings-table");

includes("components/AssetDataDashboard.tsx", "data-dashboard-sector-weightings");

includes("components/AssetDataDashboard.tsx", "data-dashboard-performance-section");

includes("components/AssetDataDashboard.tsx", "data-quote-stat-grid");

includes("components/AssetDataDashboard.tsx", "data-dashboard-glossary-label");

includes("components/AssetDataDashboard.tsx", "hasAssetDataDashboard");

includes("components/AssetDataDashboard.tsx", "dashboardTableSubtitle");

includes("components/AssetDataDashboard.tsx", "SourceDisclosure");

includes("components/AssetDataDashboard.tsx", "data-dashboard-source-icon");

includes("components/AssetDataDashboard.tsx", "data-dashboard-collapsible-table");

includes("styles/globals.css", "repeat\\(auto-fit, minmax\\(260px, 1fr\\)\\)");

includes("styles/globals.css", "overflow: visible");

includes("styles/globals.css", ".source-icon-disclosure");

includes("styles/globals.css", "position: static");

includes("components/AssetPriceRangeChart.tsx", "data-chart-range-tabs");

includes("components/AssetPriceRangeChart.tsx", "data-active-chart-range");

includes("components/AssetPriceRangeChart.tsx", "data-chart-volume-bars");

includes("lib/assetChart.ts", "/api/assets/");

includes("lib/assetChart.ts", "/chart\\?range=");

includes("lib/assetChart.ts", "defaultChartRange: ChartRange = \"6mo\"");

includes("components/StructuredOverviewDisplays.tsx", "data-overview-table");

includes("components/StructuredOverviewDisplays.tsx", "data-holdings-table");

includes("components/StructuredOverviewDisplays.tsx", "data-sector-weightings");

includes("components/StructuredOverviewDisplays.tsx", "data-performance-section");

includes("components/StructuredOverviewDisplays.tsx", "data-price-chart-panel");

includes("components/StructuredOverviewDisplays.tsx", "price-chart-svg");

includes("lib/assetOverview.ts", "table: section.table");

includes("lib/assetOverview.ts", "chart: section.chart");

includes("lib/fixtures.ts", "OverviewTable");

includes("lib/fixtures.ts", "OverviewChart");

includes("lib/compare.ts", "metric_groups");

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

includes("components/CitationChip.tsx", "Open source drawer");

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

includes("styles/globals.css", "max-height: none");

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
  "evidence_limits",
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
    "evidence_limits",
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
  "Single-company risk",
  "Business and competition risk",
  "Financial and valuation risk",
  "Concentration risk",
  "Tracking risk",
  "issuer_facts_are_point_in_time",
  "provider_reference_limits",
  "provider_fallback_limits",
  "weeklyNewsFocusFixtures",
  "aiComprehensiveAnalysisFixtures",
  "marketNewsFocusFixture",
  "marketAIComprehensiveAnalysisFixture",
  "weekly-news-focus-v1",
  "ai-comprehensive-analysis-v1",
  "market-news-focus-v1",
  "market-ai-comprehensive-analysis-v1",
  "configuredMaxItemCount",
  "selectedItemCount",
  "suppressedCandidateCount",
  "evidenceLimitedState",
  "minimumWeeklyNewsItemCount",
  "weeklyNewsSelectedItemCount",
  "minimumMarketNewsItemCount",
  "marketNewsSelectedItemCount",
  "c_market_news_macro_policy",
  "src_market_news_macro_policy",
  "c_weekly_qqq_methodology",
  "c_weekly_qqq_sponsor_update",
  "src_qqq_weekly_methodology",
  "src_qqq_weekly_sponsor_update",
  "What Changed This Week",
  "Market Context",
  "Business/Fund Context",
  "Risk Context",
  "Macro & Policy",
  "Scenario Lens",
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

assert.deepEqual(Object.keys(packageJson.dependencies).sort(), ["@tauri-apps/api", "react", "react-dom"]);

assert.deepEqual(
  Object.keys(packageJson.devDependencies).sort(),
  ["@playwright/test", "@tauri-apps/cli", "@types/node", "@types/react", "@types/react-dom", "@typescript-eslint/parser", "@vitejs/plugin-react", "eslint", "typescript", "vite", "vitest"]
);

const rootPackageJson = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));

assert.deepEqual(rootPackageJson.workspaces, ["apps/desktop"]);

for (const scriptName of ["dev", "build", "test", "typecheck"]) {
  assert.match(rootPackageJson.scripts[scriptName], /--workspace apps\/desktop/);
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

assert.equal(
  read("components/SearchBox.tsx").includes("https://") || read("components/SearchBox.tsx").includes("http://"),
  false,
  "Home search should not add live external calls"
);

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
  "Local example, not the requested pair",
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
console.log("Financial reference component contracts passed.");
