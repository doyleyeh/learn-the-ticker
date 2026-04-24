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
  "components/WeeklyNewsPanel.tsx",
  "lib/assetDetails.ts",
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

includes("app/page.tsx", "SearchBox");
includes("app/page.tsx", "Understand a stock or ETF in plain English");
includes("app/page.tsx", "Search a U.S. stock or non-leveraged U.S. equity ETF");
includes("app/page.tsx", "single-asset-search");
includes("app/page.tsx", "separate-comparison");
includes("app/page.tsx", "VOO vs QQQ");
includes("app/page.tsx", "/compare");
includes("app/assets/[ticker]/page.tsx", "Stable facts");
includes("app/assets/[ticker]/page.tsx", "Stale and unknown treatment");
includes("app/assets/[ticker]/page.tsx", "AssetModeLayout");
includes("app/assets/[ticker]/page.tsx", "WeeklyNewsPanel");
includes("app/assets/[ticker]/page.tsx", "AIComprehensiveAnalysisPanel");
includes("app/assets/[ticker]/page.tsx", "data-beginner-primary-claim");
includes("app/assets/[ticker]/page.tsx", "data-beginner-top-risk-count");
includes("app/assets/[ticker]/page.tsx", "data-beginner-stable-recent-separation");
includes("app/assets/[ticker]/page.tsx", "data-beginner-educational-framing");
includes("app/assets/[ticker]/page.tsx", "SourceDrawer");
includes("app/assets/[ticker]/page.tsx", "GlossaryPopover");
includes("app/assets/[ticker]/page.tsx", "data-beginner-glossary-area");
includes("app/assets/[ticker]/page.tsx", "data-glossary-asset-ticker");
includes("app/assets/[ticker]/page.tsx", "data-glossary-asset-type");
includes("app/assets/[ticker]/page.tsx", "data-glossary-no-generated-context");
includes("app/assets/[ticker]/page.tsx", "fetchSupportedAssetGlossaryContexts");
includes("app/assets/[ticker]/page.tsx", "data-asset-glossary-rendering");
includes("app/assets/[ticker]/page.tsx", "data-glossary-backend-context");
includes("app/assets/[ticker]/page.tsx", "data-glossary-generic-education");
includes("app/assets/[ticker]/page.tsx", "beginnerGlossaryGroupsByAssetType");
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
includes("app/assets/[ticker]/page.tsx", "rendered source document IDs");
includes("app/assets/[ticker]/page.tsx", "getAssetComparisonSuggestions");
includes("app/assets/[ticker]/page.tsx", "ComparisonSuggestions");
includes("app/assets/[ticker]/page.tsx", "AssetEtfSections");
includes("app/assets/[ticker]/page.tsx", "AssetStockSections");
includes("app/assets/[ticker]/page.tsx", "hasEtfPrdSections");
includes("app/assets/[ticker]/page.tsx", "hasStockPrdSections");
includes("app/assets/[ticker]/sources/page.tsx", "SourceDrawer");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-state");
includes("app/assets/[ticker]/sources/page.tsx", "data-source-list-rendering");
includes("app/assets/[ticker]/sources/page.tsx", "fetchSupportedSourceDrawerResponse");
includes("app/assets/[ticker]/sources/page.tsx", "sourceListUnavailableMessage");
includes("app/assets/[ticker]/sources/page.tsx", "No source metadata is rendered because this ticker is recognized as unsupported");
includes("app/assets/[ticker]/sources/page.tsx", "No source metadata is rendered because this ticker is outside the Top-500 manifest-backed support scope");
includes("app/assets/[ticker]/sources/page.tsx", "source-list view");
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
includes("components/AssetChatPanel.tsx", "business-model");
includes("components/AssetChatPanel.tsx", "holdings-exposure");
includes("components/AssetChatPanel.tsx", "top-risk");
includes("components/AssetChatPanel.tsx", "recent-developments");
includes("components/AssetChatPanel.tsx", "advice-boundary");
includes("components/AssetChatPanel.tsx", "business model work");
includes("components/AssetChatPanel.tsx", "fund exposure");
includes("components/AssetChatPanel.tsx", "without a personal recommendation");
includes("components/AssetModeLayout.tsx", "data-asset-mode-layout");
includes("components/AssetModeLayout.tsx", "data-asset-mode-region");
includes("components/AssetModeLayout.tsx", "data-beginner-mode-region");
includes("components/AssetModeLayout.tsx", "data-deep-dive-mode-region");
includes("components/AssetModeLayout.tsx", "Beginner Mode");
includes("components/AssetModeLayout.tsx", "Deep-Dive Mode");
includes("components/WeeklyNewsPanel.tsx", "Weekly News Focus");
includes("components/WeeklyNewsPanel.tsx", "data-weekly-news-state");
includes("components/WeeklyNewsPanel.tsx", "data-weekly-news-item-count");
includes("components/WeeklyNewsPanel.tsx", "data-beginner-weekly-news-focus");
includes("components/WeeklyNewsPanel.tsx", "data-beginner-recent-developments");
includes("components/WeeklyNewsPanel.tsx", "Source quality:");
includes("components/WeeklyNewsPanel.tsx", "Source-use policy:");
includes("components/WeeklyNewsPanel.tsx", "No major Weekly News Focus items found");
includes("components/AIComprehensiveAnalysisPanel.tsx", "AI Comprehensive Analysis");
includes("components/AIComprehensiveAnalysisPanel.tsx", "data-ai-analysis-state");
includes("components/AIComprehensiveAnalysisPanel.tsx", "data-ai-analysis-available");
includes("components/AIComprehensiveAnalysisPanel.tsx", "What Changed This Week");
includes("components/AIComprehensiveAnalysisPanel.tsx", "Market Context");
includes("components/AIComprehensiveAnalysisPanel.tsx", "Business/Fund Context");
includes("components/AIComprehensiveAnalysisPanel.tsx", "Risk Context");
includes("components/AIComprehensiveAnalysisPanel.tsx", "data-ai-analysis-section-order");
includes("components/AIComprehensiveAnalysisPanel.tsx", "fabricated analysis");
includes("components/ExportControls.tsx", "data-export-controls");
includes("components/ExportControls.tsx", "data-export-relative-api");
includes("components/ExportControls.tsx", "data-export-no-live-external");
includes("components/ExportControls.tsx", "data-export-control");
includes("components/ExportControls.tsx", "data-export-href");
includes("components/ExportControls.tsx", "data-export-contract-rendering");
includes("components/ExportControls.tsx", "data-export-contract-source");
includes("components/ExportControls.tsx", "data-export-contract-marker");
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
includes("components/ExportControls.tsx", "data-export-copy-markdown");
includes("components/ExportControls.tsx", "data-export-rendered-markdown");
includes("components/ComparisonSuggestions.tsx", "data-comparison-suggestions");
includes("components/ComparisonSuggestions.tsx", "data-comparison-suggestion-selected-ticker");
includes("components/ComparisonSuggestions.tsx", "data-comparison-suggestion-state");
includes("components/ComparisonSuggestions.tsx", "data-comparison-suggestion-target");
includes("components/ComparisonSuggestions.tsx", "data-comparison-suggestion-url");
includes("components/ComparisonSuggestions.tsx", "data-comparison-no-local-pack");
includes("components/ComparisonSuggestions.tsx", "data-comparison-requested-availability-state");
includes("lib/compareSuggestions.ts", "localComparisonPairs");
includes("lib/compareSuggestions.ts", "VOO");
includes("lib/compareSuggestions.ts", "QQQ");
includes("lib/compareSuggestions.ts", "buildSuggestion\\(rightTicker, leftTicker\\)");
includes("lib/compareSuggestions.ts", "No local source-backed comparison pack");
includes("lib/compareSuggestions.ts", "not facts about the requested pair");
includes("lib/compareSuggestions.ts", "requestedAvailabilityState");
includes("components/AssetStockSections.tsx", "data-stock-prd-sections");
includes("components/AssetStockSections.tsx", "data-stock-section-id");
includes("components/AssetStockSections.tsx", "data-stock-stable-recent-separation");
includes("components/AssetStockSections.tsx", "data-stock-top-risk-count");
includes("components/AssetStockSections.tsx", "No citation chip is shown because this item is an explicit evidence gap");
includes("components/AssetEtfSections.tsx", "data-etf-prd-sections");
includes("components/AssetEtfSections.tsx", "data-etf-section-id");
includes("components/AssetEtfSections.tsx", "data-etf-stable-recent-separation");
includes("components/AssetEtfSections.tsx", "data-etf-top-risk-count");
includes("components/AssetEtfSections.tsx", "No citation chip is shown because this ETF item is an explicit evidence gap");
includes("lib/assetChat.ts", "/api/assets/");
includes("lib/assetChat.ts", "/chat");
includes("lib/assetChat.ts", "conversation_id");
includes("lib/assetChat.ts", "chat-session-contract-v1");
includes("lib/assetChat.ts", "export_available");
includes("lib/exportControls.ts", "/api/assets/");
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
includes("components/SourceDrawer.tsx", "Published or as of");
includes("components/SourceDrawer.tsx", "Related claim context");
includes("components/SourceDrawer.tsx", "Supporting passage");
includes("components/SourceDrawer.tsx", "Official source");
includes("components/SourceDrawer.tsx", "URL");
includes("components/CitationChip.tsx", "data-source-document-id");
includes("components/SearchBox.tsx", "data-search-state");
includes("components/SearchBox.tsx", "resolveLocalSearchResponse");
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
includes("components/SearchBox.tsx", "data-search-comparison-result");
includes("components/SearchBox.tsx", "data-search-special-autocomplete-result");
includes("components/SearchBox.tsx", "data-search-comparison-route");
includes("components/SearchBox.tsx", "data-search-open-comparison-route");
includes("components/SearchBox.tsx", "Pending ingestion");
includes("components/SearchBox.tsx", "Out of scope");
includes("components/SearchBox.tsx", "No supported stock or ETF found for");
includes("components/SearchBox.tsx", "No generated asset page, grounded chat, or comparison is available today");
includes("components/SearchBox.tsx", "No facts are invented for this ticker or name");
includes("lib/search.ts", "comparison_route");
includes("lib/search.ts", "/compare\\?left=");
includes("lib/search.ts", "VOO, QQQ, AAPL, NVDA, and SOXX");
includes("lib/search.ts", "We found this ticker, but it is not supported in v1.");
includes("lib/search.ts", "Learn the Ticker currently supports U.S.-listed common stocks and non-leveraged U.S.-listed equity ETFs.");
includes("components/FreshnessLabel.tsx", "data-freshness-state");
includes("components/GlossaryPopover.tsx", "data-glossary-term");
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
assert.ok(
  assetPage.indexOf("beginnerMode=") < assetPage.indexOf("deepDiveMode="),
  "Asset page should pass Beginner Mode before Deep-Dive Mode"
);
assert.ok(
  assetPage.indexOf("data-beginner-top-risks") < assetPage.indexOf("<WeeklyNewsPanel"),
  "Beginner Mode should show top risks before Weekly News Focus"
);
assert.ok(
  assetPage.indexOf("<WeeklyNewsPanel") < assetPage.indexOf("<AIComprehensiveAnalysisPanel"),
  "Weekly News Focus should render before AI Comprehensive Analysis"
);
assert.ok(
  assetPage.indexOf("<AIComprehensiveAnalysisPanel") < assetPage.indexOf("data-beginner-educational-framing"),
  "Timely context should render before educational suitability"
);
assert.ok(
  assetPage.indexOf("data-beginner-stable-recent-separation=\"stable\"") <
    assetPage.indexOf("<WeeklyNewsPanel"),
  "Beginner Mode should keep stable facts before timely-context modules"
);
assert.ok(
  assetPage.lastIndexOf("AssetChatPanel") > assetPage.indexOf("data-beginner-educational-framing"),
  "Beginner Mode should keep chat access in the beginner flow"
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
assert.equal(read("components/SearchBox.tsx").includes("/api/search"), false, "Home search should not call /api/search");
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
assert.equal(compareSource.includes("src_aapl"), false, "Compare source metadata must not include AAPL sources");
assert.match(compareSource, /No factual citation chips or source drawers/, "Unavailable compare states must avoid factual citation UI");

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
  "benchmark, cost, holdings breadth, and beginner role",
  "peer list, citation chips, source documents",
  "not facts about the requested pair"
]) {
  assert.ok(comparisonSuggestionSource.includes(marker), `Comparison suggestions should include ${marker}`);
}
assert.match(
  comparisonSuggestionSource,
  /localComparisonPairs = \[\["VOO", "QQQ"\] as const\]/,
  "Only the VOO/QQQ local comparison pair should be suggested"
);
assert.match(
  comparisonSuggestionSource,
  /buildSuggestion\(leftTicker, rightTicker\)/,
  "VOO should keep the VOO to QQQ relative comparison direction"
);
assert.match(
  comparisonSuggestionSource,
  /buildSuggestion\(rightTicker, leftTicker\)/,
  "QQQ should keep the QQQ to VOO relative comparison direction"
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

console.log("Frontend smoke checks passed.");
