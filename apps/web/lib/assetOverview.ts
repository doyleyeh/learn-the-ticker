import {
  normalizeTicker,
  type AssetFixture,
  type AssetType,
  type Citation,
  type EvidenceState,
  type FreshnessState,
  type SourceDocument,
  type StockOverviewSection,
  type StockSectionType
} from "./fixtures";

type Fetcher = typeof fetch;

type BackendAssetIdentity = {
  ticker: string;
  name: string;
  asset_type: string;
  exchange: string | null;
  issuer: string | null;
  status: string;
  supported: boolean;
};

type BackendFreshness = {
  page_last_updated_at: string;
  facts_as_of: string;
  holdings_as_of: string | null;
  recent_events_as_of: string;
  freshness_state: string;
};

type BackendBeginnerSummary = {
  what_it_is: string;
  why_people_consider_it: string;
  main_catch: string;
};

type BackendRiskItem = {
  title: string;
  plain_english_explanation: string;
  citation_ids: string[];
};

type BackendSuitabilitySummary = {
  may_fit: string;
  may_not_fit: string;
  learn_next: string;
};

type BackendClaim = {
  claim_id: string;
  claim_text: string;
  citation_ids: string[];
};

type BackendCitation = {
  citation_id: string;
  source_document_id: string;
  title: string;
  publisher: string;
  freshness_state: string;
};

type BackendPermittedOperations = {
  can_export_full_text?: boolean;
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
  supporting_passage: string;
  source_quality: string;
  allowlist_status: string;
  source_use_policy: string;
  permitted_operations: BackendPermittedOperations;
};

type BackendOverviewSectionItem = {
  item_id: string;
  title: string;
  summary: string;
  citation_ids: string[];
  source_document_ids: string[];
  freshness_state: string;
  evidence_state: string;
  event_date: string | null;
  as_of_date: string | null;
  retrieved_at: string | null;
  limitations: string | null;
};

type BackendOverviewMetric = {
  metric_id: string;
  label: string;
  value: string | number | null;
  unit: string | null;
  citation_ids: string[];
  source_document_ids: string[];
  freshness_state: string;
  evidence_state: string;
  as_of_date: string | null;
  retrieved_at: string | null;
  limitations: string | null;
};

type BackendOverviewSection = {
  section_id: string;
  title: string;
  section_type: string;
  applies_to: string[];
  beginner_summary: string | null;
  items: BackendOverviewSectionItem[];
  metrics: BackendOverviewMetric[];
  citation_ids: string[];
  source_document_ids: string[];
  freshness_state: string;
  evidence_state: string;
  as_of_date: string | null;
  retrieved_at: string | null;
  limitations: string | null;
};

type BackendOverviewResponse = {
  asset: BackendAssetIdentity;
  state: {
    status: string;
    message: string;
  };
  freshness: BackendFreshness;
  beginner_summary: BackendBeginnerSummary;
  top_risks: BackendRiskItem[];
  suitability_summary: BackendSuitabilitySummary;
  claims: BackendClaim[];
  citations: BackendCitation[];
  source_documents: BackendSourceDocument[];
  sections: BackendOverviewSection[];
};

export async function fetchSupportedAssetOverview(
  ticker: string,
  fallbackAsset?: AssetFixture,
  fetcher: Fetcher = fetch
): Promise<AssetFixture> {
  const normalizedTicker = normalizeTicker(ticker);
  const endpoint = assetOverviewEndpoint(normalizedTicker);
  const response = await fetcher(endpoint);

  if (!response.ok) {
    throw new Error(`Asset overview request failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (!isSupportedAssetOverviewResponse(payload, normalizedTicker)) {
    throw new Error("Asset overview response did not match the expected backend response contract.");
  }

  return mergeAssetFixtureWithOverview(fallbackAsset, payload);
}

export const GOVERNED_GOLDEN_OVERVIEW_RENDERING_PROOF =
  "api-backed governed golden overview uses persisted knowledge-pack records plus generated-output cache validation";

function assetOverviewEndpoint(ticker: string) {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || process.env.API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new Error("No API base URL is configured for supported asset overview fetches.");
  }
  return new URL(`/api/assets/${encodeURIComponent(ticker)}/overview`, apiBaseUrl).toString();
}

function isSupportedAssetOverviewResponse(value: unknown, requestedTicker: string): value is BackendOverviewResponse {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<BackendOverviewResponse>;
  return (
    !!candidate.asset &&
    typeof candidate.asset === "object" &&
    candidate.asset.ticker === requestedTicker &&
    (candidate.asset.asset_type === "stock" || candidate.asset.asset_type === "etf") &&
    candidate.asset.supported === true &&
    !!candidate.state &&
    typeof candidate.state === "object" &&
    candidate.state.status === "supported" &&
    !!candidate.freshness &&
    typeof candidate.freshness === "object" &&
    typeof candidate.freshness.page_last_updated_at === "string" &&
    typeof candidate.freshness.facts_as_of === "string" &&
    typeof candidate.freshness.recent_events_as_of === "string" &&
    !!candidate.beginner_summary &&
    typeof candidate.beginner_summary === "object" &&
    typeof candidate.beginner_summary.what_it_is === "string" &&
    typeof candidate.beginner_summary.why_people_consider_it === "string" &&
    typeof candidate.beginner_summary.main_catch === "string" &&
    !!candidate.suitability_summary &&
    typeof candidate.suitability_summary === "object" &&
    typeof candidate.suitability_summary.may_fit === "string" &&
    typeof candidate.suitability_summary.may_not_fit === "string" &&
    typeof candidate.suitability_summary.learn_next === "string" &&
    Array.isArray(candidate.top_risks) &&
    candidate.top_risks.length >= 3 &&
    Array.isArray(candidate.claims) &&
    candidate.claims.length > 0 &&
    Array.isArray(candidate.citations) &&
    candidate.citations.length > 0 &&
    Array.isArray(candidate.source_documents) &&
    candidate.source_documents.length > 0 &&
    Array.isArray(candidate.sections)
  );
}

function mergeAssetFixtureWithOverview(fallbackAsset: AssetFixture | undefined, overview: BackendOverviewResponse): AssetFixture {
  const assetType = toAssetType(overview.asset.asset_type);
  const backendSections = overview.sections
    .filter((section) => section.applies_to.includes(assetType))
    .map(toOverviewSection);
  const backendSectionFields =
    backendSections.length > 0
      ? assetType === "stock"
        ? { stockSections: backendSections, etfSections: undefined }
        : { etfSections: backendSections, stockSections: undefined }
      : {};
  const fallbackCitations = fallbackAsset?.citations ?? [];
  const fallbackSources = fallbackAsset?.sourceDocuments ?? [];
  const sourceDocuments = mergeUniqueBy(
    overview.source_documents.map(toSourceDocument),
    fallbackSources,
    (source) => source.sourceDocumentId
  );
  const citations = mergeUniqueBy(overview.citations.map(toCitation), fallbackCitations, (citation) => citation.citationId);

  return {
    ...(fallbackAsset ?? {}),
    ticker: overview.asset.ticker,
    name: overview.asset.name,
    assetType,
    exchange: overview.asset.exchange ?? fallbackAsset?.exchange ?? "Unknown",
    issuer: overview.asset.issuer ?? fallbackAsset?.issuer,
    freshness: {
      pageLastUpdatedAt: overview.freshness.page_last_updated_at,
      factsAsOf: overview.freshness.facts_as_of,
      holdingsAsOf: overview.freshness.holdings_as_of ?? fallbackAsset?.freshness.holdingsAsOf,
      recentEventsAsOf: overview.freshness.recent_events_as_of
    },
    beginnerSummary: {
      whatItIs: overview.beginner_summary.what_it_is,
      whyPeopleConsiderIt: overview.beginner_summary.why_people_consider_it,
      mainCatch: overview.beginner_summary.main_catch
    },
    claims: overview.claims.map((claim) => ({
      claimId: claim.claim_id,
      claimText: claim.claim_text,
      citationIds: claim.citation_ids
    })),
    topRisks: overview.top_risks.map((risk) => ({
      title: risk.title,
      plainEnglishExplanation: risk.plain_english_explanation,
      citationIds: risk.citation_ids
    })),
    facts: fallbackAsset?.facts ?? factsFromOverviewSections(backendSections),
    recentDevelopments: fallbackAsset?.recentDevelopments ?? [],
    suitabilitySummary: {
      mayFit: overview.suitability_summary.may_fit,
      mayNotFit: overview.suitability_summary.may_not_fit,
      learnNext: overview.suitability_summary.learn_next
    },
    citations,
    sourceDocuments,
    citationContexts: fallbackAsset?.citationContexts ?? citationContextsFromOverview(backendSections, citations, sourceDocuments),
    ...backendSectionFields
  };
}

function toAssetType(value: string): AssetType {
  return value === "stock" ? "stock" : "etf";
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
    supportingPassage: source.supporting_passage,
    sourceQuality: toSourceQuality(source.source_quality),
    source_quality: toSourceQuality(source.source_quality),
    allowlistStatus: toAllowlistStatus(source.allowlist_status),
    allowlist_status: toAllowlistStatus(source.allowlist_status),
    sourceUsePolicy: toSourceUsePolicy(source.source_use_policy),
    source_use_policy: toSourceUsePolicy(source.source_use_policy),
    permitted_operations: {
      can_export_full_text: source.permitted_operations.can_export_full_text
    }
  };
}

function factsFromOverviewSections(sections: StockOverviewSection[]): AssetFixture["facts"] {
  const facts: AssetFixture["facts"] = [];
  const seen = new Set<string>();

  for (const section of sections) {
    for (const metric of section.metrics ?? []) {
      if (seen.has(metric.label)) {
        continue;
      }
      seen.add(metric.label);
      facts.push({
        label: metric.label,
        value: formatSectionMetricValue(metric.value, metric.unit),
        citationId: metric.citationIds[0]
      });
    }

    for (const item of section.items) {
      if (facts.length >= 6 || seen.has(item.title)) {
        continue;
      }
      seen.add(item.title);
      facts.push({
        label: item.title,
        value: item.summary,
        citationId: item.citationIds[0]
      });
    }
  }

  return facts.slice(0, 6);
}

function citationContextsFromOverview(
  sections: StockOverviewSection[],
  citations: Citation[],
  sourceDocuments: SourceDocument[]
): AssetFixture["citationContexts"] {
  const citationSourceIds = new Map(citations.map((citation) => [citation.citationId, citation.sourceDocumentId]));
  const sourcePassages = new Map(sourceDocuments.map((source) => [source.sourceDocumentId, source.supportingPassage]));
  const contexts: NonNullable<AssetFixture["citationContexts"]> = [];
  const seen = new Set<string>();

  for (const section of sections) {
    const subjects = [
      ...section.items.map((item) => ({
        id: item.itemId,
        title: item.title,
        summary: item.summary,
        citationIds: item.citationIds
      })),
      ...(section.metrics ?? []).map((metric) => ({
        id: metric.metricId,
        title: metric.label,
        summary: formatSectionMetricValue(metric.value, metric.unit),
        citationIds: metric.citationIds
      }))
    ];

    for (const subject of subjects) {
      for (const citationId of subject.citationIds) {
        const sourceDocumentId = citationSourceIds.get(citationId);
        if (!sourceDocumentId) {
          continue;
        }
        const key = `${section.sectionId}:${subject.id}:${citationId}`;
        if (seen.has(key)) {
          continue;
        }
        seen.add(key);
        contexts.push({
          citationId,
          sourceDocumentId,
          sectionId: section.sectionId,
          sectionTitle: section.title,
          claimContext: `${subject.title}: ${subject.summary}`,
          supportingPassage: sourcePassages.get(sourceDocumentId) ?? ""
        });
      }
    }
  }

  return contexts;
}

function formatSectionMetricValue(value: string | number | null, unit: string | null | undefined) {
  if (value === null || value === undefined) {
    return "Unavailable";
  }
  return unit ? `${value}${unit}` : String(value);
}

function toOverviewSection(section: BackendOverviewSection): StockOverviewSection {
  return {
    sectionId: section.section_id,
    title: section.title,
    sectionType: toStockSectionType(section.section_type),
    beginnerSummary:
      section.beginner_summary ??
      section.limitations ??
      "This section is unavailable because the backend overview contract did not provide a source-backed summary.",
    items: section.items.map((item) => ({
      itemId: item.item_id,
      title: item.title,
      summary: item.summary,
      citationIds: item.citation_ids,
      sourceDocumentIds: item.source_document_ids,
      freshnessState: toFreshnessState(item.freshness_state),
      evidenceState: toEvidenceState(item.evidence_state),
      eventDate: item.event_date,
      asOfDate: item.as_of_date,
      retrievedAt: item.retrieved_at,
      limitations: item.limitations
    })),
    metrics: section.metrics.map((metric) => ({
      metricId: metric.metric_id,
      label: metric.label,
      value: metric.value,
      unit: metric.unit,
      citationIds: metric.citation_ids,
      sourceDocumentIds: metric.source_document_ids,
      freshnessState: toFreshnessState(metric.freshness_state),
      evidenceState: toEvidenceState(metric.evidence_state),
      asOfDate: metric.as_of_date,
      retrievedAt: metric.retrieved_at,
      limitations: metric.limitations
    })),
    citationIds: section.citation_ids,
    sourceDocumentIds: section.source_document_ids,
    freshnessState: toFreshnessState(section.freshness_state),
    evidenceState: toEvidenceState(section.evidence_state),
    asOfDate: section.as_of_date,
    retrievedAt: section.retrieved_at,
    limitations: section.limitations
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
  if (
    value === "fresh" ||
    value === "stale" ||
    value === "unknown" ||
    value === "unavailable" ||
    value === "partial" ||
    value === "insufficient_evidence"
  ) {
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

function toStockSectionType(value: string): StockSectionType {
  if (
    value === "stable_facts" ||
    value === "evidence_gap" ||
    value === "risk" ||
    value === "recent_developments" ||
    value === "educational_suitability"
  ) {
    return value;
  }
  return "evidence_gap";
}

function toSourceQuality(value: string): SourceDocument["sourceQuality"] {
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

function toAllowlistStatus(value: string): SourceDocument["allowlistStatus"] {
  if (value === "allowed" || value === "rejected" || value === "pending_review" || value === "not_allowlisted") {
    return value;
  }
  return "not_allowlisted";
}

function toSourceUsePolicy(value: string): SourceDocument["sourceUsePolicy"] {
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
