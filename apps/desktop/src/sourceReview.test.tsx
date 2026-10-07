import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { SourceReviewCard } from "./SourceReview";

it("keeps every source unchecked and describes unknown dates and independent validation", () => {
  const html = renderToStaticMarkup(<SourceReviewCard request={{ run_id: "synthetic-run", asset_id: "SYNTHETIC", expires_at: "2099-01-01T00:00:00Z", sources: [
    { id: "s", url: "https://www.sec.gov/example", publisher: "<script>publisher</script>", policy: "full_text_allowed", rights_url: "https://www.sec.gov/terms", reviewed_at: "2026-10-04" },
  ] }} onDecide={async () => {}}/>);
  expect(html).not.toContain("checked=");
  expect(html).toContain('disabled=""');
  expect(html).toContain("publication and as-of dates remain unknown");
  expect(html).toContain("Approval does not verify facts");
  expect(html).toContain("&lt;script&gt;publisher");
  expect(html).toContain("Skip these sources");
});

it("identifies the experimental numerical exception without claiming a text permission grant", () => {
  const html = renderToStaticMarkup(<SourceReviewCard request={{ run_id: "private-run", asset_id: "SYN", expires_at: "2099-01-01T00:00:00Z", sources: [
    { id: "s", url: "https://finance.yahoo.com/quote/SYN/history/", publisher: "Yahoo Finance", policy: "metadata_only", local_numeric_only: true, rights_url: "https://help.yahoo.com/", reviewed_at: "2026-10-04" },
  ] }} onDecide={async () => {}}/>);
  expect(html).not.toContain("checked=");
  expect(html).toContain("Numerical evidence for personal learning");
  expect(html).toContain("not a Yahoo permission grant");
  expect(html).toContain("can enter the selected AI provider");
});
