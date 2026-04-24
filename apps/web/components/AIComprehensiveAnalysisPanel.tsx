import type { Citation, AIComprehensiveAnalysisFixture } from "../lib/fixtures";
import { CitationChip } from "./CitationChip";
import { FreshnessLabel } from "./FreshnessLabel";

type FreshnessState = "fresh" | "stale" | "unknown" | "unavailable" | "partial" | "insufficient_evidence";

type AIComprehensiveAnalysisPanelProps = {
  analysis: AIComprehensiveAnalysisFixture;
  citations: Citation[];
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

export function AIComprehensiveAnalysisPanel({ analysis, citations }: AIComprehensiveAnalysisPanelProps) {
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

  return (
    <section
      className="plain-panel recent-section"
      aria-labelledby="beginner-ai-comprehensive-analysis"
      data-beginner-stable-recent-separation="recent"
      data-beginner-ai-comprehensive-analysis
      data-timely-context-layer="ai-comprehensive-analysis"
      data-ai-analysis-state={analysis.state}
      data-ai-analysis-available={analysis.analysisAvailable ? "true" : "false"}
      data-ai-analysis-minimum-weekly-news-items={analysis.minimumWeeklyNewsItemCount}
      data-ai-analysis-weekly-news-selected-count={analysis.weeklyNewsSelectedItemCount}
      data-ai-analysis-threshold-state={
        analysis.weeklyNewsSelectedItemCount >= analysis.minimumWeeklyNewsItemCount ? "threshold_met" : "threshold_not_met"
      }
    >
      <div className="section-heading">
        <p className="eyebrow">Timely context</p>
        <h2 id="beginner-ai-comprehensive-analysis">AI Comprehensive Analysis</h2>
      </div>

      <div className="state-row">
        <FreshnessLabel
          label="Analysis availability"
          value={analysis.analysisAvailable ? "Available in deterministic fixture" : "Suppressed in deterministic fixture"}
          state={freshnessState}
        />
        <FreshnessLabel
          label="Evidence state"
          value={analysis.state}
          state={freshnessState}
        />
        <span className="state-pill" data-evidence-state={analysis.analysisAvailable ? "supported" : "insufficient_evidence"}>
          State: {analysis.state.replaceAll("_", " ")}
        </span>
        <span className="state-pill compact-state" data-ai-analysis-evidence-threshold>
          {analysis.weeklyNewsSelectedItemCount} of {analysis.minimumWeeklyNewsItemCount} high-signal items
        </span>
      </div>

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
              <span className="chip-row">
                {section.citationIds.map((citationId) => {
                  const citation = citations.find((entry) => entry.citationId === citationId);
                  return citation ? <CitationChip key={`${section.sectionId}-${citationId}`} citation={citation} /> : null;
                })}
              </span>
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
          <FreshnessLabel label="Canonical evidence" value={analysis.canonicalFactCitationIds.join(", ")} state={freshnessState} />
        </div>
      )}
    </section>
  );
}
