export type ChatSafetyClassification =
  | "educational"
  | "personalized_advice_redirect"
  | "unsupported_asset_redirect"
  | "insufficient_evidence";

export type ChatAsset = {
  ticker: string;
  name: string;
  asset_type: "stock" | "etf" | "unsupported" | "unknown";
  exchange: string | null;
  issuer: string | null;
  status: "supported" | "unsupported" | "unknown";
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

export type AssetChatResponse = {
  asset: ChatAsset;
  direct_answer: string;
  why_it_matters: string;
  citations: ChatCitation[];
  source_documents: ChatSourceDocument[];
  uncertainty: string[];
  safety_classification: ChatSafetyClassification;
};

type Fetcher = typeof fetch;

export async function postAssetChat(
  ticker: string,
  question: string,
  fetcher: Fetcher = fetch
): Promise<AssetChatResponse> {
  const endpoint = `/api/assets/${encodeURIComponent(ticker.trim().toUpperCase())}/chat`;
  const response = await fetcher(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ question })
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
    typeof candidate.asset === "object"
  );
}
