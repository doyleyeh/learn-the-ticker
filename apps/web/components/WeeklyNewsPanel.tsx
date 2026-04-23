import type { Citation, WeeklyNewsFocusFixture } from "../lib/fixtures";
import { CitationChip } from "./CitationChip";
import { FreshnessLabel } from "./FreshnessLabel";

type WeeklyNewsPanelProps = {
  focus: WeeklyNewsFocusFixture;
  citations: Citation[];
};

export function WeeklyNewsPanel({ focus, citations }: WeeklyNewsPanelProps) {
  const windowLabel = `${focus.window.newsWindowStart} to ${focus.window.newsWindowEnd}`;
  const emptyMessage = focus.emptyState?.message ?? "No major Weekly News Focus items found in the deterministic local fixture window.";

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
        <FreshnessLabel label="News window" value={windowLabel} state="fresh" />
        <FreshnessLabel label="Checked as of" value={focus.window.asOfDate} state="fresh" />
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
          <p className="source-gap-note">
            An empty Weekly News Focus state is normal when no major high-signal items pass the local evidence rules.
          </p>
        </div>
      )}
    </section>
  );
}
