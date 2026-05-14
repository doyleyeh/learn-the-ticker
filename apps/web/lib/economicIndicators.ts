import {
  economicIndicatorsPackFixture,
  type Citation,
  type EconomicIndicatorsPackFixture,
  type EvidenceState,
  type FreshnessState,
  type SourceAllowlistStatus,
  type SourceDocument,
  type SourceQuality,
  type SourceUsePolicy,
  type WeeklyNewsContractState
} from "./fixtures";
import { runtimeSectionStatesFromPayload } from "./runtimeSectionStates";

type Fetcher = typeof fetch;

type BackendCitation = {
  citation_id: string;
  source_document_id: string;
  title: string;
  publisher: string;
  freshness_state: string;
};

type BackendSourceDocument = {
  source_document_id: string;
  source_type: string;
  title: string;
  publisher: string;
  url: string;
  published_at: string | null;
  as_of_date: string | null;
  retrieved_at: string;
  freshness_state: string;
  is_official: boolean;
  supporting_passage?: string;
  source_quality: string;
  allowlist_status: string;
  source_use_policy: string;
  permitted_operations?: {
    can_export_full_text?: boolean;
  };
};

type BackendEconomicIndicatorsPack = {
  schema_version: "economic-indicators-pack-v1";
  state: WeeklyNewsContractState;
  region: "US";
  as_of_date: string;
  items: Array<{
    indicator_id: string;
    name: string;
    category: "official_historical_actual" | "market_reference";
    value: string;
    numeric_value: number | null;
    unit: string | null;
    period: string;
    as_of_date: string;
    published_at: string | null;
    retrieved_at: string;
    source: BackendSourceDocument;
    freshness_state: string;
    trend_direction: "up" | "down" | "neutral" | "unknown";
    citation_ids: string[];
    source_document_ids: string[];
    evidence_state: string;
  }>;
  citations: BackendCitation[];
  source_documents: BackendSourceDocument[];
  section_states?: unknown[];
  analysis_pack_metadata?: {
    analysis_source?: "imported_local_pack" | "backend_generated" | "deterministic_fixture";
    freshness_expires_at?: string | null;
    import_bundle_id?: string | null;
    validation_status?: "passed" | "failed" | "not_applicable";
  } | null;
  no_live_external_calls: boolean;
  stable_facts_are_separate: boolean;
};

export async function fetchEconomicIndicators(
  fallback: EconomicIndicatorsPackFixture = economicIndicatorsPackFixture,
  fetcher: Fetcher = fetch
): Promise<EconomicIndicatorsPackFixture> {
  const response = await fetcher(economicIndicatorsEndpoint());

  if (!response.ok) {
    throw new Error(`Economic indicators request failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (!isEconomicIndicatorsPackResponse(payload)) {
    throw new Error("Economic indicators response did not match the expected backend response contract.");
  }

  return toEconomicIndicatorsPack(payload, fallback);
}

function economicIndicatorsEndpoint() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || process.env.API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new Error("No API base URL is configured for economic-indicators fetches.");
  }
  return new URL("/api/economic-indicators", apiBaseUrl).toString();
}

function isEconomicIndicatorsPackResponse(value: unknown): value is BackendEconomicIndicatorsPack {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<BackendEconomicIndicatorsPack>;
  return (
    candidate.schema_version === "economic-indicators-pack-v1" &&
    candidate.region === "US" &&
    !!candidate.state &&
    typeof candidate.as_of_date === "string" &&
    Array.isArray(candidate.items) &&
    Array.isArray(candidate.citations) &&
    Array.isArray(candidate.source_documents) &&
    candidate.no_live_external_calls === true &&
    candidate.stable_facts_are_separate === true
  );
}

function toEconomicIndicatorsPack(
  pack: BackendEconomicIndicatorsPack,
  fallback: EconomicIndicatorsPackFixture
): EconomicIndicatorsPackFixture {
  return {
    schemaVersion: "economic-indicators-pack-v1",
    state: pack.state,
    region: "US",
    asOfDate: pack.as_of_date,
    items: pack.items.map((item) => ({
      indicatorId: item.indicator_id,
      name: item.name,
      category: item.category,
      value: item.value,
      numericValue: item.numeric_value,
      unit: item.unit,
      period: item.period,
      asOfDate: item.as_of_date,
      publishedAt: item.published_at,
      retrievedAt: item.retrieved_at,
      source: toEconomicIndicatorSource(item.source),
      freshnessState: toFreshnessState(item.freshness_state),
      trendDirection: item.trend_direction,
      citationIds: item.citation_ids,
      sourceDocumentIds: item.source_document_ids,
      evidenceState: toEvidenceState(item.evidence_state)
    })),
    citations: mergeUniqueBy(
      pack.citations.map(toCitation),
      fallback.citations,
      (citation) => citation.citationId
    ),
    sourceDocuments: mergeUniqueBy(
      pack.source_documents.map(toSourceDocument),
      fallback.sourceDocuments,
      (source) => source.sourceDocumentId
    ),
    analysisPackMetadata: pack.analysis_pack_metadata
      ? {
          analysisSource: pack.analysis_pack_metadata.analysis_source ?? "backend_generated",
          freshnessExpiresAt: pack.analysis_pack_metadata.freshness_expires_at ?? null,
          importBundleId: pack.analysis_pack_metadata.import_bundle_id ?? null,
          validationStatus: pack.analysis_pack_metadata.validation_status ?? "not_applicable"
        }
      : null,
    sectionStates: runtimeSectionStatesFromPayload(pack),
    noLiveExternalCalls: true,
    stableFactsAreSeparate: true
  };
}

function toEconomicIndicatorSource(source: BackendSourceDocument): EconomicIndicatorsPackFixture["items"][number]["source"] {
  return {
    sourceDocumentId: source.source_document_id,
    sourceType: source.source_type,
    title: source.title,
    publisher: source.publisher,
    url: source.url,
    publishedAt: source.published_at ?? null,
    asOfDate: source.as_of_date ?? null,
    retrievedAt: source.retrieved_at,
    freshnessState: toFreshnessState(source.freshness_state),
    isOfficial: source.is_official,
    sourceQuality: toSourceQuality(source.source_quality),
    allowlistStatus: toAllowlistStatus(source.allowlist_status),
    sourceUsePolicy: toSourceUsePolicy(source.source_use_policy)
  };
}

function toCitation(citation: BackendCitation): Citation {
  return {
    citationId: citation.citation_id,
    sourceDocumentId: citation.source_document_id,
    title: citation.title,
    publisher: citation.publisher,
    freshnessState: toFreshnessState(citation.freshness_state)
  };
}

function toSourceDocument(source: BackendSourceDocument): SourceDocument {
  return {
    sourceDocumentId: source.source_document_id,
    sourceType: source.source_type,
    title: source.title,
    publisher: source.publisher,
    url: source.url,
    publishedAt: source.published_at ?? source.as_of_date ?? "Unknown",
    asOfDate: source.as_of_date ?? undefined,
    retrievedAt: source.retrieved_at,
    freshnessState: toFreshnessState(source.freshness_state),
    isOfficial: source.is_official,
    supportingPassage: source.supporting_passage ?? "",
    sourceQuality: toSourceQuality(source.source_quality),
    source_quality: toSourceQuality(source.source_quality),
    allowlistStatus: toAllowlistStatus(source.allowlist_status),
    allowlist_status: toAllowlistStatus(source.allowlist_status),
    sourceUsePolicy: toSourceUsePolicy(source.source_use_policy),
    source_use_policy: toSourceUsePolicy(source.source_use_policy),
    permitted_operations: {
      can_export_full_text: source.permitted_operations?.can_export_full_text
    }
  };
}

function mergeUniqueBy<T>(preferred: T[], fallback: T[], getKey: (item: T) => string): T[] {
  const merged: T[] = [];
  const seen = new Set<string>();
  for (const collection of [preferred, fallback]) {
    for (const item of collection) {
      const key = getKey(item);
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      merged.push(item);
    }
  }
  return merged;
}

function toFreshnessState(value: string): FreshnessState {
  if (value === "fresh" || value === "stale" || value === "unknown" || value === "unavailable") {
    return value;
  }
  return "unknown";
}

function toEvidenceState(value: string): EvidenceState {
  if (
    value === "supported" ||
    value === "partial" ||
    value === "mixed" ||
    value === "unknown" ||
    value === "unavailable" ||
    value === "stale" ||
    value === "insufficient_evidence" ||
    value === "no_high_signal" ||
    value === "no_major_recent_development" ||
    value === "unsupported"
  ) {
    return value;
  }
  return "unknown";
}

function toSourceQuality(value: string): SourceQuality {
  if (
    value === "official" ||
    value === "issuer" ||
    value === "provider" ||
    value === "fixture" ||
    value === "allowlisted" ||
    value === "rejected" ||
    value === "unknown"
  ) {
    return value;
  }
  return "unknown";
}

function toAllowlistStatus(value: string): SourceAllowlistStatus {
  if (value === "allowed" || value === "rejected" || value === "pending_review" || value === "not_allowlisted") {
    return value;
  }
  return "not_allowlisted";
}

function toSourceUsePolicy(value: string): SourceUsePolicy {
  if (
    value === "metadata_only" ||
    value === "link_only" ||
    value === "summary_allowed" ||
    value === "full_text_allowed" ||
    value === "rejected"
  ) {
    return value;
  }
  return "metadata_only";
}
