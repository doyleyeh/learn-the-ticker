import { publicApiEndpoint, requiredApiEndpoint } from "./apiEndpoints";

export type ExportFormat = "markdown";

type Fetcher = typeof fetch;

export type AssetExportContractRendering = "backend_contract" | "local_fallback";

export type ExportResponsePreview = {
  export_state: "available" | "unsupported" | "unavailable";
  rendered_markdown: string;
  contractSource: "session_contract" | "single_turn_fallback";
  conversationIdPresent: boolean;
  selectedTicker: string;
  sessionLifecycleState: string;
  sessionExportAvailable: boolean;
  sessionExpiresAt: string;
  validationSchemaVersion: "export-validation-v1" | "local_fallback";
  bindingScope: "same_asset" | "no_factual_evidence" | "unavailable" | "local_fallback";
  citationCount: number;
  sourceCount: number;
  sourceFromSafeSessionRecords: boolean;
  usedExistingChatContract: boolean;
  noLiveExternalCalls: boolean;
};

export type AssetExportContractValidation = {
  rendering: AssetExportContractRendering;
  contentType: "asset_page" | "asset_source_list" | "comparison";
  exportState: "available";
  title: string;
  citationCount: number;
  sourceCount: number;
  sectionCount: number;
  freshnessState: string;
  asOfDate: string;
  validationSchemaVersion: "export-validation-v1";
  bindingScope: "same_asset" | "same_comparison_pack";
  leftTicker?: string;
  rightTicker?: string;
  comparisonId?: string;
};

export const EXPORT_FORMAT: ExportFormat = "markdown";

export const EXPORT_TRUST_CONTEXT =
  "Saved output uses backend export payloads with citation IDs, source metadata, freshness/as-of dates, the educational disclaimer, and licensing scope.";

export const EXPORT_LICENSING_CONTEXT =
  "Export controls request Markdown-shaped payloads only; full source documents, restricted provider payloads, raw model reasoning, hidden prompts, credentials, and live external download URLs are not exported.";

export function assetPageExportUrl(ticker: string, exportFormat: ExportFormat = EXPORT_FORMAT): string {
  const encodedTicker = encodeTicker(ticker);
  return publicApiEndpoint(`/api/assets/${encodedTicker}/export?export_format=${exportFormat}`);
}

export function assetSourceListExportUrl(ticker: string, exportFormat: ExportFormat = EXPORT_FORMAT): string {
  const encodedTicker = encodeTicker(ticker);
  return publicApiEndpoint(`/api/assets/${encodedTicker}/sources/export?export_format=${exportFormat}`);
}

export async function fetchSupportedAssetExportContract(
  ticker: string,
  contentType: "asset_page" | "asset_source_list",
  fetcher: Fetcher = fetch
): Promise<AssetExportContractValidation> {
  const normalizedTicker = normalizeTicker(ticker);
  const endpoint =
    contentType === "asset_page"
      ? assetExportEndpoint(normalizedTicker, assetPageExportUrl(normalizedTicker))
      : assetExportEndpoint(normalizedTicker, assetSourceListExportUrl(normalizedTicker));
  const response = await fetcher(endpoint);

  if (!response.ok) {
    throw new Error(`Asset export request failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (!isSupportedSameAssetMarkdownExport(payload, normalizedTicker, contentType)) {
    throw new Error("Asset export response did not match the supported same-asset Markdown export contract.");
  }

  const freshness = payload.freshness;

  return {
    rendering: "backend_contract",
    contentType,
    exportState: "available",
    title: payload.title,
    citationCount: payload.citations.length,
    sourceCount: payload.source_documents.length,
    sectionCount: payload.sections.length,
    freshnessState: freshness.freshness_state,
    asOfDate:
      freshness.facts_as_of ??
      freshness.holdings_as_of ??
      freshness.recent_events_as_of ??
      freshness.page_last_updated_at,
    validationSchemaVersion: "export-validation-v1",
    bindingScope: "same_asset"
  };
}

export function comparisonExportUrl(
  leftTicker: string,
  rightTicker: string,
  exportFormat: ExportFormat = EXPORT_FORMAT
): string {
  const params = new URLSearchParams({
    left_ticker: normalizeTicker(leftTicker),
    right_ticker: normalizeTicker(rightTicker),
    export_format: exportFormat
  });

  return publicApiEndpoint(`/api/compare/export?${params.toString()}`);
}

export async function fetchSupportedComparisonExportContract(
  leftTicker: string,
  rightTicker: string,
  fetcher: Fetcher = fetch
): Promise<AssetExportContractValidation> {
  const normalizedLeftTicker = normalizeTicker(leftTicker);
  const normalizedRightTicker = normalizeTicker(rightTicker);
  const relativeUrl = comparisonExportUrl(normalizedLeftTicker, normalizedRightTicker);
  const response = await fetcher(
    exportEndpoint(relativeUrl, "No API base URL is configured for supported comparison export contract fetches.")
  );

  if (!response.ok) {
    throw new Error(`Comparison export request failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (!isSupportedSameComparisonPackMarkdownExport(payload, normalizedLeftTicker, normalizedRightTicker)) {
    throw new Error("Comparison export response did not match the supported same-comparison-pack Markdown export contract.");
  }

  const freshness = comparisonExportFreshness(payload);
  const leftAsset = payload.left_asset!;
  const rightAsset = payload.right_asset!;
  const exportValidation = payload.export_validation!;

  return {
    rendering: "backend_contract",
    contentType: "comparison",
    exportState: "available",
    title: payload.title,
    citationCount: payload.citations.length,
    sourceCount: payload.source_documents.length,
    sectionCount: payload.sections.length,
    freshnessState: freshness.freshnessState,
    asOfDate: freshness.asOfDate,
    validationSchemaVersion: "export-validation-v1",
    bindingScope: "same_comparison_pack",
    leftTicker: leftAsset.ticker,
    rightTicker: rightAsset.ticker,
    comparisonId:
      exportValidation.citation_bindings[0]?.comparison_id ??
      exportValidation.source_bindings[0]?.comparison_id ??
      undefined
  };
}

export function chatTranscriptExportUrl(ticker: string): string {
  return publicApiEndpoint(`/api/assets/${encodeTicker(ticker)}/chat/export`);
}

export async function postChatTranscriptExport(
  ticker: string,
  question: string,
  conversationIdOrFetcher?: string | null | Fetcher,
  fetcher: Fetcher = fetch
): Promise<ExportResponsePreview> {
  const conversationId =
    typeof conversationIdOrFetcher === "function" ? null : conversationIdOrFetcher ?? null;
  const resolvedFetcher = typeof conversationIdOrFetcher === "function" ? conversationIdOrFetcher : fetcher;
  if (conversationId) {
    try {
      const sessionResponse = await postChatTranscriptExportRequest(ticker, question, resolvedFetcher, conversationId);
      if (isSupportedChatSessionMarkdownExport(sessionResponse, normalizeTicker(ticker), conversationId)) {
        return chatExportResponsePreview(sessionResponse, "session_contract");
      }
    } catch {
      // Preserve the existing single-turn transcript export fallback when the accountless session export is unavailable.
    }
  }

  const fallbackResponse = await postChatTranscriptExportRequest(ticker, question, resolvedFetcher);
  if (isChatTranscriptExportPreview(fallbackResponse, normalizeTicker(ticker))) {
    return chatExportResponsePreview(fallbackResponse, "single_turn_fallback");
  }

  throw new Error("Chat transcript export did not match the expected local API shape.");
}

async function postChatTranscriptExportRequest(
  ticker: string,
  question: string,
  fetcher: Fetcher,
  conversationId?: string
): Promise<unknown> {
  const endpoint = chatTranscriptExportUrl(ticker);
  const response = await fetcher(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question,
      ...(conversationId ? { conversation_id: conversationId } : {}),
      export_format: EXPORT_FORMAT
    })
  });

  if (!response.ok) {
    throw new Error(`Chat transcript export failed with status ${response.status}`);
  }

  return response.json();
}

function normalizeTicker(ticker: string): string {
  return ticker.trim().toUpperCase();
}

function assetExportEndpoint(_ticker: string, relativeUrl: string) {
  return exportEndpoint(relativeUrl, "No API base URL is configured for supported asset export contract fetches.");
}

function exportEndpoint(
  relativeUrl: string,
  missingApiBaseMessage = "No API base URL is configured for supported export contract fetches."
) {
  return requiredApiEndpoint(relativeUrl, missingApiBaseMessage);
}

function encodeTicker(ticker: string): string {
  return encodeURIComponent(normalizeTicker(ticker));
}

type BackendExportContract = {
  content_type: "asset_page" | "asset_source_list";
  export_format: string;
  export_state: string;
  title: string;
  state: {
    status: string;
    message: string;
  };
  asset: {
    ticker: string;
    status: string;
    supported: boolean;
  } | null;
  freshness: {
    page_last_updated_at: string;
    facts_as_of?: string | null;
    holdings_as_of?: string | null;
    recent_events_as_of?: string | null;
    freshness_state: string;
  };
  sections: Array<{
    section_id: string;
    freshness_state?: string | null;
    evidence_state?: string | null;
    as_of_date?: string | null;
    retrieved_at?: string | null;
  }>;
  citations: Array<{
    citation_id: string;
    source_document_id: string;
    freshness_state?: string | null;
  }>;
  source_documents: Array<{
    source_document_id: string;
    title: string;
    source_type: string;
    publisher: string;
    url: string;
    published_at?: string | null;
    as_of_date?: string | null;
    retrieved_at: string;
    freshness_state: string;
    allowlist_status: string;
    source_use_policy: string;
    permitted_operations?: {
      can_export_full_text?: boolean;
    };
    allowed_excerpt?: {
      note?: string;
      redistribution_allowed?: boolean;
      source_use_policy?: string;
      allowlist_status?: string;
    } | null;
  }>;
  disclaimer: string;
  licensing_note: {
    note_id: string;
    text: string;
  };
  rendered_markdown: string;
  export_validation: {
    schema_version: string;
    content_type: string;
    export_state: string;
    binding_scope: string;
    citation_bindings: Array<{
      citation_id: string;
      source_document_id: string;
      asset_ticker?: string | null;
      supports_exported_content?: boolean;
    }>;
    source_bindings: Array<{
      source_document_id: string;
      asset_ticker?: string | null;
      source_use_policy: string;
      allowlist_status: string;
    }>;
    section_validations: Array<{
      section_id: string;
      displayed_freshness_state?: string | null;
      displayed_as_of_date?: string | null;
      displayed_retrieved_at?: string | null;
      validated_freshness_state?: string | null;
      validated_as_of_date?: string | null;
      validated_retrieved_at?: string | null;
    }>;
    diagnostics: {
      no_live_external_calls?: boolean;
      same_asset_citation_bindings_only?: boolean;
      same_asset_source_bindings_only?: boolean;
      used_existing_overview_contract?: boolean;
      no_new_facts_or_dates?: boolean;
      empty_factual_evidence_export?: boolean;
    };
  } | null;
};

type ExportValidationSection = NonNullable<BackendExportContract["export_validation"]>["section_validations"][number];

type BackendComparisonExportContract = {
  content_type: "comparison";
  export_format: string;
  export_state: string;
  title: string;
  state: {
    status: string;
    message: string;
  };
  left_asset: {
    ticker: string;
    status: string;
    supported: boolean;
  } | null;
  right_asset: {
    ticker: string;
    status: string;
    supported: boolean;
  } | null;
  sections: Array<{
    section_id: string;
    freshness_state?: string | null;
    evidence_state?: string | null;
    as_of_date?: string | null;
    retrieved_at?: string | null;
  }>;
  citations: Array<{
    citation_id: string;
    source_document_id: string;
    freshness_state?: string | null;
  }>;
  source_documents: BackendExportContract["source_documents"];
  disclaimer: string;
  licensing_note: {
    note_id: string;
    text: string;
  };
  rendered_markdown: string;
  metadata?: {
    comparison_type?: string;
    source?: string;
    generated_comparison_output?: boolean;
  };
  export_validation: {
    schema_version: string;
    content_type: string;
    export_state: string;
    binding_scope: string;
    citation_bindings: Array<{
      citation_id: string;
      source_document_id: string;
      asset_ticker?: string | null;
      comparison_id?: string | null;
      supports_exported_content?: boolean;
    }>;
    source_bindings: Array<{
      source_document_id: string;
      asset_ticker?: string | null;
      comparison_id?: string | null;
      source_use_policy: string;
      allowlist_status: string;
    }>;
    section_validations: ExportValidationSection[];
    diagnostics: {
      no_live_external_calls?: boolean;
      same_comparison_pack_citation_bindings_only?: boolean;
      same_comparison_pack_source_bindings_only?: boolean;
      used_existing_comparison_contract?: boolean;
      no_new_facts_or_dates?: boolean;
      empty_factual_evidence_export?: boolean;
    };
  } | null;
};

type BackendChatTranscriptExportContract = {
  content_type: "chat_transcript";
  export_format: string;
  export_state: string;
  title: string;
  state: {
    status: string;
    message: string;
  };
  asset: {
    ticker: string;
    status: string;
    supported: boolean;
  } | null;
  sections: Array<{
    section_id: string;
    freshness_state?: string | null;
    evidence_state?: string | null;
    as_of_date?: string | null;
    retrieved_at?: string | null;
    items?: Array<{
      metadata?: Record<string, unknown> | null;
    }>;
  }>;
  citations: BackendExportContract["citations"];
  source_documents: BackendExportContract["source_documents"];
  disclaimer: string;
  licensing_note: {
    note_id: string;
    text: string;
  };
  rendered_markdown: string;
  metadata: {
    conversation_id?: string | null;
    session_lifecycle_state?: string | null;
    selected_ticker?: string | null;
    expires_at?: string | null;
    export_available?: boolean;
    source?: string | null;
    generated_chat_answer?: boolean;
    safety_classification?: string | null;
    compare_route_suggestion?: unknown;
    compare_route_suggestions?: unknown;
  };
  export_validation: {
    schema_version: string;
    content_type: string;
    export_state: string;
    binding_scope: string;
    citation_bindings: Array<{
      citation_id: string;
      source_document_id: string;
      asset_ticker?: string | null;
      supports_exported_content?: boolean;
      scope?: string;
    }>;
    source_bindings: Array<{
      source_document_id: string;
      asset_ticker?: string | null;
      source_use_policy: string;
      allowlist_status: string;
    }>;
    section_validations: ExportValidationSection[];
    diagnostics: {
      no_live_external_calls?: boolean;
      same_asset_citation_bindings_only?: boolean;
      same_asset_source_bindings_only?: boolean;
      used_existing_chat_contract?: boolean;
      no_new_facts_or_dates?: boolean;
      empty_factual_evidence_export?: boolean;
      limitation_reasons?: string[];
    };
  } | null;
};

function isSupportedSameAssetMarkdownExport(
  value: unknown,
  requestedTicker: string,
  expectedContentType: "asset_page" | "asset_source_list"
): value is BackendExportContract {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<BackendExportContract>;
  if (
    candidate.content_type !== expectedContentType ||
    candidate.export_format !== EXPORT_FORMAT ||
    candidate.export_state !== "available" ||
    typeof candidate.title !== "string" ||
    !candidate.asset ||
    candidate.asset.ticker !== requestedTicker ||
    candidate.asset.status !== "supported" ||
    candidate.asset.supported !== true ||
    !candidate.freshness ||
    typeof candidate.freshness.page_last_updated_at !== "string" ||
    typeof candidate.freshness.freshness_state !== "string" ||
    !hasAsOfMetadata(candidate.freshness) ||
    !Array.isArray(candidate.sections) ||
    candidate.sections.length === 0 ||
    !Array.isArray(candidate.citations) ||
    candidate.citations.length === 0 ||
    !candidate.citations.every(isExportCitation) ||
    !Array.isArray(candidate.source_documents) ||
    candidate.source_documents.length === 0 ||
    !candidate.source_documents.every(isExportSourceMetadata) ||
    typeof candidate.disclaimer !== "string" ||
    !candidate.disclaimer.toLowerCase().includes("educational") ||
    !candidate.licensing_note ||
    candidate.licensing_note.note_id !== "export_licensing_scope" ||
    typeof candidate.licensing_note.text !== "string" ||
    !candidate.licensing_note.text.toLowerCase().includes("source attribution") ||
    typeof candidate.rendered_markdown !== "string" ||
    !candidate.rendered_markdown.includes("Educational Disclaimer") ||
    !candidate.export_validation ||
    candidate.export_validation.schema_version !== "export-validation-v1" ||
    candidate.export_validation.content_type !== expectedContentType ||
    candidate.export_validation.export_state !== "available" ||
    candidate.export_validation.binding_scope !== "same_asset" ||
    !Array.isArray(candidate.export_validation.citation_bindings) ||
    candidate.export_validation.citation_bindings.length === 0 ||
    !Array.isArray(candidate.export_validation.source_bindings) ||
    candidate.export_validation.source_bindings.length === 0 ||
    !Array.isArray(candidate.export_validation.section_validations) ||
    candidate.export_validation.section_validations.length === 0 ||
    !candidate.export_validation.diagnostics.no_live_external_calls ||
    !candidate.export_validation.diagnostics.same_asset_source_bindings_only ||
    !candidate.export_validation.diagnostics.used_existing_overview_contract ||
    !candidate.export_validation.diagnostics.no_new_facts_or_dates ||
    candidate.export_validation.diagnostics.empty_factual_evidence_export === true
  ) {
    return false;
  }

  const citationIds = new Set(candidate.citations.map((citation) => citation.citation_id));
  const sourceIds = new Set(candidate.source_documents.map((source) => source.source_document_id));
  return (
    candidate.citations.every((citation) => sourceIds.has(citation.source_document_id)) &&
    candidate.export_validation.citation_bindings.every(
      (binding) =>
        citationIds.has(binding.citation_id) &&
        sourceIds.has(binding.source_document_id) &&
        (binding.asset_ticker === undefined || binding.asset_ticker === null || binding.asset_ticker === requestedTicker)
    ) &&
    candidate.export_validation.source_bindings.every(
      (binding) =>
        sourceIds.has(binding.source_document_id) &&
        (binding.asset_ticker === undefined || binding.asset_ticker === null || binding.asset_ticker === requestedTicker) &&
        isExportableSourceUsePolicy(binding.source_use_policy) &&
        binding.allowlist_status === "allowed"
    ) &&
    candidate.export_validation.section_validations.some(
      (section) =>
        typeof section.displayed_freshness_state === "string" ||
        typeof section.validated_freshness_state === "string" ||
        typeof section.displayed_as_of_date === "string" ||
        typeof section.validated_as_of_date === "string" ||
        typeof section.displayed_retrieved_at === "string" ||
        typeof section.validated_retrieved_at === "string"
    )
  );
}

function isSupportedSameComparisonPackMarkdownExport(
  value: unknown,
  requestedLeftTicker: string,
  requestedRightTicker: string
): value is BackendComparisonExportContract {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<BackendComparisonExportContract>;
  if (
    candidate.content_type !== "comparison" ||
    candidate.export_format !== EXPORT_FORMAT ||
    candidate.export_state !== "available" ||
    typeof candidate.title !== "string" ||
    !candidate.left_asset ||
    candidate.left_asset.ticker !== requestedLeftTicker ||
    candidate.left_asset.status !== "supported" ||
    candidate.left_asset.supported !== true ||
    !candidate.right_asset ||
    candidate.right_asset.ticker !== requestedRightTicker ||
    candidate.right_asset.status !== "supported" ||
    candidate.right_asset.supported !== true ||
    !Array.isArray(candidate.sections) ||
    candidate.sections.length === 0 ||
    !Array.isArray(candidate.citations) ||
    candidate.citations.length === 0 ||
    !candidate.citations.every(isExportCitation) ||
    !Array.isArray(candidate.source_documents) ||
    candidate.source_documents.length === 0 ||
    !candidate.source_documents.every(isExportSourceMetadata) ||
    typeof candidate.disclaimer !== "string" ||
    !candidate.disclaimer.toLowerCase().includes("educational") ||
    !candidate.licensing_note ||
    candidate.licensing_note.note_id !== "export_licensing_scope" ||
    typeof candidate.licensing_note.text !== "string" ||
    !candidate.licensing_note.text.toLowerCase().includes("source attribution") ||
    typeof candidate.rendered_markdown !== "string" ||
    !candidate.rendered_markdown.includes("Educational Disclaimer") ||
    !candidate.export_validation ||
    candidate.export_validation.schema_version !== "export-validation-v1" ||
    candidate.export_validation.content_type !== "comparison" ||
    candidate.export_validation.export_state !== "available" ||
    candidate.export_validation.binding_scope !== "same_comparison_pack" ||
    !Array.isArray(candidate.export_validation.citation_bindings) ||
    candidate.export_validation.citation_bindings.length === 0 ||
    !Array.isArray(candidate.export_validation.source_bindings) ||
    candidate.export_validation.source_bindings.length === 0 ||
    !Array.isArray(candidate.export_validation.section_validations) ||
    candidate.export_validation.section_validations.length === 0 ||
    !candidate.export_validation.diagnostics.no_live_external_calls ||
    !candidate.export_validation.diagnostics.same_comparison_pack_citation_bindings_only ||
    !candidate.export_validation.diagnostics.same_comparison_pack_source_bindings_only ||
    !candidate.export_validation.diagnostics.used_existing_comparison_contract ||
    !candidate.export_validation.diagnostics.no_new_facts_or_dates ||
    candidate.export_validation.diagnostics.empty_factual_evidence_export === true
  ) {
    return false;
  }

  const requestedTickers = new Set([requestedLeftTicker, requestedRightTicker]);
  const citationIds = new Set(candidate.citations.map((citation) => citation.citation_id));
  const sourceIds = new Set(candidate.source_documents.map((source) => source.source_document_id));
  return (
    candidate.citations.every((citation) => sourceIds.has(citation.source_document_id)) &&
    candidate.export_validation.citation_bindings.every(
      (binding) =>
        citationIds.has(binding.citation_id) &&
        sourceIds.has(binding.source_document_id) &&
        typeof binding.comparison_id === "string" &&
        binding.comparison_id.length > 0 &&
        (binding.asset_ticker === undefined || binding.asset_ticker === null || requestedTickers.has(binding.asset_ticker))
    ) &&
    candidate.export_validation.source_bindings.every(
      (binding) =>
        sourceIds.has(binding.source_document_id) &&
        typeof binding.comparison_id === "string" &&
        binding.comparison_id.length > 0 &&
        (binding.asset_ticker === undefined || binding.asset_ticker === null || requestedTickers.has(binding.asset_ticker)) &&
        isExportableSourceUsePolicy(binding.source_use_policy) &&
        binding.allowlist_status === "allowed"
    ) &&
    candidate.export_validation.section_validations.some(
      (section) =>
        typeof section.displayed_freshness_state === "string" ||
        typeof section.validated_freshness_state === "string" ||
        typeof section.displayed_as_of_date === "string" ||
        typeof section.validated_as_of_date === "string" ||
        typeof section.displayed_retrieved_at === "string" ||
        typeof section.validated_retrieved_at === "string"
    ) &&
    candidate.source_documents.some(
      (source) => typeof source.as_of_date === "string" || typeof source.retrieved_at === "string"
    )
  );
}

function isSupportedChatSessionMarkdownExport(
  value: unknown,
  requestedTicker: string,
  requestedConversationId: string
): value is BackendChatTranscriptExportContract {
  if (!isChatTranscriptExportPreview(value, requestedTicker)) {
    return false;
  }

  const candidate = value as BackendChatTranscriptExportContract;
  if (
    candidate.export_state !== "available" ||
    candidate.metadata.conversation_id !== requestedConversationId ||
    candidate.metadata.session_lifecycle_state !== "active" ||
    candidate.metadata.selected_ticker !== requestedTicker ||
    candidate.metadata.export_available !== true ||
    candidate.metadata.source !== "local_accountless_chat_session" ||
    candidate.metadata.generated_chat_answer !== true ||
    !candidate.state.message.toLowerCase().includes("safe session turn records") ||
    !candidate.export_validation ||
    candidate.export_validation.schema_version !== "export-validation-v1" ||
    candidate.export_validation.content_type !== "chat_transcript" ||
    candidate.export_validation.export_state !== "available" ||
    !candidate.export_validation.diagnostics.no_live_external_calls ||
    !candidate.export_validation.diagnostics.used_existing_chat_contract ||
    !candidate.export_validation.diagnostics.no_new_facts_or_dates
  ) {
    return false;
  }

  if (candidate.export_validation.binding_scope === "same_asset") {
    return chatExportHasSameAssetBindings(candidate, requestedTicker);
  }

  if (candidate.export_validation.binding_scope === "no_factual_evidence") {
    return chatExportHasNoFactualEvidenceBindings(candidate);
  }

  return false;
}

function isChatTranscriptExportPreview(value: unknown, requestedTicker: string): value is BackendChatTranscriptExportContract {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<BackendChatTranscriptExportContract>;
  return (
    candidate.content_type === "chat_transcript" &&
    candidate.export_format === EXPORT_FORMAT &&
    typeof candidate.export_state === "string" &&
    typeof candidate.title === "string" &&
    !!candidate.asset &&
    candidate.asset.ticker === requestedTicker &&
    candidate.asset.status === "supported" &&
    candidate.asset.supported === true &&
    Array.isArray(candidate.sections) &&
    typeof candidate.disclaimer === "string" &&
    candidate.disclaimer.toLowerCase().includes("educational") &&
    !!candidate.licensing_note &&
    candidate.licensing_note.note_id === "export_licensing_scope" &&
    typeof candidate.licensing_note.text === "string" &&
    candidate.licensing_note.text.toLowerCase().includes("source attribution") &&
    typeof candidate.rendered_markdown === "string" &&
    candidate.rendered_markdown.includes("Educational Disclaimer") &&
    !!candidate.metadata &&
    typeof candidate.metadata === "object" &&
    (Array.isArray(candidate.citations) ? candidate.citations.every(isExportCitation) : false) &&
    (Array.isArray(candidate.source_documents) ? candidate.source_documents.every(isExportSourceMetadata) : false)
  );
}

function chatExportHasSameAssetBindings(contract: BackendChatTranscriptExportContract, requestedTicker: string) {
  const exportValidation = contract.export_validation!;
  if (
    contract.citations.length === 0 ||
    contract.source_documents.length === 0 ||
    exportValidation.citation_bindings.length === 0 ||
    exportValidation.source_bindings.length === 0 ||
    !exportValidation.diagnostics.same_asset_citation_bindings_only ||
    !exportValidation.diagnostics.same_asset_source_bindings_only ||
    exportValidation.diagnostics.empty_factual_evidence_export === true
  ) {
    return false;
  }

  const citationIds = new Set(contract.citations.map((citation) => citation.citation_id));
  const sourceIds = new Set(contract.source_documents.map((source) => source.source_document_id));
  return (
    contract.citations.every((citation) => sourceIds.has(citation.source_document_id)) &&
    exportValidation.citation_bindings.every(
      (binding) =>
        citationIds.has(binding.citation_id) &&
        sourceIds.has(binding.source_document_id) &&
        binding.supports_exported_content === true &&
        (binding.asset_ticker === undefined || binding.asset_ticker === null || binding.asset_ticker === requestedTicker)
    ) &&
    exportValidation.source_bindings.every(
      (binding) =>
        sourceIds.has(binding.source_document_id) &&
        (binding.asset_ticker === undefined || binding.asset_ticker === null || binding.asset_ticker === requestedTicker) &&
        isExportableSourceUsePolicy(binding.source_use_policy) &&
        binding.allowlist_status === "allowed"
    )
  );
}

function chatExportHasNoFactualEvidenceBindings(contract: BackendChatTranscriptExportContract) {
  const exportValidation = contract.export_validation!;
  return (
    contract.citations.length === 0 &&
    contract.source_documents.length === 0 &&
    exportValidation.citation_bindings.length === 0 &&
    exportValidation.source_bindings.length === 0 &&
    exportValidation.diagnostics.empty_factual_evidence_export === true &&
    exportValidation.section_validations.length > 0
  );
}

function chatExportResponsePreview(
  contract: BackendChatTranscriptExportContract,
  contractSource: ExportResponsePreview["contractSource"]
): ExportResponsePreview {
  const exportValidation = contract.export_validation;
  return {
    export_state:
      contract.export_state === "available" || contract.export_state === "unsupported" || contract.export_state === "unavailable"
        ? contract.export_state
        : "unavailable",
    rendered_markdown: contract.rendered_markdown,
    contractSource,
    conversationIdPresent: Boolean(contract.metadata.conversation_id),
    selectedTicker: contract.metadata.selected_ticker ?? contract.asset?.ticker ?? "unknown",
    sessionLifecycleState: contract.metadata.session_lifecycle_state ?? "single_turn",
    sessionExportAvailable: contract.metadata.export_available === true,
    sessionExpiresAt: contract.metadata.expires_at ?? "unknown",
    validationSchemaVersion: exportValidation?.schema_version === "export-validation-v1" ? "export-validation-v1" : "local_fallback",
    bindingScope:
      exportValidation?.binding_scope === "same_asset" ||
      exportValidation?.binding_scope === "no_factual_evidence" ||
      exportValidation?.binding_scope === "unavailable"
        ? exportValidation.binding_scope
        : "local_fallback",
    citationCount: contract.citations.length,
    sourceCount: contract.source_documents.length,
    sourceFromSafeSessionRecords: contract.metadata.source === "local_accountless_chat_session",
    usedExistingChatContract: exportValidation?.diagnostics.used_existing_chat_contract === true,
    noLiveExternalCalls: exportValidation?.diagnostics.no_live_external_calls === true
  };
}

function comparisonExportFreshness(contract: BackendComparisonExportContract) {
  const exportValidation = contract.export_validation!;
  const sectionWithFreshness = exportValidation.section_validations.find(
    (section) => section.validated_freshness_state ?? section.displayed_freshness_state
  );
  const sectionWithAsOf = exportValidation.section_validations.find(
    (section) =>
      section.validated_as_of_date ??
      section.displayed_as_of_date ??
      section.validated_retrieved_at ??
      section.displayed_retrieved_at
  );
  const sourceWithAsOf = contract.source_documents.find(
    (source) => typeof source.as_of_date === "string" || typeof source.retrieved_at === "string"
  );

  return {
    freshnessState: sectionWithFreshness?.validated_freshness_state ?? sectionWithFreshness?.displayed_freshness_state ?? "unknown",
    asOfDate:
      sectionWithAsOf?.validated_as_of_date ??
      sectionWithAsOf?.displayed_as_of_date ??
      sectionWithAsOf?.validated_retrieved_at ??
      sectionWithAsOf?.displayed_retrieved_at ??
      sourceWithAsOf?.as_of_date ??
      sourceWithAsOf?.retrieved_at ??
      "unknown"
  };
}

function isExportCitation(value: BackendExportContract["citations"][number]) {
  return (
    typeof value.citation_id === "string" &&
    value.citation_id.length > 0 &&
    typeof value.source_document_id === "string" &&
    value.source_document_id.length > 0
  );
}

function isExportSourceMetadata(value: BackendExportContract["source_documents"][number]) {
  return (
    typeof value.source_document_id === "string" &&
    value.source_document_id.length > 0 &&
    typeof value.title === "string" &&
    value.title.length > 0 &&
    typeof value.source_type === "string" &&
    value.source_type.length > 0 &&
    typeof value.publisher === "string" &&
    value.publisher.length > 0 &&
    typeof value.url === "string" &&
    value.url.length > 0 &&
    typeof value.retrieved_at === "string" &&
    value.retrieved_at.length > 0 &&
    typeof value.freshness_state === "string" &&
    value.freshness_state.length > 0 &&
    value.allowlist_status === "allowed" &&
    isExportableSourceUsePolicy(value.source_use_policy) &&
    value.permitted_operations?.can_export_full_text === false &&
    !!value.allowed_excerpt &&
    typeof value.allowed_excerpt.note === "string" &&
    value.allowed_excerpt.note.length > 0
  );
}

function isExportableSourceUsePolicy(value: string) {
  return value === "full_text_allowed" || value === "summary_allowed";
}

function hasAsOfMetadata(freshness: NonNullable<BackendExportContract["freshness"]>) {
  return (
    typeof freshness.facts_as_of === "string" ||
    typeof freshness.holdings_as_of === "string" ||
    typeof freshness.recent_events_as_of === "string" ||
    typeof freshness.page_last_updated_at === "string"
  );
}
