"use client";

import { useMemo, useState } from "react";
import type { Citation, WeeklyNewsFocusFixture } from "../lib/fixtures";
import { CitationChip } from "./CitationChip";
import { FreshnessDisclosure } from "./FreshnessLabel";

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

type WeeklyNewsFilter = "all" | "news" | "press" | "filings";

const WEEKLY_NEWS_FILTERS: Array<{ id: WeeklyNewsFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "news", label: "News" },
  { id: "press", label: "Press Releases" },
  { id: "filings", label: "SEC Filings / Issuer Updates" }
];

export function WeeklyNewsPanel({ focus, citations }: WeeklyNewsPanelProps) {
  const [activeFilter, setActiveFilter] = useState<WeeklyNewsFilter>("all");
  const windowLabel = `${focus.window.newsWindowStart} to ${focus.window.newsWindowEnd}`;
  const emptyMessage = focus.emptyState?.message ?? "No major Weekly News Focus items found in the current local evidence window.";
  const emptyEvidenceState = evidenceStateToFreshnessFromFocus(focus.emptyState);
  const windowFreshness = stateToFreshness(focus.state);
  const itemCounts = useMemo(
    () =>
      WEEKLY_NEWS_FILTERS.reduce<Record<WeeklyNewsFilter, number>>(
        (counts, filter) => {
          counts[filter.id] = filter.id === "all" ? focus.items.length : focus.items.filter((item) => classifyWeeklyNewsItem(item) === filter.id).length;
          return counts;
        },
        { all: 0, news: 0, press: 0, filings: 0 }
      ),
    [focus.items]
  );
  const visibleItems = useMemo(
    () => focus.items.filter((item) => activeFilter === "all" || classifyWeeklyNewsItem(item) === activeFilter),
    [activeFilter, focus.items]
  );

  return (
    <section
      className="plain-panel recent-section"
      aria-labelledby="beginner-weekly-news-focus"
      data-beginner-stable-recent-separation="recent"
      data-beginner-weekly-news-focus
      data-beginner-recent-developments
      data-timely-context-layer="weekly-news-focus"
      data-weekly-news-state={focus.state}
      data-weekly-news-configured-max={focus.configuredMaxItemCount}
      data-weekly-news-selected-count={focus.selectedItemCount}
      data-weekly-news-suppressed-candidate-count={focus.suppressedCandidateCount}
      data-weekly-news-evidence-state={focus.evidenceState}
      data-weekly-news-evidence-limited-state={focus.evidenceLimitedState}
      data-weekly-news-empty-behavior={focus.selectedItemCount === 0 ? "explicit_empty_state" : "not_empty"}
      data-weekly-news-active-filter={activeFilter}
    >
      <div className="section-heading-row">
        <div className="section-heading">
          <p className="eyebrow">Timely context</p>
          <h2 id="beginner-weekly-news-focus">Weekly News Focus</h2>
        </div>
        <div className="state-row">
          <span className="state-pill compact-state" data-evidence-state={focus.evidenceState}>
            {focus.selectedItemCount} of {focus.configuredMaxItemCount} verified
          </span>
        </div>
      </div>

      <p className="notice-text">
        Weekly News Focus keeps recent developments separate from stable facts so short-term context does not redefine the
        asset.
      </p>
      <div className="freshness-disclosure-row">
        <FreshnessDisclosure label="News window" value={windowLabel} state={windowFreshness} />
        <FreshnessDisclosure label="Checked as of" value={focus.window.asOfDate} state={windowFreshness} />
      </div>

      {focus.items.length ? (
        <div className="section-stack" data-weekly-news-item-count={focus.items.length}>
          <div className="weekly-news-filter-tabs" role="tablist" aria-label="Weekly News source filter" data-weekly-news-filter-tabs>
            {WEEKLY_NEWS_FILTERS.map((filter) => (
              <button
                key={filter.id}
                type="button"
                role="tab"
                className="weekly-news-filter-tab"
                aria-selected={activeFilter === filter.id}
                onClick={() => setActiveFilter(filter.id)}
                data-weekly-news-filter-tab={filter.id}
                data-weekly-news-filter-count={itemCounts[filter.id]}
              >
                {filter.label}
              </button>
            ))}
          </div>
          {focus.evidenceLimitedState === "limited_verified_set" ? (
            <p className="source-gap-note" data-weekly-news-limited-verified-set>
              Weekly News Focus is showing a smaller verified set because only {focus.selectedItemCount} high-signal
              item{focus.selectedItemCount === 1 ? "" : "s"} passed the evidence rules.
            </p>
          ) : null}
          {visibleItems.length ? null : (
            <p className="source-gap-note" data-weekly-news-filter-empty>
              No selected items match this source filter.
            </p>
          )}
          {visibleItems.map((item) => (
            <article
              className="timeline-item"
              key={item.eventId}
              data-weekly-news-item-id={item.eventId}
              data-weekly-news-event-type={item.eventType}
              data-weekly-news-period-bucket={item.periodBucket}
              data-weekly-news-source-quality={item.source.sourceQuality}
              data-weekly-news-source-use-policy={item.source.sourceUsePolicy}
              data-weekly-news-allowlist-status={item.source.allowlistStatus}
              data-weekly-news-source-filter={classifyWeeklyNewsItem(item)}
              data-freshness-state={item.freshnessState}
            >
              <div className="etf-item-heading">
                <h3>{item.title}</h3>
                <span className="state-pill compact-state" data-evidence-state={focus.state}>
                  {item.eventType.replaceAll("_", " ")}
                </span>
              </div>
              <p>{item.summary}</p>
              <div className="freshness-disclosure-row">
                <FreshnessDisclosure
                  label={item.eventDate ? "Event date" : "Published or as of"}
                  value={item.eventDate ?? item.source.publishedAt ?? item.source.asOfDate ?? "Unknown in current evidence"}
                  state={item.freshnessState}
                />
                <FreshnessDisclosure label="Retrieved" value={item.source.retrievedAt} state={item.freshnessState} />
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
            {focus.emptyState ? (
              <span className="state-pill compact-state" data-evidence-state={focus.emptyState.state}>
                selected items: {focus.emptyState.selectedItemCount}
              </span>
            ) : null}
            <span className="state-pill compact-state" data-weekly-news-empty-suppressed-candidate-count={focus.suppressedCandidateCount}>
              suppressed candidates: {focus.suppressedCandidateCount}
            </span>
          </div>
          <div className="freshness-disclosure-row">
            <FreshnessDisclosure
              label="Empty-state evidence"
              value={focus.emptyState ? focus.emptyState.state : focus.state}
              state={emptyEvidenceState}
            />
          </div>
          <p className="source-gap-note">
            An empty Weekly News Focus state is normal when no major high-signal items pass the local evidence rules.
          </p>
        </div>
      )}
    </section>
  );
}

function classifyWeeklyNewsItem(item: WeeklyNewsFocusFixture["items"][number]): WeeklyNewsFilter {
  const sourceType = item.source.sourceType.toLowerCase();
  const eventType = item.eventType.toLowerCase();
  if (
    sourceType.includes("sec") ||
    sourceType.includes("filing") ||
    sourceType.includes("prospectus") ||
    sourceType.includes("fact_sheet") ||
    eventType === "methodology_change" ||
    eventType === "index_change" ||
    eventType === "fee_change" ||
    item.source.isOfficial
  ) {
    return "filings";
  }
  if (sourceType.includes("press") || sourceType.includes("investor_relations") || sourceType.includes("issuer")) {
    return "press";
  }
  return "news";
}
