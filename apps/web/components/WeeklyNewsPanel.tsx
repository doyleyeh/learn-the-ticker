import type { Citation, WeeklyNewsFocusFixture } from "../lib/fixtures";
import { CompactCitationSources, resolveCitationList } from "./CompactCitationSources";
import { SectionStateNote, type SectionStateForDisplay } from "./SectionStateNote";

type FreshnessState = "fresh" | "stale" | "unknown" | "unavailable" | "partial" | "insufficient_evidence";

function stateToFreshness(state: WeeklyNewsFocusFixture["state"]): FreshnessState {
  if (state === "available") {
    return "fresh";
  }
  if (state === "suppressed" || state === "no_high_signal") {
    return "insufficient_evidence";
  }
  if (state === "insufficient_evidence") {
    return "insufficient_evidence";
  }
  if (state === "unavailable") {
    return "unavailable";
  }
  return "unknown";
}

function evidenceStateToFreshnessFromFocus(
  emptyState: WeeklyNewsFocusFixture["emptyState"]
): FreshnessState {
  if (!emptyState) {
    return "unknown";
  }
  if (emptyState.evidenceState === "supported" || emptyState.evidenceState === "mixed") {
    return "fresh";
  }
  if (emptyState.evidenceState === "stale") {
    return "stale";
  }
  if (emptyState.evidenceState === "no_high_signal" || emptyState.evidenceState === "no_major_recent_development") {
    return "insufficient_evidence";
  }
  if (emptyState.evidenceState === "insufficient_evidence") {
    return "insufficient_evidence";
  }
  if (emptyState.evidenceState === "unavailable") {
    return "unavailable";
  }
  return "unknown";
}

type WeeklyNewsPanelProps = {
  focus: WeeklyNewsFocusFixture;
  citations: Citation[];
  assetTicker?: string;
  sectionState?: SectionStateForDisplay | null;
};

export function WeeklyNewsPanel({ focus, citations, assetTicker, sectionState }: WeeklyNewsPanelProps) {
  const windowLabel = `${focus.window.newsWindowStart} to ${focus.window.newsWindowEnd}`;
  const emptyMessage = focus.emptyState?.message ?? "No major Weekly News Focus items found in the current local evidence window.";
  const emptyEvidenceState = evidenceStateToFreshnessFromFocus(focus.emptyState);
  const windowFreshness = stateToFreshness(focus.state);
  const sectionTitle = assetTicker ? `Weekly News Focus: ${assetTicker}` : "Weekly News Focus";
  const sectionMetadata = [
    { label: "News window", value: windowLabel, state: windowFreshness },
    { label: "Checked as of", value: focus.window.asOfDate, state: windowFreshness },
    { label: "Empty-state evidence", value: focus.emptyState ? focus.emptyState.state : null, state: emptyEvidenceState },
    { label: "Live external calls", value: focus.noLiveExternalCalls ? "No" : "Yes" }
  ];

  return (
    <section
      className="plain-panel recent-section"
      aria-labelledby="beginner-weekly-news-focus"
      data-beginner-stable-recent-separation="recent"
      data-beginner-weekly-news-focus
      data-beginner-recent-developments
      data-timely-context-layer="weekly-news-focus"
      data-weekly-news-scope="ticker"
      data-weekly-news-state={focus.state}
      data-weekly-news-configured-max={focus.configuredMaxItemCount}
      data-weekly-news-selected-count={focus.selectedItemCount}
      data-weekly-news-suppressed-candidate-count={focus.suppressedCandidateCount}
      data-weekly-news-evidence-state={focus.evidenceState}
      data-weekly-news-evidence-limited-state={focus.evidenceLimitedState}
      data-weekly-news-empty-behavior={focus.selectedItemCount === 0 ? "explicit_empty_state" : "not_empty"}
    >
      <div className="section-heading-row">
        <div className="section-heading">
          <p className="eyebrow">Ticker-specific context</p>
          <h2 id="beginner-weekly-news-focus">{sectionTitle}</h2>
        </div>
        <div className="state-row">
          <span className="state-pill compact-state" data-evidence-state={focus.evidenceState}>
            {focus.selectedItemCount} of {focus.configuredMaxItemCount} verified
          </span>
          <CompactCitationSources
            citations={focus.citations}
            label="Weekly News Focus evidence details"
            metadataRows={sectionMetadata}
            dashboardSourceIcon
          />
        </div>
      </div>

      <SectionStateNote state={sectionState} weeklyNewsFailureNotice />
      <p className="notice-text">
        Weekly News Focus keeps recent developments separate from stable facts so short-term context does not redefine the
        asset.
      </p>

      {focus.items.length ? (
        <div className="section-stack" data-weekly-news-item-count={focus.items.length}>
          {focus.evidenceLimitedState === "limited_verified_set" ? (
            <p className="source-gap-note" data-weekly-news-limited-verified-set>
              Weekly News Focus is showing a smaller verified set because only {focus.selectedItemCount} high-signal
              item{focus.selectedItemCount === 1 ? "" : "s"} passed the evidence rules.
            </p>
          ) : null}
          {focus.items.map((item) => (
            <article
              className="timeline-item"
              key={item.eventId}
              data-weekly-news-item-id={item.eventId}
              data-weekly-news-event-type={item.eventType}
              data-weekly-news-period-bucket={item.periodBucket}
              data-weekly-news-source-quality={item.source.sourceQuality}
              data-weekly-news-source-use-policy={item.source.sourceUsePolicy}
              data-weekly-news-allowlist-status={item.source.allowlistStatus}
              data-freshness-state={item.freshnessState}
            >
              <div className="etf-item-heading">
                <h3>{item.title}</h3>
                <span className="state-pill compact-state" data-evidence-state={focus.state}>
                  {item.eventType.replaceAll("_", " ")}
                </span>
              </div>
              <p>{item.summary}</p>
              <div className="compact-source-row">
                <CompactCitationSources
                  citations={resolveCitationList(citations, item.citationIds)}
                  label="News sources"
                  metadataRows={[
                    {
                      label: item.eventDate ? "Event date" : "Published or as of",
                      value: item.eventDate ?? item.source.publishedAt ?? item.source.asOfDate ?? "Unknown in current evidence",
                      state: item.freshnessState
                    },
                    { label: "Retrieved", value: item.source.retrievedAt, state: item.freshnessState },
                    { label: "Source quality", value: item.source.sourceQuality },
                    { label: "Allowlist", value: item.source.allowlistStatus },
                    { label: "Source-use policy", value: item.source.sourceUsePolicy },
                    { label: "Source", value: item.source.publisher }
                  ]}
                />
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="unknown-state" data-weekly-news-empty-state={focus.emptyState?.state ?? focus.state}>
          <p>{emptyMessage}</p>
          <div className="state-row">
            {focus.emptyState ? (
              <span className="state-pill compact-state" data-evidence-state={focus.emptyState.state}>
                selected items: {focus.emptyState.selectedItemCount}
              </span>
            ) : null}
            <span className="state-pill compact-state" data-weekly-news-empty-suppressed-candidate-count={focus.suppressedCandidateCount}>
              suppressed candidates: {focus.suppressedCandidateCount}
            </span>
          </div>
          <p className="source-gap-note">
            An empty Weekly News Focus state is normal when no major high-signal items pass the local evidence rules.
          </p>
        </div>
      )}
    </section>
  );
}
