import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { EvidenceBundle } from "./contracts";
import fixture from "./fixtures/privateMarket.json";
import { MarketHistory } from "./MarketHistory";
import { ValuationAvailability } from "./ValuationAvailability";
import { Connections } from "./Connections";
import { admittedMarket, chartRows, priceGeometry, privateClaims, privateSource } from "./marketPresentation";

// The same JSON fixture is validated by the backend contract test.
const bundle = () => structuredClone(fixture) as unknown as EvidenceBundle;

describe("private market presentation", () => {
  it("restricts legacy Yahoo references and transitive derivatives from automatic selection", () => {
    const data = bundle();
    data.sources![0].usage_scope = "standard"; data.sources![0].provenance = "verified_retrieval";
    expect(privateSource(data.sources![0])).toBe(true);
    data.claims = [
      { id: "derived", asset_id: data.asset.id, text: "second-hop", input_claim_ids: ["first"] },
      { id: "first", asset_id: data.asset.id, text: "first-hop", input_claim_ids: ["price"] },
      { id: "price", asset_id: data.asset.id, text: "private", source_ids: [data.sources![0].id!] },
      { id: "public", asset_id: data.asset.id, text: "general" },
    ];
    expect([...privateClaims(data)].sort()).toEqual(["derived", "first", "price"]);
  });
  it("preserves exact values, original citations and separate saved return methods", () => {
    const data = bundle(), html = renderToStaticMarkup(<MarketHistory bundle={data}/>);
    expect(html).toContain("9,007,199,254,740,993");
    expect(html).toContain("0.123456789012345678 USD");
    expect(html).toContain("27.272727%");
    expect(html).toContain("40%");
    expect(html).toContain("Observed 2026-01-02 through 2026-01-05");
    expect(html).toContain("No observation at or before the required start boundary");
    expect(html).toContain(`source=${encodeURIComponent(data.market!.source_id)}`);
    expect(html).toContain("bundle=synthetic-private-version");
    expect(html).toContain("data-local-only=\"true\"");
    expect(html).toContain("Historical snapshot, not a current quote");
    expect(html).toContain("reinvestment proxy");
    expect(html).toContain("Daily snapshot · 2026-01-05");
    expect(html).toContain("Preceding retained close");
    expect(html).toContain("11 USD<br/>2026-01-02");
    expect(html).toContain("may not be the previous trading session");
  });
  it.each(["verified", "asset_id", "policy", "usage_scope", "provenance"])("withholds prices detached from original source %s", (field) => {
    const data = bundle();
    Object.assign(data.sources![0], { [field]: field === "verified" ? false : "wrong" });
    expect(admittedMarket(data)).toBeUndefined();
    const html = renderToStaticMarkup(<MarketHistory bundle={data}/>);
    expect(html).not.toContain("<svg");
    expect(html).not.toContain("27.272727");
    expect(html).toContain("could not be validated for display");
  });
  it("does not create numbers from notes, prose or older versions without saved calculations", () => {
    const data = bundle();
    data.market!.return_method = null; data.market!.returns = [];
    const html = renderToStaticMarkup(<MarketHistory bundle={data}/>);
    expect(html).toContain("Returns were not retained in this version");
    expect(html).not.toContain("27.272727");
    data.market = null;
    data.notes = [{ asset_id: data.asset.id, text: "Unverified price 8888888" }];
    expect(renderToStaticMarkup(<MarketHistory bundle={data}/>)).not.toContain("8888888");
  });
  it("does not invent a preceding session or valuation when history is partial", () => {
    const data = bundle();
    data.market!.bars = [data.market!.bars[0]];
    expect(renderToStaticMarkup(<MarketHistory bundle={data}/>)).toContain("no earlier observation retained");
    const html = renderToStaticMarkup(<ValuationAvailability bundle={data}/>);
    expect(html).toContain("Historical daily prices are retained");
    expect(html).toContain("data-local-only=\"true\"");
    data.sources = [];
    expect(renderToStaticMarkup(<ValuationAvailability bundle={data}/>)).toContain("verified daily price snapshot is unavailable");
    data.asset.asset_type = "unknown";
    expect(renderToStaticMarkup(<ValuationAvailability bundle={data}/>)).toContain("until its identity is confirmed");
  });
  it("withholds a detached or incomplete stored return without recomputation", () => {
    const data = bundle(), row = data.market!.returns!.at(-1)!;
    row.source_id = "missing";
    expect(renderToStaticMarkup(<MarketHistory bundle={data}/>)).toContain("original return reference is missing");
    row.source_id = data.market!.source_id; row.price_percent = null;
    expect(renderToStaticMarkup(<MarketHistory bundle={data}/>)).toContain("no complete saved result");
  });
  it("uses exact integer differences for geometry above JavaScript precision and never bridges known gaps", () => {
    const base = bundle().market!.bars[0];
    const rows = [
      { ...base, date: "2026-01-01", close: "9007199254740992.000000000000000001" },
      { ...base, date: "2026-01-02", close: "9007199254740992.000000000000000002" },
      { ...base, date: "2026-01-20", close: "9007199254740992.000000000000000003" },
    ];
    const result = priceGeometry(rows, false)!;
    expect(result.points.map((point) => point.y)).toEqual([220, 125, 30]);
    expect(result.segments.map((segment) => segment.length)).toEqual([2, 1]);
    expect(priceGeometry(rows, true)!.segments).toHaveLength(3);
    expect(priceGeometry([rows[0]], false)!.points[0]).toMatchObject({ x: 350, y: 125 });
  });
  it("filters retained dates relative to the saved endpoint with month/leap boundaries", () => {
    const base = bundle().market!.bars[0];
    const rows = ["2023-02-27", "2023-02-28", "2024-01-28", "2024-01-29", "2024-02-29"].map((date) => ({ ...base, date }));
    expect(chartRows(rows, "1y").map((row) => row.date)).toEqual(["2023-02-28", "2024-01-28", "2024-01-29", "2024-02-29"]);
    expect(chartRows(rows, "1m").map((row) => row.date)).toEqual(["2024-01-29", "2024-02-29"]);
    expect(chartRows(rows, "ytd")).toHaveLength(3);
    expect(chartRows(rows, "all")).toEqual(rows);
  });
  it("defaults Connections opt-in off and explains the operation boundaries", () => {
    const html = renderToStaticMarkup(<Connections settings={{ provider: "codex", language: "en" }} onSave={async () => {}}/>);
    expect(html).not.toContain("checked=");
    expect(html).toContain("Enable experimental private Yahoo history");
    expect(html).toContain("Off by default and after restore");
    expect(html).toContain("shareable exports");
  });
});
