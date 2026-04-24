import {
  normalizeTicker,
  type AIComprehensiveAnalysisFixture,
  type AssetType,
  type Citation,
  type FreshnessState,
  type SourceDocument,
  type WeeklyNewsContractState,
  type WeeklyNewsEmptyState,
  type WeeklyNewsFocusFixture
} from "./fixtures";

type Fetcher = typeof fetch;

type BackendAssetIdentity = {
  ticker: string;
  asset_type: string;
  status: string;
  supported: boolean;
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
  supporting_passage?: string;
  source_quality: string;
  allowlist_status: string;
  source_use_policy: string;
  permitted_operations?: BackendPermittedOperations;
};

type BackendWeeklyNewsFocus = {
  schema_version: "weekly-news-focus-v1";
  state: WeeklyNewsContractState;
  window: {
    as_of_date: string;
    timezone: "America/New_York";
    previous_market_week: {
      start: string | null;
      end: string | null;
    };
    current_week_to_date: {
      start: string | null;
      end: string | null;
    };
    news_window_start: string;
    news_window_end: string;
    includes_current_week_to_date: boolean;
  };
  items: Array<{
    event_id: string;
    asset_ticker: string;
    event_type: string;
    title: string;
    summary: string;
    event_date?: string | null;
    published_at?: string | null;
    period_bucket: "previous_market_week" | "current_week_to_date";
    citation_ids: string[];
    source: BackendSourceDocument;
    freshness_state: string;
    importance_score: number;
  }>;
  empty_state: {
    state: WeeklyNewsContractState;
    message: string;
    evidence_state: string;
    selected_item_count: number;
    suppressed_candidate_count: number;
  } | null;
  citations: BackendCitation[];
  source_documents: BackendSourceDocument[];
  no_live_external_calls: boolean;
  stable_facts_are_separate: boolean;
};

type BackendAIComprehensiveAnalysis = {
  schema_version: "ai-comprehensive-analysis-v1";
  state: WeeklyNewsContractState;
  analysis_available: boolean;
  suppression_reason: string | null;
  sections: Array<{
    section_id: "what_changed_this_week" | "market_context" | "business_or_fund_context" | "risk_context";
    label: "What Changed This Week" | "Market Context" | "Business/Fund Context" | "Risk Context";
    analysis: string;
    bullets: string[];
    citation_ids: string[];
    uncertainty: string[];
  }>;
  citation_ids: string[];
  source_document_ids: string[];
  weekly_news_event_ids: string[];
  canonical_fact_citation_ids: string[];
  no_live_external_calls: boolean;
  stable_facts_are_separate: boolean;
};

type BackendWeeklyNewsResponse = {
  asset: BackendAssetIdentity;
  state: {
    status: string;
  };
  weekly_news_focus: BackendWeeklyNewsFocus;
  ai_comprehensive_analysis: BackendAIComprehensiveAnalysis;
};

type SupportedWeeklyNewsResponse = {
  weeklyNewsFocus: WeeklyNewsFocusFixture;
  aiComprehensiveAnalysis: AIComprehensiveAnalysisFixture;
};

export async function fetchSupportedAssetWeeklyNews(
  ticker: string,
  fallbackWeeklyNewsFocus: WeeklyNewsFocusFixture,
  fallbackAnalysis: AIComprehensiveAnalysisFixture,
  expectedAssetType: AssetType,
  fetcher: Fetcher = fetch
): Promise<SupportedWeeklyNewsResponse> {
  const normalizedTicker = normalizeTicker(ticker);
  const endpoint = assetWeeklyNewsEndpoint(normalizedTicker);
  const response = await fetcher(endpoint);

  if (!response.ok) {
    throw new Error(`Asset weekly-news request failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (!isSupportedWeeklyNewsResponse(payload, normalizedTicker, expectedAssetType)) {
    throw new Error("Asset weekly-news response did not match the expected backend response contract.");
  }

  return {
    weeklyNewsFocus: toWeeklyNewsFocus(payload.weekly_news_focus, fallbackWeeklyNewsFocus),
    aiComprehensiveAnalysis: toAIComprehensiveAnalysis(
      payload.ai_comprehensive_analysis,
      payload.weekly_news_focus,
      fallbackAnalysis
    )
  };
}

function assetWeeklyNewsEndpoint(ticker: string) {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || process.env.API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new Error("No API base URL is configured for supported asset weekly-news fetches.");
  }
  return new URL(`/api/assets/${encodeURIComponent(ticker)}/weekly-news`, apiBaseUrl).toString();
}

function isSupportedWeeklyNewsResponse(
  value: unknown,
  requestedTicker: string,
  expectedAssetType: AssetType
): value is BackendWeeklyNewsResponse {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<BackendWeeklyNewsResponse>;
  return (
    !!candidate.asset &&
    typeof candidate.asset === "object" &&
    candidate.asset.ticker === requestedTicker &&
    candidate.asset.asset_type === expectedAssetType &&
    candidate.asset.supported === true &&
    candidate.asset.status === "supported" &&
    !!candidate.state &&
    typeof candidate.state === "object" &&
    candidate.state.status === "supported" &&
    !!candidate.weekly_news_focus &&
    typeof candidate.weekly_news_focus === "object" &&
    candidate.weekly_news_focus.schema_version === "weekly-news-focus-v1" &&
    !!candidate.ai_comprehensive_analysis &&
    typeof candidate.ai_comprehensive_analysis === "object" &&
    candidate.ai_comprehensive_analysis.schema_version === "ai-comprehensive-analysis-v1" &&
    Array.isArray(candidate.weekly_news_focus.items) &&
    Array.isArray(candidate.weekly_news_focus.citations) &&
    Array.isArray(candidate.weekly_news_focus.source_documents) &&
    Array.isArray(candidate.ai_comprehensive_analysis.sections) &&
    Array.isArray(candidate.ai_comprehensive_analysis.citation_ids) &&
    Array.isArray(candidate.ai_comprehensive_analysis.source_document_ids)
  );
}

function toWeeklyNewsFocus(
  focus: BackendWeeklyNewsFocus,
  fallbackFocus: WeeklyNewsFocusFixture
): WeeklyNewsFocusFixture {
  return {
    schemaVersion: "weekly-news-focus-v1",
    state: focus.state,
    window: {
      asOfDate: focus.window.as_of_date,
      timezone: focus.window.timezone,
      previousMarketWeek: focus.window.previous_market_week,
      currentWeekToDate: focus.window.current_week_to_date,
      newsWindowStart: focus.window.news_window_start,
      newsWindowEnd: focus.window.news_window_end,
      includesCurrentWeekToDate: focus.window.includes_current_week_to_date
    },
    items: focus.items.map((item) => ({
      eventId: item.event_id,
      assetTicker: item.asset_ticker,
      eventType: item.event_type as WeeklyNewsFocusFixture["items"][number]["eventType"],
      title: item.title,
      summary: item.summary,
      eventDate: item.event_date ?? null,
      publishedAt: item.published_at ?? null,
      periodBucket: item.period_bucket,
      citationIds: item.citation_ids,
      source: toWeeklyNewsSource(item.source),
      freshnessState: toFreshnessState(item.freshness_state),
      importanceScore: item.importance_score
    })),
    emptyState: toEmptyState(focus.empty_state, fallbackFocus.emptyState),
    citations: mergeUniqueBy(
      focus.citations.map(toCitation),
      fallbackFocus.citations,
      (citation) => citation.citationId
    ),
    sourceDocuments: mergeUniqueBy(
      focus.source_documents.map(toSourceDocument),
      fallbackFocus.sourceDocuments,
      (source) => source.sourceDocumentId
    ),
    noLiveExternalCalls: true,
    stableFactsAreSeparate: true
  };
}

function toAIComprehensiveAnalysis(
  analysis: BackendAIComprehensiveAnalysis,
  focus: BackendWeeklyNewsFocus,
  fallbackAnalysis: AIComprehensiveAnalysisFixture
): AIComprehensiveAnalysisFixture {
  return {
    schemaVersion: "ai-comprehensive-analysis-v1",
    state: analysis.state,
    analysisAvailable: analysis.analysis_available,
    suppressionReason: analysis.suppression_reason,
    sections: analysis.sections.map((section) => ({
      sectionId: section.section_id,
      label: section.label,
      analysis: section.analysis,
      bullets: section.bullets,
      citationIds: section.citation_ids,
      uncertainty: section.uncertainty
    })),
    citationIds: analysis.citation_ids,
    sourceDocumentIds: analysis.source_document_ids,
    weeklyNewsEventIds: analysis.weekly_news_event_ids,
    canonicalFactCitationIds: analysis.canonical_fact_citation_ids,
    citations: mergeUniqueBy(
      focus.citations.map(toCitation),
      fallbackAnalysis.citations,
      (citation) => citation.citationId
    ),
    sourceDocuments: mergeUniqueBy(
      focus.source_documents.map(toSourceDocument),
      fallbackAnalysis.sourceDocuments,
      (source) => source.sourceDocumentId
    ),
    noLiveExternalCalls: true,
    stableFactsAreSeparate: true
  };
}

function toWeeklyNewsSource(source: BackendSourceDocument): WeeklyNewsFocusFixture["items"][number]["source"] {
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

function toEmptyState(
  emptyState: BackendWeeklyNewsFocus["empty_state"],
  fallbackEmptyState: WeeklyNewsEmptyState | null
): WeeklyNewsEmptyState | null {
  if (!emptyState) {
    return null;
  }

  return {
    state: emptyState.state,
    message: emptyState.message,
    evidenceState: toEvidenceState(emptyState.evidence_state),
    selectedItemCount: emptyState.selected_item_count,
    suppressedCandidateCount: emptyState.suppressed_candidate_count ?? fallbackEmptyState?.suppressedCandidateCount ?? 0
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

function toEvidenceState(value: string): WeeklyNewsEmptyState["evidenceState"] {
  if (
    value === "supported" ||
    value === "mixed" ||
    value === "unknown" ||
    value === "unavailable" ||
    value === "stale" ||
    value === "insufficient_evidence" ||
    value === "no_high_signal" ||
    value === "no_major_recent_development"
  ) {
    return value;
  }
  return "unknown";
}

function toSourceQuality(value: string): WeeklyNewsFocusFixture["items"][number]["source"]["sourceQuality"] {
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

function toAllowlistStatus(value: string): WeeklyNewsFocusFixture["items"][number]["source"]["allowlistStatus"] {
  if (value === "allowed" || value === "rejected" || value === "pending_review" || value === "not_allowlisted") {
    return value;
  }
  return "not_allowlisted";
}

function toSourceUsePolicy(value: string): WeeklyNewsFocusFixture["items"][number]["source"]["sourceUsePolicy"] {
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
