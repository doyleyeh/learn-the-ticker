import { normalizeTicker, type CitationContext, type SourceDrawerSourceDocument } from "./fixtures";

type Fetcher = typeof fetch;

export type SourceDrawerState =
  | "available"
  | "unsupported"
  | "out_of_scope"
  | "unknown"
  | "eligible_not_cached"
  | "deleted"
  | "stale"
  | "partial"
  | "unavailable"
  | "insufficient_evidence";

export type SourceDrawerRenderableDocument = SourceDrawerSourceDocument & {
  allowedExcerptNote?: string | null;
};

export type SourceDrawerListEntry = {
  source: SourceDrawerRenderableDocument;
  claim: string;
  contexts: CitationContext[];
  drawerState: SourceDrawerState;
};

export type SourceDrawerContractData = {
  drawerState: SourceDrawerState;
  entries: SourceDrawerListEntry[];
};

type BackendAssetIdentity = {
  ticker: string;
  name: string;
  asset_type: string;
  exchange: string | null;
  issuer: string | null;
  status: string;
  supported: boolean;
};

type BackendPermittedOperations = {
  can_export_full_text: boolean;
};

type BackendSourceDrawerExcerpt = {
  excerpt_id: string;
  source_document_id: string;
  citation_id: string | null;
  chunk_id: string | null;
  text: string | null;
  source_use_policy: string;
  allowlist_status: string;
  freshness_state: string;
  excerpt_allowed: boolean;
  suppression_reason: string | null;
  note: string;
};

type BackendSourceDrawerSourceGroup = {
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
  source_quality: string;
  allowlist_status: string;
  source_use_policy: string;
  permitted_operations: BackendPermittedOperations;
  citation_ids: string[];
  related_claim_ids: string[];
  section_ids: string[];
  allowed_excerpts: BackendSourceDrawerExcerpt[];
};

type BackendSourceDrawerRelatedClaim = {
  claim_id: string;
  claim_text: string;
  citation_ids: string[];
  source_document_ids: string[];
  section_id: string | null;
  section_title: string | null;
};

type BackendSourceDrawerCitationBinding = {
  citation_id: string;
  source_document_id: string;
  section_ids: string[];
};

type BackendSourceDrawerSectionReference = {
  section_id: string;
  section_title: string;
};

type BackendAssetSourceDrawerResponse = {
  schema_version: "asset-source-drawer-v1";
  asset: BackendAssetIdentity;
  selected_asset: BackendAssetIdentity | null;
  drawer_state: string;
  source_groups: BackendSourceDrawerSourceGroup[];
  citation_bindings: BackendSourceDrawerCitationBinding[];
  related_claims: BackendSourceDrawerRelatedClaim[];
  section_references: BackendSourceDrawerSectionReference[];
};

export async function fetchSupportedSourceDrawerResponse(
  ticker: string,
  fetcher: Fetcher = fetch
): Promise<SourceDrawerContractData> {
  const normalizedTicker = normalizeTicker(ticker);
  const endpoint = sourceDrawerEndpoint(normalizedTicker);
  const response = await fetcher(endpoint);

  if (!response.ok) {
    throw new Error(`Source drawer request failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (!isAssetSourceDrawerResponse(payload, normalizedTicker)) {
    throw new Error("Source drawer response did not match the expected backend response contract.");
  }

  return toSourceDrawerContractData(payload);
}

function sourceDrawerEndpoint(ticker: string) {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || process.env.API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new Error("No API base URL is configured for supported source-drawer fetches.");
  }
  return new URL(`/api/assets/${encodeURIComponent(ticker)}/sources`, apiBaseUrl).toString();
}

function isAssetSourceDrawerResponse(value: unknown, requestedTicker: string): value is BackendAssetSourceDrawerResponse {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<BackendAssetSourceDrawerResponse>;
  const selectedTicker = candidate.selected_asset?.ticker ?? candidate.asset?.ticker;
  return (
    candidate.schema_version === "asset-source-drawer-v1" &&
    typeof candidate.drawer_state === "string" &&
    !!candidate.asset &&
    typeof candidate.asset === "object" &&
    typeof candidate.asset.ticker === "string" &&
    selectedTicker === requestedTicker &&
    Array.isArray(candidate.source_groups) &&
    Array.isArray(candidate.citation_bindings) &&
    Array.isArray(candidate.related_claims) &&
    Array.isArray(candidate.section_references)
  );
}

function toSourceDrawerContractData(response: BackendAssetSourceDrawerResponse): SourceDrawerContractData {
  const sectionTitlesById = new Map(
    response.section_references.map((sectionReference) => [sectionReference.section_id, sectionReference.section_title])
  );
  const bindingsByCitationId = new Map(
    response.citation_bindings.map((binding) => [binding.citation_id, binding])
  );
  const claimsById = new Map(response.related_claims.map((claim) => [claim.claim_id, claim]));
  const entries = response.source_groups.map((group) => {
    const contexts = contextsForSourceGroup(group, claimsById, bindingsByCitationId, sectionTitlesById);
    const relatedClaims = group.related_claim_ids
      .map((claimId) => claimsById.get(claimId))
      .filter((claim): claim is BackendSourceDrawerRelatedClaim => Boolean(claim));
    const primaryExcerpt = group.allowed_excerpts.find((excerpt) => typeof excerpt.text === "string" && excerpt.text.length > 0);

    return {
      source: {
        sourceDocumentId: group.source_document_id,
        sourceType: group.source_type,
        title: group.title,
        publisher: group.publisher,
        url: group.url,
        publishedAt: group.published_at ?? "Unknown",
        asOfDate: group.as_of_date ?? undefined,
        retrievedAt: group.retrieved_at,
        freshnessState: toFreshnessState(group.freshness_state),
        isOfficial: group.is_official,
        supportingPassage: primaryExcerpt?.text ?? "",
        sourceQuality: toSourceQuality(group.source_quality),
        allowlistStatus: toAllowlistStatus(group.allowlist_status),
        sourceUsePolicy: toSourceUsePolicy(group.source_use_policy),
        permitted_operations: {
          can_export_full_text: group.permitted_operations.can_export_full_text
        },
        source_document_id: group.source_document_id,
        source_type: group.source_type,
        published_at: group.published_at,
        as_of_date: group.as_of_date,
        retrieved_at: group.retrieved_at,
        freshness_state: toFreshnessState(group.freshness_state),
        source_quality: toSourceQuality(group.source_quality),
        allowlist_status: toAllowlistStatus(group.allowlist_status),
        source_use_policy: toSourceUsePolicy(group.source_use_policy),
        allowedExcerptNote: primaryExcerpt?.note ?? null
      },
      claim:
        contexts[0]?.claimContext ??
        relatedClaims[0]?.claim_text ??
        `${group.title} is included in this backend-aligned deterministic source list.`,
      contexts,
      drawerState: sourceDrawerStateFromFreshness(group.freshness_state)
    };
  });

  return {
    drawerState: sourceDrawerStateFromContract(response.drawer_state),
    entries
  };
}

function contextsForSourceGroup(
  group: BackendSourceDrawerSourceGroup,
  claimsById: Map<string, BackendSourceDrawerRelatedClaim>,
  bindingsByCitationId: Map<string, BackendSourceDrawerCitationBinding>,
  sectionTitlesById: Map<string, string>
): CitationContext[] {
  const allowedExcerptByCitationId = new Map(
    group.allowed_excerpts
      .filter((excerpt) => excerpt.citation_id && typeof excerpt.text === "string" && excerpt.text.length > 0)
      .map((excerpt) => [excerpt.citation_id as string, excerpt.text as string])
  );
  const defaultExcerpt =
    group.allowed_excerpts.find((excerpt) => typeof excerpt.text === "string" && excerpt.text.length > 0)?.text ?? "";
  const seen = new Set<string>();
  const contexts: CitationContext[] = [];

  for (const claimId of group.related_claim_ids) {
    const claim = claimsById.get(claimId);
    if (!claim) {
      continue;
    }

    const citationIds = claim.citation_ids.filter((citationId) => group.citation_ids.includes(citationId));
    for (const citationId of citationIds) {
      const binding = bindingsByCitationId.get(citationId);
      const sectionId = claim.section_id ?? binding?.section_ids[0] ?? group.section_ids[0] ?? claim.claim_id;
      const sectionTitle =
        claim.section_title ??
        (binding?.section_ids[0] ? sectionTitlesById.get(binding.section_ids[0]) : undefined) ??
        "Related claim";
      const supportingPassage = allowedExcerptByCitationId.get(citationId) ?? defaultExcerpt;
      const dedupeKey = [group.source_document_id, citationId, sectionId, claim.claim_text].join("::");

      if (seen.has(dedupeKey)) {
        continue;
      }
      seen.add(dedupeKey);
      contexts.push({
        citationId,
        sourceDocumentId: group.source_document_id,
        sectionId,
        sectionTitle,
        claimContext: claim.claim_text,
        supportingPassage
      });
    }
  }

  return contexts;
}

function sourceDrawerStateFromContract(drawerState: string): SourceDrawerState {
  if (
    drawerState === "available" ||
    drawerState === "unsupported" ||
    drawerState === "out_of_scope" ||
    drawerState === "unknown" ||
    drawerState === "eligible_not_cached" ||
    drawerState === "deleted" ||
    drawerState === "stale" ||
    drawerState === "partial" ||
    drawerState === "unavailable" ||
    drawerState === "insufficient_evidence"
  ) {
    return drawerState;
  }
  return "unknown";
}

function sourceDrawerStateFromFreshness(freshnessState: string): SourceDrawerState {
  if (freshnessState === "fresh") {
    return "available";
  }
  if (freshnessState === "stale") {
    return "stale";
  }
  if (freshnessState === "unknown") {
    return "unknown";
  }
  if (freshnessState === "unavailable") {
    return "unavailable";
  }
  if (freshnessState === "partial") {
    return "partial";
  }
  if (freshnessState === "insufficient_evidence") {
    return "insufficient_evidence";
  }
  return "unknown";
}

function toFreshnessState(value: string): SourceDrawerSourceDocument["freshness_state"] {
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

function toSourceQuality(value: string): SourceDrawerSourceDocument["source_quality"] {
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

function toAllowlistStatus(value: string): SourceDrawerSourceDocument["allowlist_status"] {
  if (value === "allowed" || value === "rejected" || value === "pending_review" || value === "not_allowlisted") {
    return value;
  }
  return "not_allowlisted";
}

function toSourceUsePolicy(value: string): SourceDrawerSourceDocument["source_use_policy"] {
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
