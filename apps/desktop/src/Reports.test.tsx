import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { DatedContext, Reports } from "./Reports";
import type { ResearchReport } from "./contracts";
import { reportRoute, routeFromHash, sourceRoute } from "./routes";

const report: ResearchReport = { id: "original-report", bundle_id: "older page", created_at: "2026-10-04T12:00:00Z",
  evidence_saved_at: "2026-10-04T00:00:00Z", fingerprint: "a".repeat(64),
  asset: { id: "example", name: "Synthetic issuer", symbol: "SYN", asset_type: "stock" },
  focus: { window: { as_of: "2026-10-04", previous_start: "2026-09-21", previous_end: "2026-09-27",
    current_start: "2026-09-28", current_end: "2026-10-03", earlier_start: "2026-09-04", earlier_end: "2026-09-20" },
  weekly: [], earlier: [{ event_id: "earlier", source_id: "original-source", title: "8-K filing", published: "2026-09-17", effective: "2026-09-15", bucket: "earlier_context" }],
  earlier_requested: true, analysis_available: false },
};

it("separates older publication/effective dates from the weekly count and suppresses sparse analysis", () => {
  const html = renderToStaticMarkup(<DatedContext report={report}/>);
  for (const text of ["Weekly items (0)", "Earlier context", "Excluded from weekly counts", "Published 2026-09-17", "2026-09-15", "Fewer than two verified weekly items", "historical report remains usable"])
    expect(html).toContain(text);
  expect(html).toContain(sourceRoute("older page", "original-source").replaceAll("&", "&amp;"));
});

it("discloses the app reading guide and Monday's empty current week", () => {
  const copy = structuredClone(report);
  copy.focus.window.current_start = null; copy.focus.window.current_end = null;
  copy.reading_guide = "Synthetic bounded reading guide."; copy.guide_source_ids = ["weekly-source"];
  const html = renderToStaticMarkup(<DatedContext report={copy}/>);
  expect(html).toContain("current week is empty on Monday");
  expect(html).toContain("no AI synthesis or fresh retrieval");
  expect(html).toContain("Guide source 1");
});

it("keeps new report creation disabled offline while preserving the explicit original selection", () => {
  const html = renderToStaticMarkup(<Reports library={[]} saved={[]} settings={{ cloud_enabled: false }} reportId={null} initialBundle="old-version"/>);
  expect(html).toContain('<button disabled="">Save dated report</button>');
  expect(html).toContain("No recent-news minimum");
  expect(html).toContain('value="old-version" selected=""');
  expect(routeFromHash("#" + reportRoute("report?&")).report).toBe("report?&");
  expect(routeFromHash("#" + reportRoute(undefined, "old/version")).bundle).toBe("old/version");
});
