export type ExportFormat = "markdown";

type Fetcher = typeof fetch;

export type ExportResponsePreview = {
  export_state: "available" | "unsupported" | "unavailable";
  rendered_markdown: string;
};

export const EXPORT_FORMAT: ExportFormat = "markdown";

export const EXPORT_TRUST_CONTEXT =
  "Saved output uses backend export payloads with citation IDs, source metadata, freshness/as-of dates, the educational disclaimer, and licensing scope.";

export const EXPORT_LICENSING_CONTEXT =
  "Export controls request local Markdown-shaped payloads only; full source documents, restricted provider payloads, credentials, and live external download URLs are not exposed.";

export function assetPageExportUrl(ticker: string, exportFormat: ExportFormat = EXPORT_FORMAT): string {
  const encodedTicker = encodeTicker(ticker);
  return `/api/assets/${encodedTicker}/export?export_format=${exportFormat}`;
}

export function assetSourceListExportUrl(ticker: string, exportFormat: ExportFormat = EXPORT_FORMAT): string {
  const encodedTicker = encodeTicker(ticker);
  return `/api/assets/${encodedTicker}/sources/export?export_format=${exportFormat}`;
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

  return `/api/compare/export?${params.toString()}`;
}

export function chatTranscriptExportUrl(ticker: string): string {
  return `/api/assets/${encodeTicker(ticker)}/chat/export`;
}

export async function postChatTranscriptExport(
  ticker: string,
  question: string,
  fetcher: Fetcher = fetch
): Promise<ExportResponsePreview> {
  const endpoint = chatTranscriptExportUrl(ticker);
  const response = await fetcher(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question,
      export_format: EXPORT_FORMAT
    })
  });

  if (!response.ok) {
    throw new Error(`Chat transcript export failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (!isExportResponsePreview(payload)) {
    throw new Error("Chat transcript export did not match the expected local API shape.");
  }

  return payload;
}

function normalizeTicker(ticker: string): string {
  return ticker.trim().toUpperCase();
}

function encodeTicker(ticker: string): string {
  return encodeURIComponent(normalizeTicker(ticker));
}

function isExportResponsePreview(value: unknown): value is ExportResponsePreview {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<ExportResponsePreview>;
  return typeof candidate.export_state === "string" && typeof candidate.rendered_markdown === "string";
}
