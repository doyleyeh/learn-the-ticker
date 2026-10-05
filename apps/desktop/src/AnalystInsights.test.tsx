import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { EvidenceBundle } from "./contracts";
import fixture from "./fixtures/privateEstimates.json";
import { admittedEstimates, AnalystInsights } from "./AnalystInsights";

const bundle = () => structuredClone(fixture) as unknown as EvidenceBundle;
describe("attributed analyst opinions", () => {
  it("preserves exact values, units, forecast dates, unknown publication time and saved citations", () => {
    const data = bundle(), html = renderToStaticMarkup(<AnalystInsights bundle={data}/>);
    expect(html).toContain("1.25000000000000001 USD/share");
    expect(html).toContain("9,007,199,254,740,993 USD");
    expect(html).toContain("2026-03-31");
    expect(html).toContain("Third-party opinions");
    expect(html).toContain("Estimate publication / as-of time unknown");
    expect(html).toContain("No retained estimates for this period");
    expect(html).toContain("not reported results");
    expect(html).toContain(`source=${encodeURIComponent(data.market!.estimates!.source_id)}`);
    expect(html).toContain(`bundle=${data.id}`);
  });
  it.each(["verified", "asset_id", "policy", "usage_scope", "url", "as_of", "published_at"])("withholds a detached or misdated source: %s", (field) => {
    const data = bundle();
    Object.assign(data.sources!.at(-1)!, { [field]: field === "verified" ? false : "wrong" });
    expect(admittedEstimates(data)).toBeUndefined();
    expect(renderToStaticMarkup(<AnalystInsights bundle={data}/>)).not.toContain("1.25000000000000001");
  });
  it("preserves missing currency without borrowing the revenue currency", () => {
    const data = bundle(), p = data.market!.estimates!.points[0];
    p.currency = null; p.unit = null; p.average = null; p.low = null; p.high = null; p.reason = "currency_missing";
    const html = renderToStaticMarkup(<AnalystInsights bundle={data}/>);
    expect(html).toContain("Source currency missing");
    expect(html).not.toContain("1.25000000000000001");
    expect(html).toContain("9,007,199,254,740,993 USD");
  });
  it("rejects duplicates and unsupported units", () => {
    const data = bundle(); data.market!.estimates!.points.push(data.market!.estimates!.points[0]);
    expect(admittedEstimates(data)).toBeUndefined();
    const units = bundle(); units.market!.estimates!.points[0].unit = "USD";
    expect(admittedEstimates(units)).toBeUndefined();
  });
  it("does not use notes or fetch on missing saved estimates", () => {
    const data = bundle(); data.market!.estimates = null; data.market!.estimate_gap = "not_selected";
    data.notes = [{ asset_id: data.asset.id, text: "Forecast 998877" }];
    const html = renderToStaticMarkup(<AnalystInsights bundle={data}/>);
    expect(html).toContain("Analyst source was not selected");
    expect(html).not.toContain("998877");
  });
});
