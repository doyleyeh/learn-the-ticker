import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CitationChip } from "../components/CitationChip";
import type { Citation, SourceDocument } from "../lib/fixtures";

const citation: Citation = {
  citationId: "filing-1", sourceDocumentId: "original-1", title: "Issuer report deterministic fixture",
  publisher: "Example issuer", freshnessState: "stale",
};
const source: SourceDocument = {
  ...citation, sourceType: "issuer_report", url: "https://example.com/report",
  publishedAt: "2025-01-01", retrievedAt: "2026-10-07", isOfficial: true, supportingPassage: "Synthetic evidence.",
};

describe("citation links across the desktop migration", () => {
  it("keeps the desktop destination and label with incoming source metadata", () => {
    const html = renderToStaticMarkup(<CitationChip citation={citation} source={source} href="#/sources/exact-version" label="Original filing" />);
    expect(html).toContain('href="#/sources/exact-version"');
    expect(html).toContain("[Original filing]");
    expect(html).toContain('aria-label="Open source drawer for Issuer report"');
    expect(html).toContain('data-freshness-state="stale"');
    expect(html).toContain('data-source-document-id="original-1"');
  });

  it("retains reference anchors and source labels without relabeling unknown evidence", () => {
    const official = renderToStaticMarkup(<CitationChip citation={citation} source={source} />);
    expect(official).toContain('href="#source-original-1"');
    expect(official).toContain("[Issuer]");
    const unknown = renderToStaticMarkup(<CitationChip citation={citation} />);
    expect(unknown).toContain("Issuer report deterministic fixture");
  });
});
