import type { Citation, EconomicIndicatorsPackFixture } from "../lib/fixtures";
import { CompactCitationSources, resolveCitationList } from "./CompactCitationSources";
import { FreshnessDisclosure } from "./FreshnessLabel";

type EconomicIndicatorsPanelProps = {
  pack: EconomicIndicatorsPackFixture;
  citations: Citation[];
};

function trendSymbol(direction: EconomicIndicatorsPackFixture["items"][number]["trendDirection"]) {
  if (direction === "up") {
    return "up";
  }
  if (direction === "down") {
    return "down";
  }
  if (direction === "neutral") {
    return "flat";
  }
  return "unknown";
}

export function EconomicIndicatorsPanel({ pack, citations }: EconomicIndicatorsPanelProps) {
  const officialCount = pack.items.filter((item) => item.category === "official_historical_actual").length;
  const marketReferenceCount = pack.items.length - officialCount;

  return (
    <section
      className="plain-panel stable-section"
      aria-labelledby="beginner-economic-indicators"
      data-beginner-stable-recent-separation="context"
      data-prd-section="economic_indicators"
      data-economic-indicators
      data-economic-indicators-schema={pack.schemaVersion}
      data-economic-indicators-region={pack.region}
      data-economic-indicators-item-count={pack.items.length}
      data-economic-indicators-official-count={officialCount}
      data-economic-indicators-market-reference-count={marketReferenceCount}
      data-economic-indicators-analysis-source={pack.analysisPackMetadata?.analysisSource ?? "deterministic_fixture"}
      data-economic-indicators-validation-status={pack.analysisPackMetadata?.validationStatus ?? "passed"}
      data-economic-indicators-no-live-external={pack.noLiveExternalCalls ? "true" : "false"}
    >
      <div className="section-heading-row">
        <div className="section-heading">
          <p className="eyebrow">Common U.S. context</p>
          <h2 id="beginner-economic-indicators">Economic Indicators</h2>
        </div>
        <div className="state-row">
          <span className="state-pill compact-state" data-evidence-state={pack.state}>
            {pack.region} pack
          </span>
        </div>
      </div>

      <p className="notice-text">
        Economic Indicators are shared context for learning and stay separate from the asset's own source-backed facts.
      </p>

      <div className="freshness-disclosure-row">
        <FreshnessDisclosure label="Indicator pack as of" value={pack.asOfDate} state="fresh" />
        {pack.analysisPackMetadata?.freshnessExpiresAt ? (
          <FreshnessDisclosure
            label="Imported pack fresh until"
            value={pack.analysisPackMetadata.freshnessExpiresAt}
            state="fresh"
          />
        ) : null}
      </div>

      <div className="structured-table-panel" data-economic-indicators-table>
        <div className="structured-table-heading">
          <div>
            <h3>U.S. macro and market references</h3>
            <p>Official historical actuals first, followed by source-labeled market references.</p>
          </div>
        </div>
        <div className="structured-table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Indicator</th>
                <th scope="col">Value</th>
                <th scope="col">Period / as of</th>
                <th scope="col">Source</th>
              </tr>
            </thead>
            <tbody>
              {pack.items.map((item) => (
                <tr
                  key={item.indicatorId}
                  data-economic-indicator-id={item.indicatorId}
                  data-economic-indicator-category={item.category}
                  data-economic-indicator-freshness={item.freshnessState}
                >
                  <td>
                    <strong>{item.name}</strong>
                    <br />
                    <span className="source-gap-note">
                      {item.category === "market_reference" ? "Market reference" : "Official historical actual"}
                    </span>
                  </td>
                  <td>
                    <strong>
                      {item.value}
                      {item.unit ? ` ${item.unit}` : ""}
                    </strong>
                    <br />
                    <span className="source-gap-note" data-economic-indicator-trend={item.trendDirection}>
                      trend: {trendSymbol(item.trendDirection)}
                    </span>
                  </td>
                  <td>
                    <FreshnessDisclosure label="Period" value={item.period} state={item.freshnessState} />
                    <FreshnessDisclosure label="Retrieved" value={item.retrievedAt} state={item.freshnessState} />
                  </td>
                  <td>
                    <span>{item.source.publisher}</span>
                    <div className="compact-source-row">
                      <CompactCitationSources
                        citations={resolveCitationList(citations, item.citationIds)}
                        label={`${item.name} sources`}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
