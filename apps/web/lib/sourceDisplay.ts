import type { SourceDocument } from "./fixtures";

type SourceDisplayMetadata =
  | Pick<SourceDocument, "isOfficial" | "sourceType" | "sourceQuality" | "source_quality">
  | {
      is_official?: boolean;
      source_type?: string;
      source_quality?: string;
    }
  | null
  | undefined;

export function sanitizeSourceDisplayTitle(title: string, source?: SourceDisplayMetadata) {
  if (!isIssuerLikeSource(source)) {
    return title;
  }

  return title
    .replace(/\s+deterministic provider fixture\b/gi, "")
    .replace(/\s+deterministic fixture\b/gi, "")
    .replace(/\s+provider fixture\b/gi, "")
    .trim();
}

function isIssuerLikeSource(source: SourceDisplayMetadata) {
  if (!source) {
    return false;
  }

  const candidate = source as Partial<SourceDocument> & {
    is_official?: boolean;
    source_type?: string;
    source_quality?: string;
  };
  const sourceQuality = candidate.source_quality ?? candidate.sourceQuality;
  const sourceType = candidate.source_type ?? candidate.sourceType;
  const isOfficial = Boolean(candidate.isOfficial ?? candidate.is_official);

  return (
    isOfficial ||
    sourceQuality === "issuer" ||
    sourceQuality === "official" ||
    String(sourceType ?? "").includes("issuer") ||
    String(sourceType ?? "").includes("fact_sheet") ||
    String(sourceType ?? "").includes("prospectus")
  );
}
