import type { Citation, MarketAIComprehensiveAnalysisFixture } from "../lib/fixtures";
import { CompactCitationSources, resolveCitationList } from "./CompactCitationSources";
import { FreshnessDisclosure } from "./FreshnessLabel";

type FreshnessState = "fresh" | "stale" | "unknown" | "unavailable" | "partial" | "insufficient_evidence";

type MarketAIComprehensiveAnalysisPanelProps = {
  analysis: MarketAIComprehensiveAnalysisFixture;
  citations: Citation[];
};

function stateToFreshness(state: MarketAIComprehensiveAnalysisFixture["state"]): FreshnessState {
  if (state === "available") {
    return "fresh";
  }
  if (state === "suppressed" || state === "no_high_signal" || state === "insufficient_evidence") {
    return "insufficient_evidence";
  }
  if (state === "unavailable") {
    return "unavailable";
  }
  return "unknown";
}

export function MarketAIComprehensiveAnalysisPanel({
  analysis,
  citations
}: MarketAIComprehensiveAnalysisPanelProps) {
  const requiredSectionOrder = [
    "What Changed This Week",
    "Macro & Policy",
    "Equity Market Drivers",
    "AI / Technology / Semiconductors",
    "Geopolitical & Energy Risks",
    "Credit / Liquidity / Sentiment",
    "Scenario Lens",
    "Practical Watchpoints"
  ] as const;
  const orderedSections = requiredSectionOrder
    .map((label) => analysis.sections.find((section) => section.label === label))
    .filter((section): section is (typeof analysis.sections)[number] => Boolean(section));
  const sectionOrderState = orderedSections.length === requiredSectionOrder.length ? "matched" : analysis.sections.length ? "mismatch" : "suppressed";
  const freshnessState = stateToFreshness(analysis.state);
  const shouldRenderSections = analysis.analysisAvailable && analysis.sections.length > 0;

  return (
    <section
      className="plain-panel recent-section"
      aria-labelledby="beginner-market-ai-comprehensive-analysis"
      data-beginner-stable-recent-separation="recent"
      data-market-ai-comprehensive-analysis
      data-timely-context-layer="market-ai-comprehensive-analysis"
      data-market-ai-analysis-state={analysis.state}
      data-market-ai-analysis-available={analysis.analysisAvailable ? "true" : "false"}
      data-market-ai-analysis-minimum-market-news-items={analysis.minimumMarketNewsItemCount}
      data-market-ai-analysis-selected-topic-buckets={analysis.selectedTopicBucketCount}
    >
      <div className="section-heading-row">
        <div className="section-heading">
          <p className="eyebrow">Market-wide context</p>
          <h2 id="beginner-market-ai-comprehensive-analysis">AI Comprehensive Analysis: Market News Focus</h2>
        </div>
        <div className="state-row">
          <span className="state-pill" data-evidence-state={analysis.analysisAvailable ? "supported" : "insufficient_evidence"}>
            State: {analysis.state.replaceAll("_", " ")}
          </span>
          <span className="state-pill compact-state" data-market-ai-analysis-evidence-threshold>
            {analysis.marketNewsSelectedItemCount} market items
          </span>
        </div>
      </div>
      <div className="freshness-disclosure-row">
        <FreshnessDisclosure
          label="Analysis availability"
          value={analysis.analysisAvailable ? "Available in current evidence" : "Suppressed in current evidence"}
          state={freshnessState}
        />
        <FreshnessDisclosure label="Topic buckets" value={`${analysis.selectedTopicBucketCount} covered`} state={freshnessState} />
      </div>

      {shouldRenderSections ? (
        <div
          className="section-stack"
          data-market-ai-analysis-section-count={analysis.sections.length}
          data-market-ai-analysis-required-order={sectionOrderState}
        >
          {orderedSections.map((section, index) => (
            <article
              className="timeline-item"
              key={section.sectionId}
              data-market-ai-analysis-section-id={section.sectionId}
              data-market-ai-analysis-section-order={index + 1}
            >
              <h3>{section.label}</h3>
              <p>{section.analysis}</p>
              {section.bullets.length ? (
                <ul>
                  {section.bullets.map((bullet) => (
                    <li key={bullet}>{bullet}</li>
                  ))}
                </ul>
              ) : null}
              {section.uncertainty.length ? (
                <div className="unknown-state" data-market-ai-analysis-uncertainty>
                  <p className="source-gap-note">Uncertainty: {section.uncertainty.join(" ")}</p>
                </div>
              ) : null}
              <div className="compact-source-row">
                <CompactCitationSources
                  citations={resolveCitationList(citations, section.citationIds)}
                  label={`${section.label} sources`}
                />
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="unknown-state" data-market-ai-analysis-suppressed-reason={analysis.state}>
          <p>
            {analysis.suppressionReason ??
              "Insufficient evidence is shown instead of fabricated market analysis when the selected market-news layer is too thin."}
          </p>
          <p className="source-gap-note">
            Analysis requires at least {analysis.minimumMarketNewsItemCount} approved Market News Focus items across{" "}
            {analysis.minimumTopicBucketCount} topic buckets.
          </p>
        </div>
      )}
    </section>
  );
}
