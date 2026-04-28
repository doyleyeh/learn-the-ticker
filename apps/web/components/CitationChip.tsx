import type { Citation } from "../lib/fixtures";

type CitationChipProps = {
  citation: Citation;
  label?: string;
};

export function CitationChip({ citation, label }: CitationChipProps) {
  return (
    <a
      className="citation-chip"
      href={`#source-${citation.sourceDocumentId}`}
      aria-label={`Open source details for ${citation.title}`}
      data-citation-id={citation.citationId}
      data-source-document-id={citation.sourceDocumentId}
      data-freshness-state={citation.freshnessState}
      data-governed-golden-citation-binding="same-asset-source"
    >
      [{label ?? citation.citationId}]
    </a>
  );
}
