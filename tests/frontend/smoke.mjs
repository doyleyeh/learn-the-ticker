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
  "components/CitationChip.tsx",
  "components/ComparisonSourceDetails.tsx",
  "components/SourceDrawer.tsx",
  "components/FreshnessLabel.tsx",
  "components/GlossaryPopover.tsx",
  "lib/assetChat.ts",
  "lib/compare.ts",
  "lib/fixtures.ts",
  "styles/globals.css"
].forEach(exists);

includes("app/page.tsx", "SearchBox");
includes("app/page.tsx", "unsupported");
includes("app/assets/[ticker]/page.tsx", "Stable facts");
includes("app/assets/[ticker]/page.tsx", "Recent developments");
includes("app/assets/[ticker]/page.tsx", "Stale and unknown treatment");
includes("app/assets/[ticker]/page.tsx", "SourceDrawer");
includes("app/assets/[ticker]/page.tsx", "GlossaryPopover");
includes("app/assets/[ticker]/page.tsx", "AssetChatPanel");
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
includes("components/CitationChip.tsx", "data-source-document-id");
includes("components/SearchBox.tsx", "data-search-state");
includes("components/FreshnessLabel.tsx", "data-freshness-state");

const fixtures = read("lib/fixtures.ts");
for (const ticker of ["VOO", "QQQ", "AAPL"]) {
  assert.match(fixtures, new RegExp(`${ticker}: \\{`), `${ticker} fixture should exist`);
}

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
  read("components/ComparisonSourceDetails.tsx"),
  read("components/SearchBox.tsx"),
  read("lib/assetChat.ts"),
  read("lib/compare.ts"),
  read("lib/fixtures.ts")
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
