import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { CheckpointNotice, EvidenceView } from "./App";

it("keeps unverified claims out of canonical sections and escapes source content", () => {
  const html = renderToStaticMarkup(<EvidenceView bundle={{ asset: { id: "X:TEST", symbol: "TEST", name: "Synthetic", asset_type: "crypto" }, claims: [], notes: [{ id: "n", asset_id: "X:TEST", text: "<script>fictional metric</script>", kind: "unverified_note" }], sources: [] }}/>);
  expect(html).toContain("Unavailable — no admitted evidence");
  expect(html).not.toContain("<script>");
  expect(html.split('data-evidence-layer="notes"')[0]).not.toContain("fictional metric");
  expect(html).toContain("&lt;script&gt;fictional metric&lt;/script&gt;");
});

it("restores applicable stock/fund headings without fixture facts", () => {
  const stock = renderToStaticMarkup(<EvidenceView bundle={{ asset: { id: "X:TEST", symbol: "TEST", name: "Synthetic", asset_type: "stock" } }}/>);
  const fund = renderToStaticMarkup(<EvidenceView bundle={{ asset: { id: "X:TEST", symbol: "TEST", name: "Synthetic", asset_type: "etf" } }}/>);
  expect(stock).toContain("Products and services");
  expect(stock).toContain("Reported business strengths");
  expect(fund).toContain("Fund objective and role");
  expect(fund).toContain("Holdings and exposures");
  expect(fund).toContain("Costs and trading context");
  expect(fund).toContain("Unavailable — no admitted evidence");
  expect(fund).not.toContain("Products and services");
});

it("hides type-dependent claims when the instrument type is unresolved", () => {
  const html = renderToStaticMarkup(<EvidenceView bundle={{ asset: { id: "X:TEST", symbol: "TEST", name: "Synthetic", asset_type: "unknown" }, claims: [{ asset_id: "X:TEST", text: "Unconfirmed fund holdings", section: "holdings", source_ids: [] }] }}/>);
  expect(html).toContain("Asset type is unconfirmed");
  expect(html).not.toContain("Unconfirmed fund holdings");
});

it("distinguishes incomplete research from evidence availability", () => {
  const html = renderToStaticMarkup(<CheckpointNotice completion="section_checkpoint"/>);
  expect(html).toContain("Incomplete research");
  expect(html).toContain("may have stopped");
  expect(html).toContain("Earlier completed research is unchanged");
  expect(renderToStaticMarkup(<CheckpointNotice completion="complete"/>)).toBe("");
});
