import { citationLabel, type Citation, type SourceDocument } from "../lib/fixtures";

type CitationChipProps = {
  citation: Citation;
  label?: string;
  source?: SourceDocument;
};

export function CitationChip({ citation, label, source }: CitationChipProps) {
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
      [{label ?? citationLabelFromSource(citation, source)}]
    </a>
  );
}

function citationLabelFromSource(citation: Citation, source?: SourceDocument) {
  if (!source) {
    return citationLabel(citation.citationId);
  }

  const sourceType = source.sourceType.toLowerCase();
  const sourceQuality = (source.sourceQuality ?? source.source_quality ?? "unknown").toLowerCase();
  const publisher = source.publisher.toLowerCase();
  const title = source.title.toLowerCase();
  const url = source.url.toLowerCase();

  if (source.isOfficial && (sourceType.includes("sec") || publisher.includes("sec") || url.includes("sec.gov"))) {
    return "SEC";
  }
  if (
    source.isOfficial ||
    sourceQuality === "official" ||
    sourceQuality === "issuer" ||
    sourceType.includes("issuer") ||
    sourceType.includes("prospectus") ||
    sourceType.includes("fact_sheet")
  ) {
    return "Issuer";
  }
  if (
    sourceQuality === "provider" ||
    sourceType.includes("provider") ||
    title.includes("yahoo") ||
    publisher.includes("yahoo") ||
    publisher.includes("yfinance")
  ) {
    return "Provider";
  }
  if (sourceQuality === "fixture" || source.url.startsWith("local://")) {
    return "Fixture";
  }

  return citationLabel(citation.citationId);
}
