import { publicApiEndpoint } from "./apiEndpoints";

export type ChatSafetyClassification =
  | "educational"
  | "personalized_advice_redirect"
  | "unsupported_asset_redirect"
  | "compare_route_redirect"
  | "insufficient_evidence";

export type ChatAsset = {
  ticker: string;
  name: string;
  asset_type: "stock" | "etf" | "unsupported" | "unknown";
  exchange: string | null;
  issuer: string | null;
  status:
    | "supported"
    | "unsupported"
    | "out_of_scope"
    | "pending_ingestion"
    | "partial"
    | "stale"
    | "unknown"
    | "unavailable";
  supported: boolean;
};

export type ChatCitation = {
  citation_id: string;
  claim: string;
  source_document_id: string;
  chunk_id: string;
};

export type ChatSourceDocument = {
  citation_id: string;
  source_document_id: string;
  chunk_id: string;
  title: string;
  source_type: string;
  publisher: string;
  url: string;
  published_at: string | null;
  as_of_date: string | null;
  retrieved_at: string;
  freshness_state: "fresh" | "stale" | "unknown" | "unavailable";
  is_official: boolean;
  supporting_passage: string;
};

export type ChatSessionMetadata = {
  schema_version: "chat-session-contract-v1";
  session_id: string | null;
  conversation_id: string | null;
  lifecycle_state: "active" | "expired" | "deleted" | "ticker_mismatch" | "unavailable";
  selected_asset: ChatAsset | null;
  created_at: string | null;
  last_activity_at: string | null;
  expires_at: string | null;
  deleted_at: string | null;
  turn_count: number;
  latest_safety_classification: ChatSafetyClassification | null;
  latest_evidence_state: string | null;
  latest_freshness_state: string | null;
  export_available: boolean;
  deletion_status: "active" | "user_deleted" | "expired" | "unavailable";
};

export type AssetChatResponse = {
  asset: ChatAsset;
  direct_answer: string;
  why_it_matters: string;
  citations: ChatCitation[];
  source_documents: ChatSourceDocument[];
  uncertainty: string[];
  safety_classification: ChatSafetyClassification;
  session?: ChatSessionMetadata | null;
};

type Fetcher = typeof fetch;

export async function postAssetChat(
  ticker: string,
  question: string,
  conversationIdOrFetcher?: string | null | Fetcher,
  fetcher: Fetcher = fetch
): Promise<AssetChatResponse> {
  const conversationId =
    typeof conversationIdOrFetcher === "function" ? null : conversationIdOrFetcher ?? null;
  const resolvedFetcher = typeof conversationIdOrFetcher === "function" ? conversationIdOrFetcher : fetcher;
  const endpoint = publicApiEndpoint(`/api/assets/${encodeURIComponent(ticker.trim().toUpperCase())}/chat`);
  const response = await resolvedFetcher(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question,
      ...(conversationId ? { conversation_id: conversationId } : {})
    })
  });

  if (!response.ok) {
    throw new Error(`Chat request failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (!isAssetChatResponse(payload)) {
    throw new Error("Chat response did not match the expected local API shape.");
  }

  return payload;
}

function isAssetChatResponse(value: unknown): value is AssetChatResponse {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<AssetChatResponse>;
  return (
    typeof candidate.direct_answer === "string" &&
    typeof candidate.why_it_matters === "string" &&
    Array.isArray(candidate.citations) &&
    Array.isArray(candidate.source_documents) &&
    Array.isArray(candidate.uncertainty) &&
    typeof candidate.safety_classification === "string" &&
    !!candidate.asset &&
    typeof candidate.asset === "object" &&
    (candidate.session === undefined || candidate.session === null || isChatSessionMetadata(candidate.session))
  );
}

function isChatSessionMetadata(value: unknown): value is ChatSessionMetadata {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<ChatSessionMetadata>;
  return (
    candidate.schema_version === "chat-session-contract-v1" &&
    (candidate.conversation_id === null || typeof candidate.conversation_id === "string") &&
    typeof candidate.lifecycle_state === "string" &&
    (candidate.selected_asset === null || (!!candidate.selected_asset && typeof candidate.selected_asset === "object")) &&
    typeof candidate.turn_count === "number" &&
    typeof candidate.export_available === "boolean" &&
    typeof candidate.deletion_status === "string"
  );
}
