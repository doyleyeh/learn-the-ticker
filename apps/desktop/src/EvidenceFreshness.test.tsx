import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { EvidenceFreshness, SnapshotStatus } from "./EvidenceFreshness";
import type { EvidenceBundle } from "./contracts";

const bundle: EvidenceBundle = { asset: { id: "X:TEST", name: "Synthetic", symbol: "TEST", asset_type: "stock" }, created_at: "2026-10-05T12:00:00Z" };

it("a recent saved time cannot supply freshness or availability", () => {
  const html = renderToStaticMarkup(<SnapshotStatus bundle={bundle}/>);
  expect(html).toContain("Snapshot saved: 2026-10-05T12:00:00Z");
  expect(html).toContain("Availability when saved: Unknown");
  expect(html).not.toContain("Current evidence");
  expect(html).not.toContain("Partially available");
  const stale = renderToStaticMarkup(<SnapshotStatus bundle={{ ...bundle, state: "stale" }}/>);
  expect(stale).toContain("Availability when saved: Stale");
});

it("unassessed dates never hide original evidence or imply current verification", () => {
  const html = renderToStaticMarkup(<EvidenceFreshness bundleId="original"><p>Original evidence</p></EvidenceFreshness>);
  expect(html).toContain("Source age has not been assessed for this version");
  expect(html).toContain("Original evidence");
  expect(html).toContain("Source age does not establish a live quote");
  expect(html).not.toContain("within source age limits.");
});
