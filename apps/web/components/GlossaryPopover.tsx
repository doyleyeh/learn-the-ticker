"use client";

import { useId, useRef, useState } from "react";
import { type AssetGlossaryContext } from "../lib/assetGlossary";
import { getGlossaryTerm } from "../lib/glossary";
import { buildTrustMetricSurfaceDescriptor } from "../lib/trustMetrics";

type GlossaryPopoverProps = {
  term: string;
  assetContext?: AssetGlossaryContext;
};

export function GlossaryPopover({ term, assetContext }: GlossaryPopoverProps) {
  const [open, setOpen] = useState(false);
  const [pinned, setPinned] = useState(false);
  const entry = getGlossaryTerm(term);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const componentId = useId().replace(/[^a-z0-9]+/gi, "-");
  const termId = term.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "unavailable";
  const safeId = `glossary-${termId}-${componentId}`;
  const displayTerm = entry?.term ?? term;
  const trustMetricDescriptor = buildTrustMetricSurfaceDescriptor({
    eventType: "glossary_usage",
    workflowArea: "glossary",
    selectedSection: termId,
    citationCount: assetContext?.citationIds.length ?? 0,
    sourceDocumentCount: assetContext?.sourceReferences.length ?? 0,
    freshnessState: assetContext?.freshnessState ?? "unknown",
    evidenceState: assetContext?.evidenceState ?? "insufficient_evidence"
  });
  const closeGlossary = () => {
    setOpen(false);
    setPinned(false);
  };
  const togglePinnedGlossary = () => {
    const nextPinned = !pinned;
    setPinned(nextPinned);
    setOpen(nextPinned);
  };

  return (
    <span
      className="glossary-wrap"
      data-glossary-term={term}
      data-glossary-available={entry ? "true" : "false"}
      data-glossary-asset-context={assetContext ? assetContext.availabilityState : "generic_only"}
      data-trust-metric-schema-version={trustMetricDescriptor.schemaVersion}
      data-trust-metric-mode={trustMetricDescriptor.mode}
      data-trust-metric-event={trustMetricDescriptor.eventType}
      data-trust-metric-workflow-area={trustMetricDescriptor.workflowArea}
      data-trust-metric-occurred-at={trustMetricDescriptor.occurredAt}
      data-trust-metric-persistence={trustMetricDescriptor.persistence}
      data-trust-metric-external-analytics={trustMetricDescriptor.externalAnalytics}
      data-trust-metric-live-external-calls={trustMetricDescriptor.liveExternalCalls}
      data-trust-metric-selected-section={trustMetricDescriptor.selectedSection}
      data-trust-metric-citation-count={trustMetricDescriptor.citationCount}
      data-trust-metric-source-document-count={trustMetricDescriptor.sourceDocumentCount}
      data-trust-metric-freshness-state={trustMetricDescriptor.freshnessState}
      data-trust-metric-evidence-state={trustMetricDescriptor.evidenceState}
      data-glossary-desktop-interaction="hover-click-focus-escape"
      data-glossary-mobile-presentation="bottom-sheet"
      data-glossary-close-control="button"
      data-glossary-pinned={pinned ? "true" : "false"}
      onMouseEnter={() => {
        if (!pinned) {
          setOpen(true);
        }
      }}
      onMouseLeave={() => {
        if (!pinned) {
          setOpen(false);
        }
      }}
      onFocus={() => setOpen(true)}
      onBlur={(event) => {
        if (!pinned && !event.currentTarget.contains(event.relatedTarget)) {
          setOpen(false);
        }
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.stopPropagation();
          closeGlossary();
          triggerRef.current?.focus();
        }
      }}
    >
      <button
        ref={triggerRef}
        className="glossary-trigger"
        type="button"
        aria-expanded={open}
        aria-controls={safeId}
        aria-label={`Open glossary definition for ${displayTerm}`}
        data-glossary-trigger-mode="hover-click-focus"
        onClick={togglePinnedGlossary}
      >
        {displayTerm}
      </button>
      {open ? (
        <span
          className="glossary-popover"
          id={safeId}
          role="dialog"
          aria-label={`Glossary card for ${displayTerm}`}
          data-glossary-term={displayTerm}
          data-glossary-category={entry?.category ?? "unavailable"}
          data-glossary-asset-context={assetContext ? assetContext.availabilityState : "generic_only"}
          data-glossary-evidence-state={assetContext?.evidenceState ?? "insufficient_evidence"}
          data-glossary-freshness-state={assetContext?.freshnessState ?? "unknown"}
          data-glossary-bottom-sheet-height="min(74vh, 620px)"
          data-glossary-internal-scroll="true"
        >
          <span className="glossary-card-header">
            <span className="glossary-card-title" data-glossary-visible-term-context>
              {displayTerm}
            </span>
            <button
              className="glossary-close-button"
              type="button"
              aria-label={`Close glossary card for ${displayTerm}`}
              onClick={() => {
                closeGlossary();
                triggerRef.current?.focus();
              }}
            >
              Close
            </button>
          </span>
          {entry ? (
            <>
              <span className="glossary-category" data-glossary-category={entry.category}>
                {entry.category}
              </span>
              <strong data-glossary-definition>{entry.definition}</strong>
              <span data-glossary-why-it-matters>{entry.whyItMatters}</span>
              <small data-glossary-beginner-mistake>{entry.beginnerMistake}</small>
              {assetContext ? (
                <>
                  <span data-glossary-asset-context-note>
                    {assetContext.contextNote ??
                      "Backend glossary context is available only inside this glossary card and does not support claims outside this area."}
                  </span>
                  <small data-glossary-asset-context-boundary>
                    Asset context: {assetContext.availabilityState}; evidence: {assetContext.evidenceState}; freshness:{" "}
                    {assetContext.freshnessState}.
                  </small>
                  {assetContext.citationIds.length > 0 ? (
                    <small data-glossary-asset-citation-ids={assetContext.citationIds.join(",")}>
                      Citations: {assetContext.citationIds.join(", ")}
                    </small>
                  ) : null}
                  {assetContext.uncertaintyLabels.length > 0 ? (
                    <small data-glossary-uncertainty-labels={assetContext.uncertaintyLabels.join(",")}>
                      Uncertainty: {assetContext.uncertaintyLabels.join(", ")}
                    </small>
                  ) : null}
                  {assetContext.sourceReferences.length > 0 ? (
                    <span data-glossary-source-references>
                      {assetContext.sourceReferences.map((source) => (
                        <small
                          key={source.sourceDocumentId}
                          data-glossary-source-document-id={source.sourceDocumentId}
                          data-glossary-source-use-policy={source.sourceUsePolicy}
                          data-glossary-source-freshness={source.freshnessState}
                        >
                          Source: {source.title} ({source.publisher}; {source.sourceUsePolicy}; retrieved{" "}
                          {source.retrievedAt})
                        </small>
                      ))}
                    </span>
                  ) : null}
                  {assetContext.suppressionReasons.length > 0 ? (
                    <small data-glossary-suppression-reasons={assetContext.suppressionReasons.join(",")}>
                      Limits: {assetContext.suppressionReasons.join(", ")}
                    </small>
                  ) : null}
                </>
              ) : (
                <small data-glossary-generic-only-label>
                  Generic-only definition; no asset-specific glossary context is shown.
                </small>
              )}
            </>
          ) : (
            <>
              <span className="glossary-category" data-glossary-category="unavailable">
                Unavailable
              </span>
              <strong data-glossary-definition>Definition unavailable for this glossary term.</strong>
              <span data-glossary-why-it-matters>No local glossary entry is available.</span>
              <small data-glossary-beginner-mistake>No beginner mistake is shown without a curated entry.</small>
            </>
          )}
        </span>
      ) : null}
    </span>
  );
}
