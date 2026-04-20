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
      aria-label={`Open source drawer for ${citation.title}`}
      data-citation-id={citation.citationId}
    >
      [{label ?? citation.citationId}]
    </a>
  );
}
