import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { EvidenceBundle } from "./contracts";
import fixture from "./fixtures/privateValuations.json";
import { admittedValuations, ProviderValuations } from "./ProviderValuations";

const bundle = () => structuredClone(fixture) as unknown as EvidenceBundle;
describe("supplied private valuation observations", () => {
  it("retains exact values, dates, provider attribution and original version citations", () => {
    const data = bundle(), html = renderToStaticMarkup(<ProviderValuations bundle={data}/>);
    expect(html).toContain("28.123456789012345678 ×");
    expect(html).toContain("29.5 ×");
    expect(html).toContain("As of 2026-01-05");
    expect(html).toContain("Unavailable — source value missing");
    expect(html).toContain("Provider calculations");
    expect(html).not.toContain("data-local-only=\"true\"");
    expect(html).toContain("Fewer than 12 observations were supplied");
    expect(html).toContain("not proven point-in-time records");
    expect(html).toContain(`source=${encodeURIComponent(data.market!.valuations!.source_id)}`);
    expect(html).toContain("bundle=synthetic-valuations-version");
  });
  it.each(["verified", "asset_id", "policy", "usage_scope", "url"])("withholds a detached source: %s", (field) => {
    const data = bundle();
    Object.assign(data.sources!.at(-1)!, { [field]: field === "verified" ? false : "wrong" });
    expect(admittedValuations(data)).toBeUndefined();
    expect(renderToStaticMarkup(<ProviderValuations bundle={data}/>)).not.toContain("28.123456789012345678");
  });
  it("does not substitute an earlier trailing value when the newest is missing", () => {
    const data = bundle(), latest = data.market!.valuations!.points.at(-1)!;
    latest.value = null; latest.reason = "value_missing";
    const html = renderToStaticMarkup(<ProviderValuations bundle={data}/>);
    expect(html).not.toContain("29.5 ×");
    expect(html).toContain("As of 2026-01-05");
  });
  it("rejects duplicate and currencyless monetary inputs", () => {
    const data = bundle();
    data.market!.valuations!.points[0].currency = null;
    expect(admittedValuations(data)).toBeUndefined();
    const duplicate = bundle();
    duplicate.market!.valuations!.points.push(duplicate.market!.valuations!.points[0]);
    expect(admittedValuations(duplicate)).toBeUndefined();
  });
  it("preserves old-version missing state without computing or reading notes", () => {
    const data = bundle(); data.market!.valuations = null;
    data.notes = [{ asset_id: data.asset.id, text: "P/E 999888" }];
    const html = renderToStaticMarkup(<ProviderValuations bundle={data}/>);
    expect(html).toContain("No provider valuation observations are retained");
    expect(html).not.toContain("999888");
  });
});
