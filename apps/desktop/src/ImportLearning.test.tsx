import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ImportExplanationDetails, ImportLearning } from "./ImportLearning";
import type { RetainedImportView } from "./contracts";

const view: RetainedImportView = { item: { id: "synthetic", title: "Document", format: "csv", origin: "local_file", source: null,
  checked_at: "2026-01-01T00:00:00Z", retained_at: "2026-01-02T00:00:00Z", content_hash: "a".repeat(64), byte_count: 20 },
  document: { format: "csv", content_hash: "a".repeat(64), blocks: [], limitations: ["unverified_import"] } };

describe("document learning disclosure", () => {
  it("requires separate sharing permission and discloses cached-only context", () => {
    const html = renderToStaticMarkup(<ImportLearning view={view} level="beginner" settings={{ cloud_enabled: false }}/>);
    expect(html).toContain("browsing disabled");
    expect(html).toContain("Previously saved explanations remain available");
    expect(html).toContain("permission to send this document");
    expect(html).toContain('disabled="">Explain this document');
    expect(html).not.toContain('checked=""');
  });
  it("renders exact escaped references and never calls the generated date fresh", () => {
    const html = renderToStaticMarkup(<ImportExplanationDetails value={{ id: "b".repeat(64), document_id: view.item.id,
      content_hash: view.item.content_hash, provider: "codex", explanation: "<script>Unverified 9007199254740993</script>",
      references: [{ locator: "Sheet 文字 row 2 / B2", quote: "9007199254740993" }], created_at: "2026-03-01T00:00:00Z" }}/>);
    expect(html).toContain("Saved interpretation · Unverified");
    expect(html).toContain("9007199254740993");
    expect(html).toContain("Sheet 文字 row 2 / B2");
    expect(html).toContain("does not establish source freshness");
    expect(html).not.toContain("<script>");
  });
});
