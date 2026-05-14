import {
  marketAIComprehensiveAnalysisFixture,
  marketNewsFocusFixture,
  type Citation,
  type EvidenceState,
  type FreshnessState,
  type GenerationDiagnostics,
  type MarketAIComprehensiveAnalysisFixture,
  type MarketNewsFocusFixture,
  type MarketNewsTopicBucket,
  type SourceAllowlistStatus,
  type SourceDocument,
  type SourceQuality,
  type SourceUsePolicy,
  type WeeklyNewsContractState,
  type WeeklyNewsEvidenceLimitedState
} from "./fixtures";
import { runtimeSectionStatesFromPayload, type RuntimeSectionState } from "./runtimeSectionStates";
import { sanitizeSourceDisplayTitle } from "./sourceDisplay";

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

type BackendMarketNewsFocus = {
  schema_version: "market-news-focus-v1";
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
  configured_max_item_count: number;
  selected_item_count: number;
  suppressed_candidate_count: number;
  evidence_state: string;
  evidence_limited_state: WeeklyNewsEvidenceLimitedState;
  items: Array<{
    story_id: string;
    title: string;
    summary: string;
    published_at: string;
    topic_bucket: MarketNewsTopicBucket;
    entities: string[];
    citation_ids: string[];
    source: BackendSourceDocument;
    freshness_state: string;
    importance_score: number;
    cluster: {
      cluster_id: string;
      representative_article_id: string;
      supporting_sources: string[];
      article_count: number;
      suppressed_duplicate_count: number;
      topic_bucket: MarketNewsTopicBucket;
      critical_claim: boolean;
      corroborated: boolean;
    };
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
  reusable_across_tickers: boolean;
};

type BackendMarketAIComprehensiveAnalysis = {
  schema_version: "market-ai-comprehensive-analysis-v1";
  state: WeeklyNewsContractState;
  analysis_available: boolean;
  minimum_market_news_item_count: number;
  minimum_topic_bucket_count: number;
  market_news_selected_item_count: number;
  selected_topic_bucket_count: number;
  suppression_reason: string | null;
  sections: Array<{
    section_id: MarketAIComprehensiveAnalysisFixture["sections"][number]["sectionId"];
    label: MarketAIComprehensiveAnalysisFixture["sections"][number]["label"];
    analysis: string;
    bullets: string[];
    citation_ids: string[];
    uncertainty: string[];
  }>;
  citation_ids: string[];
  source_document_ids: string[];
  market_news_story_ids: string[];
  no_live_external_calls: boolean;
  stable_facts_are_separate: boolean;
  generation_diagnostics?: BackendGenerationDiagnostics;
};

type BackendGenerationDiagnostics = {
  attempted_live: boolean;
  used_fallback: boolean;
  fallback_reason_codes: string[];
  model_name: string | null;
};

type BackendMarketNewsResponse = {
  schema_version: "market-news-response-v1";
  state: {
    status: string;
  };
  market_news_focus: BackendMarketNewsFocus;
  market_ai_comprehensive_analysis: BackendMarketAIComprehensiveAnalysis;
  section_states?: unknown[];
};

type SupportedMarketNewsResponse = {
  marketNewsFocus: MarketNewsFocusFixture;
  marketAIComprehensiveAnalysis: MarketAIComprehensiveAnalysisFixture;
  sectionStates?: RuntimeSectionState[];
};

export async function fetchMarketNews(
  fallbackFocus: MarketNewsFocusFixture = marketNewsFocusFixture,
  fallbackAnalysis: MarketAIComprehensiveAnalysisFixture = marketAIComprehensiveAnalysisFixture,
  fetcher: Fetcher = fetch
): Promise<SupportedMarketNewsResponse> {
  const response = await fetcher(marketNewsEndpoint());

  if (!response.ok) {
    throw new Error(`Market news request failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (!isSupportedMarketNewsResponse(payload)) {
    throw new Error("Market news response did not match the expected backend response contract.");
  }

  const sectionStates = runtimeSectionStatesFromPayload(payload);

  return {
    marketNewsFocus: toMarketNewsFocus(payload.market_news_focus, fallbackFocus),
    marketAIComprehensiveAnalysis: {
      ...toMarketAIComprehensiveAnalysis(
        payload.market_ai_comprehensive_analysis,
        payload.market_news_focus,
        fallbackAnalysis
      ),
      sectionStates: sectionStates.filter((state) => state.sectionId === "market_ai_comprehensive_analysis")
    },
    sectionStates
  };
}

function marketNewsEndpoint() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || process.env.API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new Error("No API base URL is configured for market-news fetches.");
  }
  return new URL("/api/market-news", apiBaseUrl).toString();
}

function isSupportedMarketNewsResponse(value: unknown): value is BackendMarketNewsResponse {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<BackendMarketNewsResponse>;
  return (
    candidate.schema_version === "market-news-response-v1" &&
    !!candidate.state &&
    typeof candidate.state === "object" &&
    candidate.state.status === "supported" &&
    !!candidate.market_news_focus &&
    typeof candidate.market_news_focus === "object" &&
    candidate.market_news_focus.schema_version === "market-news-focus-v1" &&
    candidate.market_news_focus.reusable_across_tickers === true &&
    typeof candidate.market_news_focus.configured_max_item_count === "number" &&
    typeof candidate.market_news_focus.selected_item_count === "number" &&
    Array.isArray(candidate.market_news_focus.items) &&
    Array.isArray(candidate.market_news_focus.citations) &&
    Array.isArray(candidate.market_news_focus.source_documents) &&
    !!candidate.market_ai_comprehensive_analysis &&
    typeof candidate.market_ai_comprehensive_analysis === "object" &&
    candidate.market_ai_comprehensive_analysis.schema_version === "market-ai-comprehensive-analysis-v1" &&
    typeof candidate.market_ai_comprehensive_analysis.minimum_market_news_item_count === "number" &&
    typeof candidate.market_ai_comprehensive_analysis.minimum_topic_bucket_count === "number" &&
    Array.isArray(candidate.market_ai_comprehensive_analysis.sections) &&
    Array.isArray(candidate.market_ai_comprehensive_analysis.citation_ids) &&
    Array.isArray(candidate.market_ai_comprehensive_analysis.source_document_ids)
  );
}

function toMarketNewsFocus(
  focus: BackendMarketNewsFocus,
  fallbackFocus: MarketNewsFocusFixture
): MarketNewsFocusFixture {
  return {
    schemaVersion: "market-news-focus-v1",
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
    configuredMaxItemCount: focus.configured_max_item_count,
    selectedItemCount: focus.selected_item_count,
    suppressedCandidateCount: focus.suppressed_candidate_count,
    evidenceState: toEvidenceState(focus.evidence_state),
    evidenceLimitedState: focus.evidence_limited_state,
    items: focus.items.map((item) => ({
      storyId: item.story_id,
      title: item.title,
      summary: item.summary,
      publishedAt: item.published_at,
      topicBucket: item.topic_bucket,
      entities: item.entities,
      citationIds: item.citation_ids,
      source: toMarketNewsSource(item.source),
      freshnessState: toFreshnessState(item.freshness_state),
      importanceScore: item.importance_score,
      cluster: {
        clusterId: item.cluster.cluster_id,
        representativeArticleId: item.cluster.representative_article_id,
        supportingSources: item.cluster.supporting_sources,
        articleCount: item.cluster.article_count,
        suppressedDuplicateCount: item.cluster.suppressed_duplicate_count,
        topicBucket: item.cluster.topic_bucket,
        criticalClaim: item.cluster.critical_claim,
        corroborated: item.cluster.corroborated
      }
    })),
    emptyState: focus.empty_state
      ? {
          state: focus.empty_state.state,
          message: focus.empty_state.message,
          evidenceState: toEvidenceState(focus.empty_state.evidence_state),
          selectedItemCount: focus.empty_state.selected_item_count,
          suppressedCandidateCount: focus.empty_state.suppressed_candidate_count
        }
      : null,
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
    noLiveExternalCalls: focus.no_live_external_calls,
    stableFactsAreSeparate: true,
    reusableAcrossTickers: true
  };
}

function toMarketAIComprehensiveAnalysis(
  analysis: BackendMarketAIComprehensiveAnalysis,
  focus: BackendMarketNewsFocus,
  fallbackAnalysis: MarketAIComprehensiveAnalysisFixture
): MarketAIComprehensiveAnalysisFixture {
  return {
    schemaVersion: "market-ai-comprehensive-analysis-v1",
    state: analysis.state,
    analysisAvailable: analysis.analysis_available,
    minimumMarketNewsItemCount: analysis.minimum_market_news_item_count,
    minimumTopicBucketCount: analysis.minimum_topic_bucket_count,
    marketNewsSelectedItemCount: analysis.market_news_selected_item_count,
    selectedTopicBucketCount: analysis.selected_topic_bucket_count,
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
    marketNewsStoryIds: analysis.market_news_story_ids,
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
    generationDiagnostics: toGenerationDiagnostics(analysis.generation_diagnostics),
    noLiveExternalCalls: analysis.no_live_external_calls,
    stableFactsAreSeparate: true
  };
}

function toMarketNewsSource(source: BackendSourceDocument): MarketNewsFocusFixture["items"][number]["source"] {
  return {
    sourceDocumentId: source.source_document_id,
    sourceType: source.source_type,
    title: sanitizeSourceDisplayTitle(source.title, source),
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
    title: sanitizeSourceDisplayTitle(citation.title, {
      source_type: citation.source_document_id,
      source_quality: citation.source_document_id.includes("provider_issuer") ? "issuer" : undefined
    }),
    publisher: citation.publisher,
    freshnessState: toFreshnessState(citation.freshness_state)
  };
}

function toSourceDocument(source: BackendSourceDocument): SourceDocument {
  return {
    sourceDocumentId: source.source_document_id,
    sourceType: source.source_type,
    title: sanitizeSourceDisplayTitle(source.title, source),
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

function toGenerationDiagnostics(
  diagnostics: BackendGenerationDiagnostics | undefined
): GenerationDiagnostics | null {
  if (!diagnostics) {
    return null;
  }
  return {
    attemptedLive: Boolean(diagnostics.attempted_live),
    usedFallback: Boolean(diagnostics.used_fallback),
    fallbackReasonCodes: Array.isArray(diagnostics.fallback_reason_codes) ? diagnostics.fallback_reason_codes : [],
    modelName: diagnostics.model_name ?? null
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
