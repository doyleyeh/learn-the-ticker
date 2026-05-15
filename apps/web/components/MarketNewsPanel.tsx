import type { Citation, MarketNewsFocusFixture, MarketNewsTopicBucket } from "../lib/fixtures";
import { CompactCitationSources, resolveCitationList } from "./CompactCitationSources";
import { SectionStateNote, type SectionStateForDisplay } from "./SectionStateNote";

type FreshnessState = "fresh" | "stale" | "unknown" | "unavailable" | "partial" | "insufficient_evidence";

type MarketNewsPanelProps = {
  focus: MarketNewsFocusFixture;
  citations: Citation[];
  sectionState?: SectionStateForDisplay | null;
};

function stateToFreshness(state: MarketNewsFocusFixture["state"]): FreshnessState {
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

function topicLabel(topic: MarketNewsTopicBucket) {
  return topic.replaceAll("_", " ");
}

function shortDate(value: string) {
  return value.slice(0, 10);
}

export function MarketNewsPanel({ focus, citations, sectionState }: MarketNewsPanelProps) {
  const windowLabel = `${focus.window.newsWindowStart} to ${focus.window.newsWindowEnd}`;
  const freshness = stateToFreshness(focus.state);
  const emptyMessage = focus.emptyState?.message ?? "No major Market News Focus items passed the evidence rules for this window.";
  const sectionMetadata = [
    { label: "News window", value: windowLabel, state: freshness },
    { label: "Checked as of", value: focus.window.asOfDate, state: freshness },
    { label: "Reusable context", value: focus.reusableAcrossTickers ? "Yes" : "No" },
    { label: "Live external calls", value: focus.noLiveExternalCalls ? "No" : "Yes" }
  ];

  return (
    <section
      className="plain-panel recent-section"
      aria-labelledby="beginner-market-news-focus"
      data-beginner-stable-recent-separation="recent"
      data-market-news-focus
      data-timely-context-layer="market-news-focus"
      data-market-news-state={focus.state}
      data-market-news-configured-max={focus.configuredMaxItemCount}
      data-market-news-selected-count={focus.selectedItemCount}
      data-market-news-reusable-across-tickers={focus.reusableAcrossTickers ? "true" : "false"}
      data-market-news-evidence-limited-state={focus.evidenceLimitedState}
      data-market-news-empty-behavior={focus.selectedItemCount === 0 ? "explicit_empty_state" : "not_empty"}
    >
      <div className="section-heading-row">
        <div className="section-heading">
          <p className="eyebrow">Market-wide context</p>
          <h2 id="beginner-market-news-focus">Market News Focus</h2>
        </div>
        <div className="state-row">
          <span className="state-pill compact-state" data-evidence-state={focus.evidenceState}>
            {focus.selectedItemCount} of {focus.configuredMaxItemCount} verified
          </span>
          <CompactCitationSources
            citations={focus.citations}
            label="Market News Focus evidence details"
            metadataRows={sectionMetadata}
            dashboardSourceIcon
          />
        </div>
      </div>

      <SectionStateNote state={sectionState} />
      <p className="notice-text">
        Market News Focus gives broad U.S. and global financial context before the ticker-specific weekly section.
      </p>

      {focus.items.length ? (
        <div className="section-stack" data-market-news-item-count={focus.items.length}>
          {focus.evidenceLimitedState === "limited_verified_set" ? (
            <p className="source-gap-note" data-market-news-limited-verified-set>
              Showing a smaller verified set because only {focus.selectedItemCount} market-wide item
              {focus.selectedItemCount === 1 ? "" : "s"} passed the source-use rules.
            </p>
          ) : null}
          {focus.items.map((item) => (
            <article
              className="timeline-item"
              key={item.storyId}
              data-market-news-story-id={item.storyId}
              data-market-news-topic-bucket={item.topicBucket}
              data-market-news-source-quality={item.source.sourceQuality}
              data-market-news-source-use-policy={item.source.sourceUsePolicy}
              data-market-news-critical-claim={item.cluster.criticalClaim ? "true" : "false"}
              data-market-news-corroborated={item.cluster.corroborated ? "true" : "false"}
            >
              <div className="etf-item-heading">
                <h3>
                  [{item.source.publisher}] {item.title} ({shortDate(item.publishedAt)})
                </h3>
                <span className="state-pill compact-state" data-evidence-state={focus.state}>
                  {topicLabel(item.topicBucket)}
                </span>
              </div>
              <p>{item.summary}</p>
              <div className="compact-source-row">
                <CompactCitationSources
                  citations={resolveCitationList(citations, item.citationIds)}
                  label="Market news sources"
                  metadataRows={[
                    { label: "Published", value: shortDate(item.publishedAt), state: item.freshnessState },
                    { label: "Retrieved", value: item.source.retrievedAt, state: item.freshnessState },
                    { label: "Source quality", value: item.source.sourceQuality },
                    { label: "Allowlist", value: item.source.allowlistStatus },
                    { label: "Source-use policy", value: item.source.sourceUsePolicy },
                    { label: "Supporting sources", value: item.cluster.supportingSources.join(", ") }
                  ]}
                />
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="unknown-state" data-market-news-empty-state={focus.emptyState?.state ?? focus.state}>
          <p>{emptyMessage}</p>
          <div className="state-row">
            <span className="state-pill compact-state" data-market-news-empty-suppressed-candidate-count={focus.suppressedCandidateCount}>
              suppressed candidates: {focus.suppressedCandidateCount}
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
