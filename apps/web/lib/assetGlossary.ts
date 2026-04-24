import { normalizeTicker, type FreshnessState } from "./fixtures";
import { type GlossaryTermKey } from "./glossary";

type Fetcher = typeof fetch;

type GlossaryContextAvailability =
  | "available"
  | "generic_only"
  | "unavailable"
  | "stale"
  | "partial"
  | "unknown"
  | "suppressed"
  | "insufficient_evidence";

type GlossaryEvidenceState =
  | "supported"
  | "partial"
  | "no_major_recent_development"
  | "no_high_signal"
  | "unavailable"
  | "unknown"
  | "stale"
  | "mixed"
  | "insufficient_evidence"
  | "unsupported";

type SourceUsePolicy = "metadata_only" | "link_only" | "summary_allowed" | "full_text_allowed" | "rejected";
type SourceAllowlistStatus = "allowed" | "rejected" | "pending_review" | "not_allowlisted";
type SourceQuality = "official" | "issuer" | "provider" | "fixture" | "allowlisted" | "rejected" | "unknown";

export type AssetGlossarySourceReference = {
  sourceDocumentId: string;
  sourceType: string;
  title: string;
  publisher: string;
  url: string;
  publishedAt: string | null;
  asOfDate: string | null;
  retrievedAt: string;
  freshnessState: FreshnessState;
  isOfficial: boolean;
  sourceQuality: SourceQuality;
  allowlistStatus: SourceAllowlistStatus;
  sourceUsePolicy: SourceUsePolicy;
};

export type AssetGlossaryContext = {
  term: GlossaryTermKey;
  slug: string;
  availabilityState: GlossaryContextAvailability;
  evidenceState: GlossaryEvidenceState;
  freshnessState: FreshnessState;
  contextNote: string | null;
  evidenceReferenceIds: string[];
  citationIds: string[];
  sourceDocumentIds: string[];
  sourceReferences: AssetGlossarySourceReference[];
  uncertaintyLabels: string[];
  suppressionReasons: string[];
};

type BackendAssetIdentity = {
  ticker: string;
  asset_type: string;
  status: string;
  supported: boolean;
};

type BackendGlossaryAssetContext = {
  availability_state: GlossaryContextAvailability;
  evidence_state: GlossaryEvidenceState;
  freshness_state: string;
  context_note: string | null;
  evidence_reference_ids: string[];
  citation_ids: string[];
  source_document_ids: string[];
  uncertainty_labels: string[];
  suppression_reasons: string[];
};

type BackendGlossaryTerm = {
  term_identity: {
    term: string;
    slug: string;
  };
  asset_context: BackendGlossaryAssetContext;
};

type BackendGlossaryCitationBinding = {
  term_slug: string;
  citation_id: string;
  source_document_id: string;
  asset_ticker: string;
  source_use_policy: SourceUsePolicy;
  allowlist_status: SourceAllowlistStatus;
  supports_asset_specific_context: boolean;
};

type BackendGlossarySourceReference = {
  source_document_id: string;
  asset_ticker: string;
  source_type: string;
  title: string;
  publisher: string;
  url: string;
  published_at: string | null;
  as_of_date: string | null;
  retrieved_at: string;
  freshness_state: string;
  is_official: boolean;
  source_quality: SourceQuality;
  allowlist_status: SourceAllowlistStatus;
  source_use_policy: SourceUsePolicy;
};

type BackendGlossaryResponse = {
  schema_version: "glossary-asset-context-v1";
  selected_asset: BackendAssetIdentity;
  state: {
    status: string;
    message: string;
  };
  glossary_state: string;
  terms: BackendGlossaryTerm[];
  citation_bindings: BackendGlossaryCitationBinding[];
  source_references: BackendGlossarySourceReference[];
  diagnostics: {
    no_live_external_calls: boolean;
    live_provider_calls_attempted: boolean;
    live_llm_calls_attempted: boolean;
    generic_definitions_are_not_evidence: boolean;
    same_asset_evidence_only: boolean;
    restricted_text_exposed: boolean;
  };
};

export async function fetchSupportedAssetGlossaryContexts(
  ticker: string,
  terms: readonly GlossaryTermKey[],
  fetcher: Fetcher = fetch
): Promise<Map<GlossaryTermKey, AssetGlossaryContext>> {
  const normalizedTicker = normalizeTicker(ticker);
  const endpoint = assetGlossaryEndpoint(normalizedTicker);
  const response = await fetcher(endpoint);

  if (!response.ok) {
    throw new Error(`Asset glossary request failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (!isGlossaryAssetContextResponse(payload, normalizedTicker)) {
    throw new Error("Asset glossary response did not match the expected backend response contract.");
  }

  const contexts = assetGlossaryContextsByTerm(payload, terms);
  if (contexts.size === 0) {
    throw new Error("Asset glossary response did not include usable same-asset context for rendered terms.");
  }

  return contexts;
}

function assetGlossaryEndpoint(ticker: string) {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || process.env.API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new Error("No API base URL is configured for supported asset glossary fetches.");
  }
  return new URL(`/api/assets/${encodeURIComponent(ticker)}/glossary`, apiBaseUrl).toString();
}

function isGlossaryAssetContextResponse(value: unknown, requestedTicker: string): value is BackendGlossaryResponse {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<BackendGlossaryResponse>;
  return (
    candidate.schema_version === "glossary-asset-context-v1" &&
    !!candidate.selected_asset &&
    typeof candidate.selected_asset === "object" &&
    candidate.selected_asset.ticker === requestedTicker &&
    candidate.selected_asset.supported === true &&
    candidate.state?.status === "supported" &&
    candidate.glossary_state === "available" &&
    Array.isArray(candidate.terms) &&
    Array.isArray(candidate.citation_bindings) &&
    Array.isArray(candidate.source_references) &&
    candidate.diagnostics?.no_live_external_calls === true &&
    candidate.diagnostics.live_provider_calls_attempted === false &&
    candidate.diagnostics.live_llm_calls_attempted === false &&
    candidate.diagnostics.generic_definitions_are_not_evidence === true &&
    candidate.diagnostics.same_asset_evidence_only === true &&
    candidate.diagnostics.restricted_text_exposed === false
  );
}

function assetGlossaryContextsByTerm(
  response: BackendGlossaryResponse,
  renderedTerms: readonly GlossaryTermKey[]
): Map<GlossaryTermKey, AssetGlossaryContext> {
  const requestedTerms = new Set<GlossaryTermKey>(renderedTerms);
  const contexts = new Map<GlossaryTermKey, AssetGlossaryContext>();

  for (const term of response.terms) {
    if (!isRenderedGlossaryTerm(term.term_identity.term, requestedTerms)) {
      continue;
    }

    const renderedTerm = term.term_identity.term as GlossaryTermKey;
    const context = term.asset_context;
    if (context.availability_state === "generic_only") {
      continue;
    }

    const citationIds = context.citation_ids.filter((citationId) =>
      hasSameAssetAllowedBinding(response, term.term_identity.slug, citationId)
    );
    if (context.citation_ids.length > 0 && citationIds.length !== context.citation_ids.length) {
      continue;
    }

    const sourceDocumentIds = new Set(context.source_document_ids);
    const sourceReferences = response.source_references
      .filter(
        (source) =>
          source.asset_ticker === response.selected_asset.ticker &&
          sourceDocumentIds.has(source.source_document_id) &&
          source.allowlist_status === "allowed" &&
          (source.source_use_policy === "summary_allowed" || source.source_use_policy === "full_text_allowed")
      )
      .map(toSourceReference);
    const uncertaintyLabels = [...context.uncertainty_labels];

    if (citationIds.length === 0 && uncertaintyLabels.length === 0 && context.suppression_reasons.length === 0) {
      continue;
    }

    contexts.set(renderedTerm, {
      term: renderedTerm,
      slug: term.term_identity.slug,
      availabilityState: context.availability_state,
      evidenceState: context.evidence_state,
      freshnessState: toFreshnessState(context.freshness_state),
      contextNote: context.context_note,
      evidenceReferenceIds: context.evidence_reference_ids,
      citationIds,
      sourceDocumentIds: [...sourceDocumentIds],
      sourceReferences,
      uncertaintyLabels,
      suppressionReasons: context.suppression_reasons
    });
  }

  return contexts;
}

function hasSameAssetAllowedBinding(response: BackendGlossaryResponse, termSlug: string, citationId: string) {
  return response.citation_bindings.some(
    (binding) =>
      binding.term_slug === termSlug &&
      binding.citation_id === citationId &&
      binding.asset_ticker === response.selected_asset.ticker &&
      binding.supports_asset_specific_context === true &&
      binding.allowlist_status === "allowed" &&
      (binding.source_use_policy === "summary_allowed" || binding.source_use_policy === "full_text_allowed")
  );
}

function isRenderedGlossaryTerm(term: string, renderedTerms: Set<GlossaryTermKey>): term is GlossaryTermKey {
  return renderedTerms.has(term as GlossaryTermKey);
}

function toSourceReference(source: BackendGlossarySourceReference): AssetGlossarySourceReference {
  return {
    sourceDocumentId: source.source_document_id,
    sourceType: source.source_type,
    title: source.title,
    publisher: source.publisher,
    url: source.url,
    publishedAt: source.published_at,
    asOfDate: source.as_of_date,
    retrievedAt: source.retrieved_at,
    freshnessState: toFreshnessState(source.freshness_state),
    isOfficial: source.is_official,
    sourceQuality: source.source_quality,
    allowlistStatus: source.allowlist_status,
    sourceUsePolicy: source.source_use_policy
  };
}

function toFreshnessState(value: string): FreshnessState {
  if (value === "fresh" || value === "stale" || value === "unknown" || value === "unavailable") {
    return value;
  }
  return "unknown";
}
