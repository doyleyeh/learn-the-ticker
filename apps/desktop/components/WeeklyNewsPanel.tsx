import type { Citation, WeeklyNewsFocusFixture } from "../lib/fixtures";
import { CitationChip } from "./CitationChip";
import { FreshnessLabel } from "./FreshnessLabel";

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
};

export function WeeklyNewsPanel({ focus, citations }: WeeklyNewsPanelProps) {
  const windowLabel = `${focus.window.newsWindowStart} to ${focus.window.newsWindowEnd}`;
  const emptyMessage = focus.emptyState?.message ?? "No major Weekly News Focus items found in the deterministic local fixture window.";
  const emptyEvidenceState = evidenceStateToFreshnessFromFocus(focus.emptyState);
  const windowFreshness = stateToFreshness(focus.state);

  return (
    <section
      className="plain-panel recent-section"
      aria-labelledby="beginner-weekly-news-focus"
      data-beginner-stable-recent-separation="recent"
      data-beginner-weekly-news-focus
      data-beginner-recent-developments
      data-timely-context-layer="weekly-news-focus"
      data-weekly-news-state={focus.state}
    >
      <div className="section-heading">
        <p className="eyebrow">Timely context</p>
        <h2 id="beginner-weekly-news-focus">Weekly News Focus</h2>
      </div>

      <div className="state-row">
        <FreshnessLabel label="News window" value={windowLabel} state={windowFreshness} />
        <FreshnessLabel label="Checked as of" value={focus.window.asOfDate} state={windowFreshness} />
      </div>

      <p className="notice-text">
        Weekly News Focus keeps recent developments separate from stable facts so short-term context does not redefine the
        asset.
      </p>

      {focus.items.length ? (
        <div className="section-stack" data-weekly-news-item-count={focus.items.length}>
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
              <div className="state-row">
                <FreshnessLabel
                  label={item.eventDate ? "Event date" : "Published or as of"}
                  value={item.eventDate ?? item.source.publishedAt ?? item.source.asOfDate ?? "Unknown in local fixture"}
                  state={item.freshnessState}
                />
                <FreshnessLabel label="Retrieved" value={item.source.retrievedAt} state={item.freshnessState} />
              </div>
              <p className="source-gap-note">
                Source quality: {item.source.sourceQuality}. Allowlist: {item.source.allowlistStatus}. Source-use policy:{" "}
                {item.source.sourceUsePolicy}. Source: {item.source.publisher}.
              </p>
              <span className="chip-row">
                {item.citationIds.map((citationId) => {
                  const citation = citations.find((entry) => entry.citationId === citationId);
                  return citation ? <CitationChip key={citationId} citation={citation} /> : null;
                })}
              </span>
            </article>
          ))}
        </div>
      ) : (
        <div className="unknown-state" data-weekly-news-empty-state={focus.emptyState?.state ?? focus.state}>
          <p>{emptyMessage}</p>
          <div className="state-row">
            <FreshnessLabel
              label="Empty-state evidence"
              value={focus.emptyState ? focus.emptyState.state : focus.state}
              state={emptyEvidenceState}
            />
            {focus.emptyState ? (
              <span className="state-pill compact-state" data-evidence-state={focus.emptyState.state}>
                selected items: {focus.emptyState.selectedItemCount}
              </span>
            ) : null}
          </div>
          <p className="source-gap-note">
            An empty Weekly News Focus state is normal when no major high-signal items pass the local evidence rules.
          </p>
        </div>
      )}
    </section>
  );
}
