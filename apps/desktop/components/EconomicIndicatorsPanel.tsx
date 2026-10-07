import type { Citation, EconomicIndicatorsPackFixture } from "../lib/fixtures";
import { CompactCitationSources, resolveCitationList } from "./CompactCitationSources";

type EconomicIndicatorsPanelProps = {
  pack: EconomicIndicatorsPackFixture;
  citations: Citation[];
  sectionState?: EconomicIndicatorsSectionState;
};

type EconomicIndicatorsSectionState = {
  rendering: string;
  evidenceState: string;
  reason: string;
  message: string;
  dataOrigin: string;
  sectionStatus: string;
  fallbackReason: string | null;
  freshnessState: string | null;
  sourceHandoffState: string;
  cacheState: string | null;
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

export function EconomicIndicatorsPanel({ pack, citations, sectionState }: EconomicIndicatorsPanelProps) {
  const officialCount = pack.items.filter((item) => item.category === "official_historical_actual").length;
  const marketReferenceCount = pack.items.length - officialCount;
  const sourceStateCopy = economicIndicatorsSourceStateCopy(pack, sectionState);
  const sectionMetadata = [
    { label: "Indicator pack as of", value: pack.asOfDate, state: "fresh" },
    { label: "Imported pack fresh until", value: pack.analysisPackMetadata?.freshnessExpiresAt ?? null, state: "fresh" },
    { label: "Analysis source", value: pack.analysisPackMetadata?.analysisSource ?? "deterministic_fixture" },
    { label: "Live external calls", value: pack.noLiveExternalCalls ? "No" : "Yes" }
  ];

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
      data-economic-indicators-section-rendering={sectionState?.rendering ?? "unknown"}
      data-economic-indicators-section-data-origin={sectionState?.dataOrigin ?? "unknown"}
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
          <CompactCitationSources
            citations={pack.citations}
            label="Economic Indicators evidence details"
            metadataRows={sectionMetadata}
            dashboardSourceIcon
          />
        </div>
      </div>

      <p className="notice-text">
        Economic Indicators are shared context for learning and stay separate from the asset's own source-backed facts.
      </p>
      <p
        className="source-gap-note"
        data-economic-indicators-inline-source-state
        data-economic-indicators-source-state={sectionState?.rendering ?? "unknown"}
        data-economic-indicators-data-origin={sectionState?.dataOrigin ?? "unknown"}
      >
        {sourceStateCopy}
      </p>

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
                    <span>{item.source.publisher}</span>
                    <div className="compact-source-row">
                      <CompactCitationSources
                        citations={resolveCitationList(citations, item.citationIds)}
                        label={`${item.name} sources`}
                        metadataRows={[
                          { label: "Period", value: item.period, state: item.freshnessState },
                          { label: "As of", value: item.asOfDate, state: item.freshnessState },
                          { label: "Retrieved", value: item.retrievedAt, state: item.freshnessState },
                          { label: "Source quality", value: item.source.sourceQuality },
                          { label: "Source-use policy", value: item.source.sourceUsePolicy }
                        ]}
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

function economicIndicatorsSourceStateCopy(
  pack: EconomicIndicatorsPackFixture,
  sectionState: EconomicIndicatorsSectionState | undefined
) {
  if (pack.analysisPackMetadata?.analysisSource === "imported_local_pack") {
    return "Imported analysis-pack evidence is loaded for this U.S. context section.";
  }
  if (pack.analysisPackMetadata?.analysisSource === "backend_generated" || pack.noLiveExternalCalls === false) {
    return "Live local official and market-reference indicator evidence is loaded for this U.S. context section.";
  }
  if (sectionState?.dataOrigin === "deterministic_fixture" || pack.analysisPackMetadata?.analysisSource === "deterministic_fixture") {
    return "Deterministic fixture indicators are shown for this render because live indicator evidence is disabled or unavailable.";
  }
  if (sectionState?.rendering === "source_labeled_live") {
    return "Source-labeled local indicator evidence is loaded for this U.S. context section.";
  }
  if (sectionState?.rendering === "backend_contract") {
    return "Backend indicator evidence is loaded for this U.S. context section.";
  }
  return "Indicator source state is shown inline with this section.";
}
