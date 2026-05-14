import type { Citation, AIComprehensiveAnalysisFixture } from "../lib/fixtures";
import { CompactCitationSources, resolveCitationList } from "./CompactCitationSources";
import { FreshnessDisclosure } from "./FreshnessLabel";
import { GenerationStateNote } from "./GenerationStateNote";

type FreshnessState = "fresh" | "stale" | "unknown" | "unavailable" | "partial" | "insufficient_evidence";

type AIComprehensiveAnalysisPanelProps = {
  analysis: AIComprehensiveAnalysisFixture;
  citations: Citation[];
  assetTicker?: string;
};

function stateToFreshness(state: AIComprehensiveAnalysisFixture["state"]): FreshnessState {
  if (state === "available") {
    return "fresh";
  }
  if (state === "suppressed" || state === "no_high_signal") {
    return "insufficient_evidence";
  }
  if (state === "unavailable") {
    return "unavailable";
  }
  return "unknown";
}

export function AIComprehensiveAnalysisPanel({ analysis, citations, assetTicker }: AIComprehensiveAnalysisPanelProps) {
  const requiredSectionOrder = [
    "What Changed This Week",
    "Market Context",
    "Business/Fund Context",
    "Risk Context"
  ] as const;
  const orderedSections = requiredSectionOrder
    .map((label) => analysis.sections.find((section) => section.label === label))
    .filter((section): section is (typeof analysis.sections)[number] => Boolean(section));
  const usesRequiredSectionOrder = orderedSections.length
    ? orderedSections.every((section, index) => section.label === requiredSectionOrder[index])
    : false;
  const sectionOrderState = usesRequiredSectionOrder
    ? "matched"
    : analysis.sections.length
      ? "mismatch"
      : "suppressed";
  const freshnessState = stateToFreshness(analysis.state);
  const shouldRenderSections = analysis.analysisAvailable && analysis.sections.length > 0;
  const sectionTitle = assetTicker ? `AI Comprehensive Analysis: ${assetTicker}` : "AI Comprehensive Analysis";
  const sectionState = analysis.sectionStates?.find((state) => state.sectionId === "ai_comprehensive_analysis") ?? null;

  return (
    <section
      className="plain-panel recent-section"
      aria-labelledby="beginner-ai-comprehensive-analysis"
      data-beginner-stable-recent-separation="recent"
      data-beginner-ai-comprehensive-analysis
      data-timely-context-layer="ai-comprehensive-analysis"
      data-ai-analysis-scope="ticker"
      data-ai-analysis-state={analysis.state}
      data-ai-analysis-available={analysis.analysisAvailable ? "true" : "false"}
      data-ai-analysis-minimum-weekly-news-items={analysis.minimumWeeklyNewsItemCount}
      data-ai-analysis-weekly-news-selected-count={analysis.weeklyNewsSelectedItemCount}
      data-ai-analysis-validation-reason-codes={analysis.validationReasonCodes.join(",") || "none"}
      data-ai-analysis-threshold-state={
        analysis.weeklyNewsSelectedItemCount >= analysis.minimumWeeklyNewsItemCount ? "threshold_met" : "threshold_not_met"
      }
    >
      <div className="section-heading-row">
        <div className="section-heading">
          <p className="eyebrow">Ticker-specific context</p>
          <h2 id="beginner-ai-comprehensive-analysis">{sectionTitle}</h2>
        </div>
        <div className="state-row">
          <span className="state-pill" data-evidence-state={analysis.analysisAvailable ? "supported" : "insufficient_evidence"}>
            State: {analysis.state.replaceAll("_", " ")}
          </span>
          <span className="state-pill compact-state" data-ai-analysis-evidence-threshold>
            {analysis.weeklyNewsSelectedItemCount} of {analysis.minimumWeeklyNewsItemCount} high-signal items
          </span>
        </div>
      </div>
      <div className="freshness-disclosure-row">
        <FreshnessDisclosure
          label="Analysis availability"
          value={analysis.analysisAvailable ? "Available in current evidence" : "Suppressed in current evidence"}
          state={freshnessState}
        />
        <FreshnessDisclosure
          label="Evidence state"
          value={analysis.state}
          state={freshnessState}
        />
      </div>
      <GenerationStateNote
        label="Ticker AI generation"
        diagnostics={analysis.generationDiagnostics}
        sectionState={sectionState}
        analysisAvailable={analysis.analysisAvailable}
      />

      {shouldRenderSections ? (
        <div
          className="section-stack"
          data-ai-analysis-section-count={analysis.sections.length}
          data-ai-analysis-required-order={sectionOrderState}
        >
          {orderedSections.map((section, index) => (
            <article
              className="timeline-item"
              key={section.sectionId}
              data-ai-analysis-section-id={section.sectionId}
              data-ai-analysis-section-order={index + 1}
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
                <div className="unknown-state" data-ai-analysis-uncertainty>
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
        <div className="unknown-state" data-ai-analysis-suppressed-reason={analysis.state}>
          <p>
            {analysis.suppressionReason ??
              "Insufficient evidence is shown instead of fabricated analysis when the local Weekly News Focus layer is too thin."}
          </p>
          <p className="source-gap-note">
            Analysis requires at least {analysis.minimumWeeklyNewsItemCount} high-signal Weekly News Focus items.
          </p>
          <div className="freshness-disclosure-row">
            <FreshnessDisclosure
              label="Canonical evidence"
              value={`${analysis.canonicalFactCitationIds.length} source${analysis.canonicalFactCitationIds.length === 1 ? "" : "s"} available`}
              state={freshnessState}
            />
          </div>
          <div className="compact-source-row">
            <CompactCitationSources
              citations={resolveCitationList(citations, analysis.canonicalFactCitationIds)}
              label="Canonical evidence sources"
            />
          </div>
        </div>
      )}
    </section>
  );
}
