import {
  getCitationById,
  type AssetFixture,
  type Citation
} from "../lib/fixtures";

type CompactCitationSourcesProps = {
  citations: Citation[];
  label?: string;
  summaryLabel?: string;
  emptyLabel?: string;
  showEmpty?: boolean;
  className?: string;
  dashboardSourceIcon?: boolean;
  metadataRows?: EvidenceMetadataRow[];
  showCount?: boolean;
};

export type EvidenceMetadataRow = {
  label: string;
  value: string | number | null | undefined;
  state?: string | null;
};

export function resolveAssetCitations(asset: AssetFixture, citationIds: string[]) {
  return citationIds
    .map((citationId) => getCitationById(asset, citationId))
    .filter((citation): citation is Citation => Boolean(citation));
}

export function resolveCitationList(citations: Citation[], citationIds: string[]) {
  const byId = new Map(citations.map((citation) => [citation.citationId, citation]));
  return citationIds
    .map((citationId) => byId.get(citationId))
    .filter((citation): citation is Citation => Boolean(citation));
}

export function CompactCitationSources({
  citations,
  label = "Sources",
  summaryLabel,
  emptyLabel = "No source citation",
  showEmpty = false,
  className,
  dashboardSourceIcon = false,
  metadataRows = [],
  showCount = true
}: CompactCitationSourcesProps) {
  const sourceGroups = uniqueBySourceDocumentId(citations);
  const visibleMetadataRows = metadataRows.filter((row) => row.value !== null && row.value !== undefined && row.value !== "");

  if (!sourceGroups.length && !visibleMetadataRows.length) {
    return showEmpty ? <span className="source-icon-empty" aria-label={emptyLabel}>-</span> : null;
  }

  const sourceCount = sourceGroups.length;
  const classNames = [
    "source-icon-disclosure",
    "compact-citation-sources",
    summaryLabel ? "source-icon-disclosure-labeled" : null,
    className
  ].filter(Boolean).join(" ");
  const countLabel = `${sourceCount} source${sourceCount === 1 ? "" : "s"}`;
  const metadataLabel = `${visibleMetadataRows.length} evidence detail${visibleMetadataRows.length === 1 ? "" : "s"}`;

  return (
    <details
      className={classNames}
      data-compact-citation-sources
      data-compact-citation-source-count={sourceCount}
      data-compact-citation-metadata-count={visibleMetadataRows.length}
      data-dashboard-source-icon={dashboardSourceIcon ? "true" : undefined}
      title={`${label}: ${countLabel}, ${metadataLabel}`}
    >
      <summary aria-label={`${label}: show ${countLabel} and ${metadataLabel}`}>
        {summaryLabel ? (
          <span className="source-icon-label">{summaryLabel}</span>
        ) : (
          <span className="source-icon-symbol" aria-hidden="true">i</span>
        )}
        {showCount && sourceCount > 1 ? <span className="source-icon-count">{sourceCount}</span> : null}
      </summary>
      <span className="source-icon-popover compact-citation-popover">
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
          >
            <span className="compact-citation-title">{citation.title}</span>
            <span className="compact-citation-meta">
              {citation.publisher} · {citation.freshnessState.replaceAll("_", " ")}
            </span>
          </a>
        ))}
        {visibleMetadataRows.length ? (
          <span className="compact-citation-metadata" data-source-icon-metadata-rows={visibleMetadataRows.length}>
            {visibleMetadataRows.map((row) => (
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

function uniqueBySourceDocumentId(citations: Citation[]) {
  const bySource = new Map<string, Citation & { citationIds: string[] }>();
  for (const citation of citations) {
    const existing = bySource.get(citation.sourceDocumentId);
    if (existing) {
      if (!existing.citationIds.includes(citation.citationId)) {
        existing.citationIds.push(citation.citationId);
      }
      continue;
    }
    bySource.set(citation.sourceDocumentId, { ...citation, citationIds: [citation.citationId] });
  }
  return Array.from(bySource.values());
}
