import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { FinancialHistory } from "./FinancialHistory";
import { KeyStatistics } from "./TickerDashboard";
import { FinancialRatios } from "./FinancialRatios";
import { chartGeometry, decimalInteger, displayNumber, financialSeries } from "./financialSeries";
import type { EvidenceBundle, FinancialObservation } from "./contracts";

function observation(overrides: Partial<FinancialObservation> = {}): FinancialObservation {
  return { id: "a".repeat(64), cik: "0000000001", concept: "us-gaap:Revenues", value: "9007199254740993.123456789", unit: "USD",
    start: "2025-01-01", end: "2025-12-31", period: "annual", accession: "0000000001-26-000001", filed: "2026-02-01", form: "10-K",
    reported_fiscal_year: 2025, reported_fiscal_period: "FY", source_id: "source1", revision: "current", ...overrides };
}

function bundle(rows: FinancialObservation[]): EvidenceBundle {
  const asset = { id: "FIGI:SYNTH", symbol: "SYNTH", name: "Synthetic Company", asset_type: "stock" as const };
  return { id: "saved/version", asset, sources: [{ id: "source1", asset_id: asset.id, url: "https://data.sec.gov/api/xbrl/companyconcept/CIK0000000001/us-gaap/Revenues.json",
    title: "Synthetic concept source", publisher: "Synthetic fixture", retrieved_at: "2026-10-04T00:00:00Z", published_at: "2026-02-01", as_of: "2025-12-31",
    verified: true, policy: "full_text_allowed", provenance: "structured_adapter" }], financials: {
      issuer: { ...asset, id: "SEC:1", identifiers: { cik: "0000000001" } }, checked_at: "2026-10-04T00:00:00Z",
      issuer_verification: { authority: "synthetic", source_url: "https://example.com/identity", retrieved_at: "2026-10-04T00:00:00Z", content_hash: "a".repeat(64), identity_hash: "b".repeat(64) },
      observations: rows, gaps: ["price_history_unavailable", "corporate_actions_unavailable", "Revenues:incomplete_annual_history"],
    } };
}

describe("admitted financial presentation", () => {
  function ratioBundle(): EvidenceBundle {
    const data = bundle([observation({ id: "revenue", value: "30" }), observation({ id: "income", concept: "us-gaap:NetIncomeLoss", value: "10", source_id: "source2" })]);
    data.sources!.push({ ...data.sources![0], id: "source2", title: "Synthetic net income source", url: "https://data.sec.gov/api/xbrl/companyconcept/CIK0000000001/us-gaap/NetIncomeLoss.json" });
    data.financials!.ratio_method = "sec-net-income-revenue-v1";
    data.financials!.ratios = [{ denominator_concept: "us-gaap:Revenues", period: "annual", start: "2025-01-01", end: "2025-12-31",
      input_ids: ["income", "revenue"], source_ids: ["source1", "source2"], percent: "33.333333", reason: null }];
    return data;
  }
  it("shows stored calculations separately with exact results, both original citations and dates", () => {
    const html = renderToStaticMarkup(<FinancialRatios bundle={ratioBundle()}/>);
    expect(html).toContain("33.333333%");
    expect(html).toContain("2025-01-01 through 2025-12-31");
    expect(html).toContain("10 USD");
    expect(html).toContain("30 USD");
    expect(html).toContain("source=source1");
    expect(html).toContain("source=source2");
    expect(html).toContain("Retrieved 2026-10-04T00:00:00Z");
    expect(html).toContain("sec-net-income-revenue-v1");
    expect(html).toContain("Saved results remain unchanged offline");
  });
  it("does not calculate results for an older saved version", () => {
    const data = ratioBundle();
    delete data.financials!.ratio_method;
    delete data.financials!.ratios;
    const html = renderToStaticMarkup(<FinancialRatios bundle={data}/>);
    expect(html).toContain("Not calculated for this saved version");
    expect(html).not.toContain("33.333333%");
  });
  it.each(["missing_source", "foreign_period", "conflict", "foreign_filing", "foreign_concept", "unknown_asset"])("withholds stored values with invalid display references: %s", (scenario) => {
    const data = ratioBundle();
    if (scenario === "missing_source") data.sources = [];
    if (scenario === "foreign_period") data.financials!.observations![0].start = "2025-01-02";
    if (scenario === "conflict") data.financials!.observations![0].revision = "conflict";
    if (scenario === "foreign_filing") data.financials!.observations![0].accession = "0000000001-26-000099";
    if (scenario === "foreign_concept") data.financials!.observations![0].concept = "us-gaap:Assets";
    if (scenario === "unknown_asset") data.asset.asset_type = "unknown";
    expect(renderToStaticMarkup(<FinancialRatios bundle={data}/>)).not.toContain("33.333333%");
  });
  it("discloses incompatible latest inputs without inventing a result", () => {
    const data = ratioBundle();
    data.financials!.ratios![0].percent = null;
    data.financials!.ratios![0].reason = "different_filings";
    const html = renderToStaticMarkup(<FinancialRatios bundle={data}/>);
    expect(html).toContain("latest inputs come from different filings");
    expect(html).not.toContain("33.333333%");
  });
  it("retains exact decimals beyond JavaScript precision, using bounded integers only for geometry", () => {
    const value = "9007199254740993.123456789";
    expect(displayNumber(value)).toBe("9,007,199,254,740,993.123456789");
    expect(decimalInteger(value)).toBe(9007199254740993123456789000000000n);
    const points = financialSeries(bundle([observation()])).series[0].points;
    expect(chartGeometry(points)).toEqual({ zero: 0, positions: [100] });
    const html = renderToStaticMarkup(<FinancialHistory bundle={bundle([observation()])}/>);
    expect(html).toContain("9,007,199,254,740,993.123456789");
    expect(html).toContain("2025-01-01 through 2025-12-31");
    expect(html).toContain("Filed 2026-02-01");
    expect(html).toContain("Retrieved 2026-10-04T00:00:00Z");
    expect(html).toContain("bundle=saved%2Fversion&amp;source=source1");
  });
  it("keeps currencies, concepts and annual versus quarter periods separate", () => {
    const rows = [observation(), observation({ id: "b", unit: "EUR" }), observation({ id: "c", period: "quarter", end: "2025-03-31" }),
      observation({ id: "d", concept: "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax" })];
    expect(financialSeries(bundle(rows)).series).toHaveLength(4);
  });
  it("excludes conflicts and superseded values and deduplicates equal latest filing values", () => {
    const data = bundle([observation({ revision: "superseded", value: "10" }), observation({ id: "b", value: "20" }), observation({ id: "c", value: "20" }),
      observation({ id: "d", value: "30", end: "2024-12-31", start: "2024-01-01", revision: "conflict" })]);
    const series = financialSeries(data).series[0];
    expect(series.points).toHaveLength(1);
    expect(series.points[0].row.value).toBe("20");
    expect(series.points[0].citations).toHaveLength(2);
    expect(series.withheld).toBe(1);
    expect(series.rows).toHaveLength(4);
    expect(renderToStaticMarkup(<FinancialHistory bundle={data}/>)).toContain("withheld from the chart");
  });
  it("withholds internally contradictory current observations", () => {
    const series = financialSeries(bundle([observation({ value: "10" }), observation({ id: "b", value: "11" })])).series[0];
    expect(series.points).toHaveLength(0);
    expect(series.withheld).toBe(1);
  });
  it("bounds the default annual view while preserving older filings for inspection", () => {
    const rows = Array.from({ length: 8 }, (_, index) => observation({ id: String(index), start: `${2018 + index}-01-01`, end: `${2018 + index}-12-31` }));
    const series = financialSeries(bundle(rows)).series[0];
    expect(series.points).toHaveLength(5);
    expect(series.points[0].row.start).toBe("2021-01-01");
    expect(series.rows).toHaveLength(8);
  });
  it("does not take model claims, notes, or detached source references as numbers", () => {
    const data = bundle([observation({ source_id: "missing" })]);
    data.claims = [{ asset_id: data.asset.id, kind: "fact", text: "Model numeric text", value: 999, source_ids: ["source1"] }];
    data.notes = [{ asset_id: data.asset.id, text: "Unverified numeric text", value: 777 }];
    expect(financialSeries(data).series).toHaveLength(0);
    const html = renderToStaticMarkup(<FinancialHistory bundle={data}/>);
    expect(html).not.toContain("Model numeric text");
    expect(html).not.toContain("Unverified numeric text");
    expect(html).toContain("source or numeric reference could not be validated");
  });
  it.each(["verified", "asset_id", "policy", "provenance"])("rejects inadmissible source %s", (field) => {
    const data = bundle([observation()]);
    Object.assign(data.sources![0], { [field]: field === "verified" ? false : "wrong" });
    expect(financialSeries(data).excluded).toBe(1);
  });
  it("represents positive, negative and all-zero values around a finite zero baseline", () => {
    const points = [-10, 0, 20].map((value) => ({ row: observation({ value: String(value) }), citations: [] }));
    expect(chartGeometry(points)).toEqual({ zero: 33.33, positions: [0, 33.33, 100] });
    expect(chartGeometry([points[1]])).toEqual({ zero: 0, positions: [0] });
    expect(decimalInteger("NaN")).toBeUndefined();
    expect(decimalInteger("1e9")).toBeUndefined();
    expect(decimalInteger("0." + "1".repeat(19))).toBeUndefined();
  });
  it("keeps unavailable price/total returns separate and suppresses unadjusted share trends", () => {
    const data = bundle([observation({ concept: "us-gaap:EarningsPerShareDiluted", unit: "USD/shares" })]);
    const html = renderToStaticMarkup(<FinancialHistory bundle={data}/>);
    expect(html).not.toContain("<svg");
    expect(html).toContain("Trend chart unavailable");
    expect(html).toContain("Price return: unavailable");
    expect(html).toContain("Total return: unavailable");
    expect(html).toContain("Historical valuation: unavailable");
  });
  it("shows old snapshots without inventing financial observations", () => {
    const data = bundle([]); delete data.financials;
    expect(renderToStaticMarkup(<FinancialHistory bundle={data}/>)).toContain("no independently admitted financial observations");
  });
  it("statistics retain exact dated source figures without generating market ratios", () => {
    const html = renderToStaticMarkup(<KeyStatistics bundle={bundle([observation()])}/>);
    expect(html).toContain("9,007,199,254,740,993.123456789");
    expect(html).toContain("2025-01-01 through 2025-12-31");
    expect(html).toContain("Filed 2026-02-01");
    expect(html).toContain("Synthetic fixture");
    expect(html).toContain("bundle=saved%2Fversion&amp;source=source1");
    expect(html).toContain("P/E and dividend yield: unavailable");
  });
  it("statistics do not replace a conflicted latest period with an older observation", () => {
    const html = renderToStaticMarkup(<KeyStatistics bundle={bundle([
      observation({ value: "12345", start: "2024-01-01", end: "2024-12-31" }),
      observation({ id: "b", value: "54321", revision: "conflict" }),
    ])}/>);
    expect(html).toContain("Latest period unavailable");
    expect(html).not.toContain("12,345");
    expect(html).not.toContain("54,321");
  });
  it("statistics cannot draw from missing numeric sources or prose", () => {
    const data = bundle([observation({ source_id: "missing" })]);
    data.notes = [{ asset_id: data.asset.id, text: "unverified-statistic 12345", value: 12345 }];
    data.claims = [{ asset_id: data.asset.id, kind: "fact", text: "model-statistic 54321", value: 54321 }];
    const html = renderToStaticMarkup(<KeyStatistics bundle={data}/>);
    expect(html).toContain("no independently admitted financial statistics");
    expect(html).not.toContain("unverified-statistic");
    expect(html).not.toContain("model-statistic");
  });
});
