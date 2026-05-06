import {
  getCitationById,
  type AssetFixture,
  type Citation
} from "../lib/fixtures";

type CompactCitationSourcesProps = {
  citations: Citation[];
  label?: string;
  emptyLabel?: string;
  showEmpty?: boolean;
  className?: string;
  dashboardSourceIcon?: boolean;
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
  emptyLabel = "No source citation",
  showEmpty = false,
  className,
  dashboardSourceIcon = false
}: CompactCitationSourcesProps) {
  const uniqueCitations = uniqueByCitationId(citations);

  if (!uniqueCitations.length) {
    return showEmpty ? <span className="source-icon-empty" aria-label={emptyLabel}>-</span> : null;
  }

  const sourceCount = uniqueCitations.length;
  const classNames = ["source-icon-disclosure", "compact-citation-sources", className].filter(Boolean).join(" ");

  return (
    <details
      className={classNames}
      data-compact-citation-sources
      data-compact-citation-source-count={sourceCount}
      data-dashboard-source-icon={dashboardSourceIcon ? "true" : undefined}
      title={`${label}: ${sourceCount} source${sourceCount === 1 ? "" : "s"}`}
    >
      <summary aria-label={`${label}: show ${sourceCount} source${sourceCount === 1 ? "" : "s"}`}>
        <span aria-hidden="true">i</span>
        {sourceCount > 1 ? <span className="source-icon-count">{sourceCount}</span> : null}
      </summary>
      <span className="source-icon-popover compact-citation-popover">
        {uniqueCitations.map((citation) => (
          <a
            key={citation.citationId}
            className="compact-citation-source"
            href={`#source-${citation.sourceDocumentId}`}
            data-citation-id={citation.citationId}
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
      </span>
    </details>
  );
}

function uniqueByCitationId(citations: Citation[]) {
  const seen = new Set<string>();
  return citations.filter((citation) => {
    if (seen.has(citation.citationId)) {
      return false;
    }
    seen.add(citation.citationId);
    return true;
  });
}
