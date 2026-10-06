import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { Comparisons, ComparisonView } from "./Comparisons";
import type { ComparisonResult, ComparisonCell } from "./contracts";
import { comparisonRoute, routeFromHash, sourceRoute } from "./routes";

const cell: ComparisonCell = { state: "available", value: "9007199254740993.123456789", unit: "USD",
  start: "2025-01-01", end: "2025-12-31", source_ids: ["original&source"], evidence_ids: ["observation"] };
const result: ComparisonResult = { id: "stored-result", created_at: "2026-10-06T00:00:00Z", method: "saved-evidence-alignment-v2",
  left: { bundle_id: "old page", asset: { id: "left", name: "Left example", symbol: "LEFT", asset_type: "stock" }, saved_at: "2026-03-01T00:00:00Z", state: "stale", completion: "complete", fingerprint: "a".repeat(64) },
  right: { bundle_id: "other page", asset: { id: "right", name: "Right example", symbol: "RIGHT", asset_type: "fund" }, saved_at: "2026-02-01T00:00:00Z", state: "partial", completion: "section_checkpoint", fingerprint: "b".repeat(64) },
  rows: [{ id: "financial:Revenues:annual", label: "Revenue", alignment: "missing_evidence", left: cell, right: { state: "not_applicable" } }],
};

it("preserves exact strings, dates, separate original links and explicit missing/applicability states", () => {
  const html = renderToStaticMarkup(<ComparisonView result={result}/>);
  expect(html).toContain("9,007,199,254,740,993.123456789 USD");
  expect(html).toContain(sourceRoute("old page", "original&source").replaceAll("&", "&amp;"));
  expect(html).toContain("Not applicable to this asset type");
  expect(html).toContain("Recorded availability: stale");
  expect(html).toContain("Incomplete research section");
  expect(html).toContain("does not refresh or recalculate");
  expect(html).toContain("no investment winner is selected");
});

it("displays period, method and share-basis incompatibility without a ranking or invented difference", () => {
  for (const [alignment, phrase] of [["different_periods", "Different dates"], ["different_units", "Different units"],
    ["different_methods", "Different calculation"], ["share_basis_unverified", "have not been reconciled"]] as const) {
    const copy = structuredClone(result);
    copy.rows[0].alignment = alignment; copy.rows[0].right = cell;
    expect(renderToStaticMarkup(<ComparisonView result={copy}/>)).toContain(phrase);
  }
});

it("keeps creation disabled offline and exposes saved-page controls without implying inference", () => {
  const html = renderToStaticMarkup(<Comparisons library={[]} saved={[]} settings={{ cloud_enabled: false }} resultId={null} initialLeft="older version"/>);
  expect(html).toContain("Offline: previously generated comparisons remain readable");
  expect(html).toContain('<button disabled="">Create and save comparison</button>');
  expect(html).toContain('value="older version" selected=""');
});

it("addresses immutable comparison results separately from a selected starting page", () => {
  expect(routeFromHash("#" + comparisonRoute("old/result?&")).comparison).toBe("old/result?&");
  expect(routeFromHash("#" + comparisonRoute(undefined, "older page")).bundle).toBe("older page");
  expect(routeFromHash("#" + comparisonRoute()).page).toBe("comparisons");
});
