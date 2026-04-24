import {
  normalizeTicker,
  type AssetFixture,
  type AssetType,
  type Citation,
  type FreshnessState,
  type SourceDocument
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
};

export async function fetchSupportedAssetOverview(
  ticker: string,
  fallbackAsset: AssetFixture,
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
    candidate.source_documents.length > 0
  );
}

function mergeAssetFixtureWithOverview(fallbackAsset: AssetFixture, overview: BackendOverviewResponse): AssetFixture {
  return {
    ...fallbackAsset,
    ticker: overview.asset.ticker,
    name: overview.asset.name,
    assetType: toAssetType(overview.asset.asset_type),
    exchange: overview.asset.exchange ?? fallbackAsset.exchange,
    issuer: overview.asset.issuer ?? fallbackAsset.issuer,
    freshness: {
      pageLastUpdatedAt: overview.freshness.page_last_updated_at,
      factsAsOf: overview.freshness.facts_as_of,
      holdingsAsOf: overview.freshness.holdings_as_of ?? fallbackAsset.freshness.holdingsAsOf,
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
    suitabilitySummary: {
      mayFit: overview.suitability_summary.may_fit,
      mayNotFit: overview.suitability_summary.may_not_fit,
      learnNext: overview.suitability_summary.learn_next
    },
    citations: mergeUniqueBy(
      overview.citations.map(toCitation),
      fallbackAsset.citations,
      (citation) => citation.citationId
    ),
    sourceDocuments: mergeUniqueBy(
      overview.source_documents.map(toSourceDocument),
      fallbackAsset.sourceDocuments,
      (source) => source.sourceDocumentId
    )
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
