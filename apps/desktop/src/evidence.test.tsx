import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { EvidenceView } from "./App";

it("keeps unverified claims out of canonical sections and escapes source content", () => {
  const html = renderToStaticMarkup(<EvidenceView bundle={{ asset: { id: "X:TEST", symbol: "TEST", name: "Synthetic", asset_type: "crypto" }, claims: [], notes: [{ id: "n", asset_id: "X:TEST", text: "<script>fictional metric</script>", kind: "unverified_note" }], sources: [] }}/>);
  expect(html).toContain("Unavailable — no admitted evidence");
  expect(html).not.toContain("<script>");
  expect(html.split('data-evidence-layer="notes"')[0]).not.toContain("fictional metric");
  expect(html).toContain("&lt;script&gt;fictional metric&lt;/script&gt;");
});
