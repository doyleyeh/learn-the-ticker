import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { conciseSelection, coreDefinition, normalizeTerm, TermLearning } from "./TermLearning";
import type { EvidenceBundle } from "./contracts";

describe("term learning", () => {
  it("finds curated terms independent of case and rejects oversized selections", () => {
    expect(coreDefinition("  eps ")?.term).toBe("EPS");
    expect(normalizeTerm("Ｒｅｖｅｎｕｅ")).toBe("revenue");
    expect(conciseSelection("  free   cash flow  ")).toBe("free cash flow");
    expect(conciseSelection("a ".repeat(17))).toBe("");
    expect(coreDefinition("an unknown term")).toBeUndefined();
  });
  it("keeps offline glossary controls available beside evidence", () => {
    const bundle: EvidenceBundle = { id: "snapshot", asset: { id: "TEST:TERM", name: "Synthetic term example", symbol: "TERM", asset_type: "stock" } };
    const html = renderToStaticMarkup(<TermLearning bundle={bundle} level="intermediate"><p>Canonical evidence remains separate.</p></TermLearning>);
    expect(html).toContain("Look up saved explanation");
    expect(html).toContain("Core definitions and previously generated explanations work offline");
    expect(html).toContain("Canonical evidence remains separate");
  });
});
