import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { EvidenceView } from "./TickerDashboard";
import type { EvidenceBundle } from "./contracts";

it("opens the original numerical version from an interpretation without presenting it as a fact", () => {
  const bundle: EvidenceBundle = { id: "new-version", asset: { id: "TEST:SYN", symbol: "SYN", name: "Synthetic", asset_type: "stock" },
    context_references: [{ id: "saved-reference", bundle_id: "original-version", source_id: "original-source" }],
    notes: [{ id: "note", kind: "unverified_note", asset_id: "TEST:SYN", text: "An interpretation of earlier data.", source_ids: ["saved-reference"] }] };
  const html = renderToStaticMarkup(<EvidenceView bundle={bundle}/>);
  expect(html).toContain("bundle=original-version");
  expect(html).toContain("source=original-source");
  expect(html).toContain("Original saved numerical evidence");
  expect(html).toContain("Unverified research notes");
  expect(html).toContain("data-local-only=\"true\"");
  expect(html).not.toContain("source=saved-reference");
});
