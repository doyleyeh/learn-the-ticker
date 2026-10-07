import {
  getCitationById,
  type AssetFixture,
  type Citation
} from "../lib/fixtures";
import { CompactCitationSourcesClient } from "./CompactCitationSourcesClient";

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

export type CompactCitationSourceGroup = Citation & { citationIds: string[] };

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
    <CompactCitationSourcesClient
      className={classNames}
      dashboardSourceIcon={dashboardSourceIcon}
      label={label}
      metadataLabel={metadataLabel}
      metadataRows={visibleMetadataRows}
      showCount={showCount}
      sourceCount={sourceCount}
      sourceGroups={sourceGroups}
      summaryLabel={summaryLabel}
      title={`${label}: ${countLabel}, ${metadataLabel}`}
      triggerLabel={`${label}: show ${countLabel} and ${metadataLabel}`}
    />
  );
}

function uniqueBySourceDocumentId(citations: Citation[]): CompactCitationSourceGroup[] {
  const bySource = new Map<string, CompactCitationSourceGroup>();
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
