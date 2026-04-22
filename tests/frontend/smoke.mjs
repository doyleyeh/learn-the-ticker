import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();

function read(path) {
  return readFileSync(join(root, path), "utf8");
}

function exists(path) {
  assert.equal(existsSync(join(root, path)), true, `${path} should exist`);
}

function includes(path, marker) {
  assert.match(read(path), new RegExp(marker), `${path} should include ${marker}`);
}

[
  "app/page.tsx",
  "app/assets/[ticker]/page.tsx",
  "app/compare/page.tsx",
  "components/AssetChatPanel.tsx",
  "components/AssetEtfSections.tsx",
  "components/AssetStockSections.tsx",
  "components/AssetModeLayout.tsx",
  "components/CitationChip.tsx",
  "components/ComparisonSourceDetails.tsx",
  "components/SourceDrawer.tsx",
  "components/FreshnessLabel.tsx",
  "components/GlossaryPopover.tsx",
  "lib/assetChat.ts",
  "lib/compare.ts",
  "lib/fixtures.ts",
  "lib/glossary.ts",
  "styles/globals.css"
].forEach(exists);

includes("app/page.tsx", "SearchBox");
includes("app/page.tsx", "unsupported");
includes("app/assets/[ticker]/page.tsx", "Stable facts");
includes("app/assets/[ticker]/page.tsx", "Recent developments");
includes("app/assets/[ticker]/page.tsx", "Stale and unknown treatment");
includes("app/assets/[ticker]/page.tsx", "AssetModeLayout");
includes("app/assets/[ticker]/page.tsx", "data-beginner-primary-claim");
includes("app/assets/[ticker]/page.tsx", "data-beginner-top-risk-count");
includes("app/assets/[ticker]/page.tsx", "data-beginner-stable-recent-separation");
includes("app/assets/[ticker]/page.tsx", "data-beginner-recent-developments");
includes("app/assets/[ticker]/page.tsx", "data-beginner-educational-framing");
includes("app/assets/[ticker]/page.tsx", "SourceDrawer");
includes("app/assets/[ticker]/page.tsx", "GlossaryPopover");
includes("app/assets/[ticker]/page.tsx", "data-beginner-glossary-area");
includes("app/assets/[ticker]/page.tsx", "data-glossary-asset-ticker");
includes("app/assets/[ticker]/page.tsx", "data-glossary-asset-type");
includes("app/assets/[ticker]/page.tsx", "data-glossary-no-generated-context");
includes("app/assets/[ticker]/page.tsx", "data-glossary-generic-education");
includes("app/assets/[ticker]/page.tsx", "beginnerGlossaryGroupsByAssetType");
includes("app/assets/[ticker]/page.tsx", "AssetChatPanel");
includes("app/assets/[ticker]/page.tsx", "AssetEtfSections");
includes("app/assets/[ticker]/page.tsx", "AssetStockSections");
includes("app/assets/[ticker]/page.tsx", "hasEtfPrdSections");
includes("app/assets/[ticker]/page.tsx", "hasStockPrdSections");
includes("app/compare/page.tsx", "Bottom line for beginners");
includes("app/compare/page.tsx", "ComparisonSourceDetails");
includes("app/compare/page.tsx", "getComparisonCitationMetadata");
includes("components/AssetChatPanel.tsx", "Ask about this asset");
includes("components/AssetChatPanel.tsx", "data-chat-state");
includes("components/AssetChatPanel.tsx", "data-chat-citation-id");
includes("components/AssetChatPanel.tsx", "Chat source metadata");
includes("components/AssetChatPanel.tsx", "Educational redirect");
includes("components/AssetChatPanel.tsx", "Unsupported or unknown asset");
includes("components/AssetChatPanel.tsx", "Insufficient evidence");
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
includes("lib/compare.ts", "sourceDocuments");
includes("lib/compare.ts", "c_fact_voo_benchmark");
includes("lib/compare.ts", "c_fact_qqq_benchmark");
includes("lib/compare.ts", "src_voo_fact_sheet_fixture");
includes("lib/compare.ts", "src_qqq_fact_sheet_fixture");
includes("components/ComparisonSourceDetails.tsx", "Comparison source metadata");
includes("components/ComparisonSourceDetails.tsx", "data-comparison-source-document-id");
includes("components/ComparisonSourceDetails.tsx", "Official source");
includes("components/ComparisonSourceDetails.tsx", "Published or as of");
includes("components/ComparisonSourceDetails.tsx", "Related comparison claims");
includes("components/ComparisonSourceDetails.tsx", "supportingPassage");
includes("components/SourceDrawer.tsx", "data-source-document-id");
includes("components/SourceDrawer.tsx", "Published or as of");
includes("components/SourceDrawer.tsx", "Related claim context");
includes("components/SourceDrawer.tsx", "Supporting passage");
includes("components/SourceDrawer.tsx", "Official source");
includes("components/SourceDrawer.tsx", "URL");
includes("components/CitationChip.tsx", "data-source-document-id");
includes("components/SearchBox.tsx", "data-search-state");
includes("components/SearchBox.tsx", "resolveLocalFixtureSearch");
includes("components/SearchBox.tsx", "data-search-supported-result");
includes("components/SearchBox.tsx", "data-search-multi-result");
includes("components/SearchBox.tsx", "data-search-unsupported-result");
includes("components/SearchBox.tsx", "data-search-unknown-result");
includes("components/SearchBox.tsx", "data-search-result-link");
includes("components/SearchBox.tsx", "No facts are invented for this ticker or name");
includes("components/FreshnessLabel.tsx", "data-freshness-state");
includes("components/GlossaryPopover.tsx", "data-glossary-term");
includes("components/GlossaryPopover.tsx", "data-glossary-category");
includes("components/GlossaryPopover.tsx", "data-glossary-definition");
includes("components/GlossaryPopover.tsx", "data-glossary-why-it-matters");
includes("components/GlossaryPopover.tsx", "data-glossary-beginner-mistake");
includes("components/GlossaryPopover.tsx", "data-glossary-available");
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
  assetPage.indexOf("data-beginner-top-risks") < assetPage.indexOf("data-beginner-recent-developments"),
  "Beginner Mode should show top risks before recent developments"
);
assert.ok(
  assetPage.indexOf("data-beginner-stable-recent-separation=\"stable\"") <
    assetPage.indexOf("data-beginner-stable-recent-separation=\"recent\""),
  "Beginner Mode should keep stable facts before recent developments"
);
assert.ok(
  assetPage.lastIndexOf("AssetChatPanel") > assetPage.indexOf("data-beginner-educational-framing"),
  "Beginner Mode should keep chat access in the beginner flow"
);

const fixtures = read("lib/fixtures.ts");
for (const ticker of ["VOO", "QQQ", "AAPL"]) {
  assert.match(fixtures, new RegExp(`${ticker}: \\{`), `${ticker} fixture should exist`);
}

const aaplFixture = fixtures.slice(fixtures.indexOf("AAPL: {"), fixtures.indexOf("}\n};", fixtures.indexOf("AAPL: {")));
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
const vooFixture = fixtures.slice(fixtures.indexOf("VOO: {"), fixtures.indexOf("  QQQ:", fixtures.indexOf("VOO: {")));
const qqqFixture = fixtures.slice(fixtures.indexOf("QQQ: {"), fixtures.indexOf("  AAPL:", fixtures.indexOf("QQQ: {")));
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
  "freshnessState",
  "Unknown in the local skeleton data",
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
  read("components/AssetChatPanel.tsx"),
  read("components/AssetEtfSections.tsx"),
  read("components/AssetStockSections.tsx"),
  read("components/AssetModeLayout.tsx"),
  read("components/ComparisonSourceDetails.tsx"),
  read("components/GlossaryPopover.tsx"),
  read("components/SearchBox.tsx"),
  read("components/SourceDrawer.tsx"),
  read("lib/assetChat.ts"),
  read("lib/compare.ts"),
  read("lib/fixtures.ts"),
  read("lib/glossary.ts")
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
  /fetcher\(endpoint/,
  "Chat helper should call the local relative chat endpoint through an injectable fetcher"
);
assert.equal(
  read("lib/assetChat.ts").includes("https://") ||
    read("lib/assetChat.ts").includes("http://") ||
    read("components/AssetChatPanel.tsx").includes("https://") ||
    read("components/AssetChatPanel.tsx").includes("http://"),
  false,
  "Frontend chat integration should not add live external calls"
);

assert.equal(read("components/SearchBox.tsx").includes("fetch("), false, "Home search should stay local");
assert.equal(read("components/SearchBox.tsx").includes("/api/search"), false, "Home search should not call /api/search");
assert.equal(
  read("components/SearchBox.tsx").includes("https://") || read("components/SearchBox.tsx").includes("http://"),
  false,
  "Home search should not add live external calls"
);
assert.equal(read("app/assets/[ticker]/page.tsx").includes("fetch("), false, "Asset page should stay fixture-backed");
assert.equal(read("app/assets/[ticker]/page.tsx").includes("/api/assets/"), false, "Asset page should not call backend overview APIs");
assert.equal(read("components/AssetModeLayout.tsx").includes("fetch("), false, "Mode layout should stay fixture-backed");
assert.equal(read("components/AssetEtfSections.tsx").includes("fetch("), false, "ETF sections should stay fixture-backed");
assert.equal(read("components/AssetStockSections.tsx").includes("fetch("), false, "Stock sections should stay fixture-backed");
assert.equal(read("components/GlossaryPopover.tsx").includes("fetch("), false, "Glossary popover should stay static");
assert.equal(read("lib/glossary.ts").includes("fetch("), false, "Glossary catalog should stay static");

const compareSource = [
  read("app/compare/page.tsx"),
  read("components/ComparisonSourceDetails.tsx"),
  read("lib/compare.ts")
].join("\n");

assert.equal(compareSource.includes("fetch("), false, "Compare page should not make live external calls");
assert.equal(compareSource.includes("/api/compare"), false, "Compare page should stay fixture-backed");
assert.equal(read("app/compare/page.tsx").includes("getPrimarySource"), false, "Compare chips must not use a primary asset source fallback");
assert.equal(compareSource.includes("src_aapl"), false, "Compare source metadata must not include AAPL sources");
assert.match(compareSource, /No factual citation chips or source drawers/, "Unavailable compare states must avoid factual citation UI");

console.log("Frontend smoke checks passed.");
