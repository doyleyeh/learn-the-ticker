import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ImportDocuments, ImportPreviewDetails } from "./ImportDocuments";
import type { ImportPreview } from "./contracts";

describe("import preview trust boundary", () => {
  it("escapes document instructions and preserves original number strings and locators", () => {
    const preview: ImportPreview = { state: "unverified", origin: "local_file", checked_at: "2026-10-04T00:00:00Z",
      document: { format: "csv", content_hash: "a".repeat(64), blocks: [{ locator: "row 2", cells: [
        { locator: "R2C1", text: "<script>sendSecrets()</script>", kind: "text" },
        { locator: "R2C2", text: "123456789.123456789", kind: "text" },
      ] }], limitations: ["unverified_import"] } };
    const html = renderToStaticMarkup(<ImportPreviewDetails preview={preview} filename="Synthetic.csv"/>);
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
    expect(html).toContain("123456789.123456789");
    expect(html).toContain("R2C2");
    expect(html).toContain("cannot supply facts or chart values");
    expect(html).toContain("has not been added to your library");
    expect(html).toContain("File timestamps do not establish these dates");
  });
  it("never labels an undownloaded link as a retrieved source", () => {
    const preview: ImportPreview = { state: "link_only", origin: "public_url", checked_at: "2026-10-04T00:00:00Z",
      source: { id: "import-preview", asset_id: "unassigned", title: "Imported URL", publisher: "Unverified source", url: "https://unknown.example/article", policy: "link_only", retrieved_at: "2026-10-04T00:00:00Z" } };
    const html = renderToStaticMarkup(<ImportPreviewDetails preview={preview} filename=""/>);
    expect(html).toContain('href="https://unknown.example/article"');
    expect(html).toContain("No document content was downloaded");
    expect(html).toContain("Published: Unknown");
    expect(html).not.toContain("Retrieved:");
    expect(html).not.toContain("Extracted content");
  });
  it("keeps local-file permission explicit and URL retrieval disabled offline", () => {
    const html = renderToStaticMarkup(<ImportDocuments online={false}/>);
    expect(html).toContain('type="file"');
    expect(html).toContain("I have permission to process this document locally");
    expect(html).toContain("Works offline");
    expect(html).toContain('disabled="">Preview URL');
  });
  it("labels retained copies separately from verified evidence and preserves original dates", () => {
    const checked = "2026-01-01T00:00:00Z";
    const preview: ImportPreview = { state: "unverified", origin: "local_file", checked_at: checked,
      document: { format: "csv", content_hash: "a".repeat(64), blocks: [], limitations: ["unverified_import"] } };
    const html = renderToStaticMarkup(<ImportPreviewDetails preview={preview} filename="<script>untrusted</script>" retained={{
      id: "synthetic", title: "Synthetic", format: "csv", origin: "local_file", source: null, checked_at: checked,
      retained_at: "2026-02-01T00:00:00Z", byte_count: 10, content_hash: "a".repeat(64),
    }}/>);
    expect(html).toContain("Unverified retained document");
    expect(html).toContain("not verified as factual evidence");
    expect(html).toContain("Original content check");
    expect(html).toContain("local storage and backup");
    expect(html).not.toContain("has not been added");
    expect(html).not.toContain("<script>");
    expect(html).toContain('id="retained-preview-heading"');
  });
});
