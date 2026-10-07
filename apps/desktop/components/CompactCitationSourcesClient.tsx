"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { CompactCitationSourceGroup, EvidenceMetadataRow } from "./CompactCitationSources";

type CompactCitationSourcesClientProps = {
  className: string;
  dashboardSourceIcon: boolean;
  label: string;
  metadataLabel: string;
  metadataRows: EvidenceMetadataRow[];
  showCount: boolean;
  sourceCount: number;
  sourceGroups: CompactCitationSourceGroup[];
  summaryLabel?: string;
  title: string;
  triggerLabel: string;
};

export function CompactCitationSourcesClient({
  className,
  dashboardSourceIcon,
  label,
  metadataLabel,
  metadataRows,
  showCount,
  sourceCount,
  sourceGroups,
  summaryLabel,
  title,
  triggerLabel
}: CompactCitationSourcesClientProps) {
  const [open, setOpen] = useState(false);
  const detailsRef = useRef<HTMLDetailsElement | null>(null);
  const setPopoverOpen = useCallback((nextOpen: boolean) => {
    if (detailsRef.current) {
      detailsRef.current.open = nextOpen;
    }
    setOpen(nextOpen);
  }, []);

  useEffect(() => {
    function closeFromOutsideClick(event: PointerEvent) {
      if (!detailsRef.current?.open) {
        return;
      }
      const target = event.target;
      if (target instanceof Node && detailsRef.current?.contains(target)) {
        return;
      }
      setPopoverOpen(false);
    }

    function closeFromEscape(event: KeyboardEvent) {
      if (event.key === "Escape" && detailsRef.current?.open) {
        setPopoverOpen(false);
      }
    }

    document.addEventListener("pointerdown", closeFromOutsideClick, true);
    document.addEventListener("keydown", closeFromEscape);
    return () => {
      document.removeEventListener("pointerdown", closeFromOutsideClick, true);
      document.removeEventListener("keydown", closeFromEscape);
    };
  }, [setPopoverOpen]);

  return (
    <details
      ref={detailsRef}
      className={className}
      data-compact-citation-sources
      data-compact-citation-dismissible="outside-click-escape-close-button"
      data-compact-citation-source-count={sourceCount}
      data-compact-citation-metadata-count={metadataRows.length}
      data-dashboard-source-icon={dashboardSourceIcon ? "true" : undefined}
      onToggle={(event) => setOpen(event.currentTarget.open)}
      open={open}
      title={title}
    >
      <summary
        aria-expanded={open}
        aria-label={triggerLabel}
        onClick={(event) => {
          event.preventDefault();
          setPopoverOpen(!(detailsRef.current?.open ?? open));
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setPopoverOpen(false);
          } else if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            setPopoverOpen(!(detailsRef.current?.open ?? open));
          }
        }}
        tabIndex={0}
      >
        {summaryLabel ? (
          <span className="source-icon-label">{summaryLabel}</span>
        ) : (
          <span className="source-icon-symbol" aria-hidden="true">i</span>
        )}
        {showCount && sourceCount > 1 ? <span className="source-icon-count">{sourceCount}</span> : null}
      </summary>
      <span className="source-icon-popover compact-citation-popover" role="dialog" aria-label={label}>
        <span className="compact-citation-popover-header">
          <span className="compact-citation-popover-title">
            {sourceCount} source{sourceCount === 1 ? "" : "s"}
            {metadataRows.length ? `, ${metadataLabel}` : ""}
          </span>
          <button
            className="compact-citation-close"
            type="button"
            aria-label={`Close ${label}`}
            data-compact-citation-close-control="button"
            onClick={() => setPopoverOpen(false)}
          >
            X
          </button>
        </span>
        {sourceGroups.map((citation) => (
          <a
            key={citation.sourceDocumentId}
            className="compact-citation-source"
            href={`#source-${citation.sourceDocumentId}`}
            data-citation-id={citation.citationIds[0]}
            data-citation-count={citation.citationIds.length}
            data-source-document-id={citation.sourceDocumentId}
            data-freshness-state={citation.freshnessState}
            data-governed-golden-citation-binding="same-asset-source"
            onClick={() => setPopoverOpen(false)}
          >
            <span className="compact-citation-title">{citation.title}</span>
            <span className="compact-citation-meta">
              {citation.publisher} · {citation.freshnessState.replaceAll("_", " ")}
            </span>
          </a>
        ))}
        {metadataRows.length ? (
          <span className="compact-citation-metadata" data-source-icon-metadata-rows={metadataRows.length}>
            {metadataRows.map((row) => (
              <span
                key={`${row.label}-${String(row.value)}`}
                className="compact-citation-metadata-row"
                data-source-metadata-label={row.label}
                data-source-metadata-state={row.state ?? undefined}
              >
                <span>{row.label}</span>
                <strong>{row.value}</strong>
              </span>
            ))}
          </span>
        ) : null}
      </span>
    </details>
  );
}
