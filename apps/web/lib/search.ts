import { assetFixtures } from "./fixtures";

type SearchAssetType = "stock" | "etf" | "unsupported" | "unknown";
type SearchResponseStatus = "supported" | "ambiguous" | "ingestion_needed" | "unsupported" | "out_of_scope" | "unknown";
type SearchResultStatus = "supported" | "ingestion_needed" | "unsupported" | "out_of_scope" | "unknown";
type SearchSupportClassification =
  | "cached_supported"
  | "eligible_not_cached"
  | "recognized_unsupported"
  | "out_of_scope"
  | "unknown";

type SearchCandidate = {
  ticker: string;
  name: string;
  asset_type: SearchAssetType;
  exchange: string | null;
  issuer: string | null;
  support_classification: SearchSupportClassification;
  message: string;
  aliases: string[];
};

type SearchBlockedCapabilityFlags = {
  can_open_generated_page: boolean;
  can_answer_chat: boolean;
  can_compare: boolean;
  can_request_ingestion: boolean;
};

type SearchBlockedExplanationDiagnostics = {
  deterministic_contract: true;
  generated_asset_analysis: false;
  includes_citations: false;
  includes_source_documents: false;
  includes_freshness: false;
  uses_live_calls: false;
};

export type LocalSearchBlockedExplanation = {
  schema_version: "search-blocked-explanation-v1";
  status: "unsupported" | "out_of_scope";
  support_classification: "recognized_unsupported" | "out_of_scope";
  explanation_kind: "scope_blocked_search_result";
  explanation_category: string;
  summary: string;
  scope_rationale: string;
  supported_v1_scope: string;
  blocked_capabilities: SearchBlockedCapabilityFlags;
  ingestion_eligible: false;
  ingestion_request_route: null;
  diagnostics: SearchBlockedExplanationDiagnostics;
};

export type LocalSearchResult = {
  ticker: string;
  name: string;
  asset_type: SearchAssetType;
  exchange: string | null;
  issuer: string | null;
  supported: boolean;
  status: SearchResultStatus;
  support_classification: SearchSupportClassification;
  eligible_for_ingestion: boolean;
  requires_ingestion: boolean;
  can_open_generated_page: boolean;
  can_answer_chat: boolean;
  can_compare: boolean;
  generated_route: string | null;
  can_request_ingestion: boolean;
  ingestion_request_route: string | null;
  message: string | null;
  blocked_explanation: LocalSearchBlockedExplanation | null;
};

export type LocalSearchState = {
  status: SearchResponseStatus;
  message: string;
  result_count: number;
  support_classification: SearchSupportClassification | null;
  requires_disambiguation: boolean;
  requires_ingestion: boolean;
  can_open_generated_page: boolean;
  generated_route: string | null;
  can_request_ingestion: boolean;
  ingestion_request_route: string | null;
  blocked_explanation: LocalSearchBlockedExplanation | null;
};

export type LocalSearchResponse = {
  query: string;
  results: LocalSearchResult[];
  state: LocalSearchState;
};

const SUPPORTED_V1_SCOPE_REMINDER =
  "Supported MVP coverage is limited to U.S.-listed common stocks in the current Top-500 manifest and non-leveraged U.S.-listed equity ETFs.";

const EMPTY_BLOCKED_CAPABILITIES: SearchBlockedCapabilityFlags = {
  can_open_generated_page: false,
  can_answer_chat: false,
  can_compare: false,
  can_request_ingestion: false
};

const BLOCKED_DIAGNOSTICS: SearchBlockedExplanationDiagnostics = {
  deterministic_contract: true,
  generated_asset_analysis: false,
  includes_citations: false,
  includes_source_documents: false,
  includes_freshness: false,
  uses_live_calls: false
};

const SUPPORTED_ALIAS_OVERRIDES: Record<string, string[]> = {
  VOO: ["s&p 500 etf", "vanguard s&p 500", "plain vanilla etf"],
  QQQ: ["nasdaq-100", "nasdaq 100", "invesco qqq"],
  AAPL: ["apple", "apple stock", "common stock", "top-500 manifest common stock"]
};

const ELIGIBLE_NOT_CACHED_MESSAGE =
  "Eligible U.S.-listed common stock or plain-vanilla ETF, but no local cached knowledge pack is available yet. On-demand ingestion would be required later.";

const ELIGIBLE_NOT_CACHED_CANDIDATES: SearchCandidate[] = [
  {
    ticker: "SPY",
    name: "SPDR S&P 500 ETF Trust",
    asset_type: "etf",
    exchange: "NYSE Arca",
    issuer: "State Street Global Advisors",
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["s&p 500 etf", "spdr s&p 500 etf", "plain vanilla etf"]
  },
  {
    ticker: "VTI",
    name: "Vanguard Total Stock Market ETF",
    asset_type: "etf",
    exchange: "NYSE Arca",
    issuer: "Vanguard",
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["total market etf", "vanguard total stock market etf", "plain vanilla etf"]
  },
  {
    ticker: "IVV",
    name: "iShares Core S&P 500 ETF",
    asset_type: "etf",
    exchange: "NYSE Arca",
    issuer: "iShares",
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["s&p 500 etf", "ishares core s&p 500 etf", "plain vanilla etf"]
  },
  {
    ticker: "IWM",
    name: "iShares Russell 2000 ETF",
    asset_type: "etf",
    exchange: "NYSE Arca",
    issuer: "iShares",
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["russell 2000 etf", "small-cap etf", "plain vanilla etf"]
  },
  {
    ticker: "DIA",
    name: "SPDR Dow Jones Industrial Average ETF Trust",
    asset_type: "etf",
    exchange: "NYSE Arca",
    issuer: "State Street Global Advisors",
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["dow jones etf", "dia etf", "plain vanilla etf"]
  },
  {
    ticker: "VGT",
    name: "Vanguard Information Technology ETF",
    asset_type: "etf",
    exchange: "NYSE Arca",
    issuer: "Vanguard",
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["technology etf", "vanguard technology etf", "plain vanilla etf"]
  },
  {
    ticker: "XLK",
    name: "Technology Select Sector SPDR Fund",
    asset_type: "etf",
    exchange: "NYSE Arca",
    issuer: "State Street Global Advisors",
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["technology sector etf", "select sector technology", "plain vanilla etf"]
  },
  {
    ticker: "SOXX",
    name: "iShares Semiconductor ETF",
    asset_type: "etf",
    exchange: "NASDAQ",
    issuer: "iShares",
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["semiconductor etf", "ishares semiconductor etf", "plain vanilla etf"]
  },
  {
    ticker: "SMH",
    name: "VanEck Semiconductor ETF",
    asset_type: "etf",
    exchange: "NASDAQ",
    issuer: "VanEck",
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["semiconductor etf", "vaneck semiconductor etf", "plain vanilla etf"]
  },
  {
    ticker: "XLF",
    name: "Financial Select Sector SPDR Fund",
    asset_type: "etf",
    exchange: "NYSE Arca",
    issuer: "State Street Global Advisors",
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["financial sector etf", "select sector financial", "plain vanilla etf"]
  },
  {
    ticker: "XLV",
    name: "Health Care Select Sector SPDR Fund",
    asset_type: "etf",
    exchange: "NYSE Arca",
    issuer: "State Street Global Advisors",
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["health care sector etf", "select sector health care", "plain vanilla etf"]
  },
  {
    ticker: "MSFT",
    name: "Microsoft Corporation",
    asset_type: "stock",
    exchange: "NASDAQ",
    issuer: null,
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["microsoft", "microsoft stock", "top-500 manifest common stock"]
  },
  {
    ticker: "NVDA",
    name: "NVIDIA Corporation",
    asset_type: "stock",
    exchange: "NASDAQ",
    issuer: null,
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["nvidia", "nvidia stock", "top-500 manifest common stock"]
  },
  {
    ticker: "AMZN",
    name: "Amazon.com, Inc.",
    asset_type: "stock",
    exchange: "NASDAQ",
    issuer: null,
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["amazon", "amazon stock", "top-500 manifest common stock"]
  },
  {
    ticker: "GOOGL",
    name: "Alphabet Inc.",
    asset_type: "stock",
    exchange: "NASDAQ",
    issuer: null,
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["alphabet", "google", "google stock", "top-500 manifest common stock"]
  },
  {
    ticker: "META",
    name: "Meta Platforms, Inc.",
    asset_type: "stock",
    exchange: "NASDAQ",
    issuer: null,
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["meta", "facebook", "meta stock", "top-500 manifest common stock"]
  },
  {
    ticker: "TSLA",
    name: "Tesla, Inc.",
    asset_type: "stock",
    exchange: "NASDAQ",
    issuer: null,
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["tesla", "tesla stock", "top-500 manifest common stock"]
  },
  {
    ticker: "BRK.B",
    name: "Berkshire Hathaway Inc. Class B",
    asset_type: "stock",
    exchange: "NYSE",
    issuer: null,
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["berkshire hathaway", "berkshire b", "top-500 manifest common stock"]
  },
  {
    ticker: "JPM",
    name: "JPMorgan Chase & Co.",
    asset_type: "stock",
    exchange: "NYSE",
    issuer: null,
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["jpmorgan", "jpmorgan stock", "top-500 manifest common stock"]
  },
  {
    ticker: "UNH",
    name: "UnitedHealth Group Incorporated",
    asset_type: "stock",
    exchange: "NYSE",
    issuer: null,
    support_classification: "eligible_not_cached",
    message: ELIGIBLE_NOT_CACHED_MESSAGE,
    aliases: ["unitedhealth", "unh stock", "top-500 manifest common stock"]
  }
];

const UNSUPPORTED_CANDIDATES: SearchCandidate[] = [
  {
    ticker: "BTC",
    name: "Bitcoin",
    asset_type: "unsupported",
    exchange: null,
    issuer: null,
    support_classification: "recognized_unsupported",
    message: "Crypto assets are outside the current U.S. stock and plain-vanilla ETF scope.",
    aliases: ["bitcoin", "crypto"]
  },
  {
    ticker: "ETH",
    name: "Ethereum",
    asset_type: "unsupported",
    exchange: null,
    issuer: null,
    support_classification: "recognized_unsupported",
    message: "Crypto assets are outside the current U.S. stock and plain-vanilla ETF scope.",
    aliases: ["ethereum", "ether", "crypto"]
  },
  {
    ticker: "TQQQ",
    name: "ProShares UltraPro QQQ",
    asset_type: "unsupported",
    exchange: null,
    issuer: null,
    support_classification: "recognized_unsupported",
    message: "Leveraged ETFs are outside the current plain-vanilla ETF scope.",
    aliases: ["leveraged qqq", "ultrapro qqq", "leveraged etf"]
  },
  {
    ticker: "SQQQ",
    name: "ProShares UltraPro Short QQQ",
    asset_type: "unsupported",
    exchange: null,
    issuer: null,
    support_classification: "recognized_unsupported",
    message: "Inverse ETFs are outside the current plain-vanilla ETF scope.",
    aliases: ["inverse qqq", "short qqq", "inverse etf"]
  }
];

const OUT_OF_SCOPE_CANDIDATES: SearchCandidate[] = [
  {
    ticker: "GME",
    name: "GameStop Corp.",
    asset_type: "stock",
    exchange: "NYSE",
    issuer: null,
    support_classification: "out_of_scope",
    message:
      "Recognized U.S.-listed common stock outside the local Top-500 manifest; out of scope for generated outputs unless explicitly approved for on-demand ingestion later.",
    aliases: ["gamestop", "gamestop corp", "common stock"]
  }
];

function normalizeQueryText(value: string) {
  return value.trim().toLowerCase();
}

function normalizeTicker(value: string) {
  return value.trim().toUpperCase();
}

function supportedCandidates(): SearchCandidate[] {
  return Object.values(assetFixtures).map((asset) => ({
    ticker: asset.ticker,
    name: asset.name,
    asset_type: asset.assetType,
    exchange: asset.exchange,
    issuer: asset.issuer ?? null,
    support_classification: "cached_supported",
    message: "Cached supported asset with deterministic local page, chat, and comparison data.",
    aliases: [...(asset.issuer ? [asset.issuer] : []), ...(SUPPORTED_ALIAS_OVERRIDES[asset.ticker] ?? [])]
  }));
}

function allCandidates() {
  return [...supportedCandidates(), ...UNSUPPORTED_CANDIDATES, ...ELIGIBLE_NOT_CACHED_CANDIDATES, ...OUT_OF_SCOPE_CANDIDATES];
}

function scoreCandidate(query: string, normalized_ticker: string, candidate: SearchCandidate) {
  const name = candidate.name.toLowerCase();
  const aliases = candidate.aliases.map((alias) => alias.toLowerCase());
  const issuer = candidate.issuer ? candidate.issuer.toLowerCase() : "";

  if (normalized_ticker && candidate.ticker.startsWith(normalized_ticker)) {
    return 80;
  }
  if (query === name) {
    return 75;
  }
  if (query && name.includes(query)) {
    return 60;
  }
  if (aliases.some((alias) => query === alias)) {
    return 58;
  }
  if (query && aliases.some((alias) => alias.includes(query))) {
    return 50;
  }
  if (issuer && query && issuer.includes(query)) {
    return 35;
  }
  return 0;
}

function rankedCandidates(raw_query: string, normalized_ticker: string) {
  if (!raw_query) {
    return [];
  }

  const candidates = allCandidates();
  const exact_ticker_match = candidates.find((candidate) => candidate.ticker === normalized_ticker);
  if (exact_ticker_match) {
    return [[100, exact_ticker_match] as const];
  }

  return candidates
    .map((candidate) => [scoreCandidate(raw_query.toLowerCase(), normalized_ticker, candidate), candidate] as const)
    .filter(([score]) => score > 0)
    .sort((left, right) => right[0] - left[0] || left[1].ticker.localeCompare(right[1].ticker));
}

function blockedExplanationForResult(result: LocalSearchResult): LocalSearchBlockedExplanation | null {
  if (result.support_classification === "recognized_unsupported") {
    const explanation_category =
      result.ticker === "BTC" || result.ticker === "ETH"
        ? "crypto_assets"
        : result.ticker === "TQQQ"
          ? "leveraged_etf"
          : "inverse_etf";

    return {
      schema_version: "search-blocked-explanation-v1",
      status: "unsupported",
      support_classification: "recognized_unsupported",
      explanation_kind: "scope_blocked_search_result",
      explanation_category,
      summary: `${result.ticker} is recognized, but this asset category is outside the current supported MVP coverage.`,
      scope_rationale: result.message ?? "This asset category is outside the current supported MVP scope.",
      supported_v1_scope: SUPPORTED_V1_SCOPE_REMINDER,
      blocked_capabilities: EMPTY_BLOCKED_CAPABILITIES,
      ingestion_eligible: false,
      ingestion_request_route: null,
      diagnostics: BLOCKED_DIAGNOSTICS
    };
  }

  if (result.support_classification === "out_of_scope") {
    return {
      schema_version: "search-blocked-explanation-v1",
      status: "out_of_scope",
      support_classification: "out_of_scope",
      explanation_kind: "scope_blocked_search_result",
      explanation_category: "top500_manifest_scope",
      summary: `${result.ticker} is recognized, but it is outside the current Top-500 manifest-backed supported MVP stock coverage.`,
      scope_rationale:
        result.message ??
        "Recognized U.S.-listed common stock outside the current Top-500 manifest-backed MVP scope.",
      supported_v1_scope: SUPPORTED_V1_SCOPE_REMINDER,
      blocked_capabilities: EMPTY_BLOCKED_CAPABILITIES,
      ingestion_eligible: false,
      ingestion_request_route: null,
      diagnostics: BLOCKED_DIAGNOSTICS
    };
  }

  return null;
}

function candidateToResult(candidate: SearchCandidate): LocalSearchResult {
  const cached_supported = candidate.support_classification === "cached_supported";
  const eligible_not_cached = candidate.support_classification === "eligible_not_cached";

  const base: LocalSearchResult = {
    ticker: candidate.ticker,
    name: candidate.name,
    asset_type: candidate.asset_type,
    exchange: candidate.exchange,
    issuer: candidate.issuer,
    supported: cached_supported,
    status: cached_supported
      ? "supported"
      : eligible_not_cached
        ? "ingestion_needed"
        : candidate.support_classification === "recognized_unsupported"
          ? "unsupported"
          : candidate.support_classification === "out_of_scope"
            ? "out_of_scope"
            : "unknown",
    support_classification: candidate.support_classification,
    eligible_for_ingestion: eligible_not_cached,
    requires_ingestion: eligible_not_cached,
    can_open_generated_page: cached_supported,
    can_answer_chat: cached_supported,
    can_compare: cached_supported,
    generated_route: cached_supported ? `/assets/${candidate.ticker}` : null,
    can_request_ingestion: eligible_not_cached,
    ingestion_request_route: eligible_not_cached ? `/api/admin/ingest/${candidate.ticker}` : null,
    message: candidate.message,
    blocked_explanation: null
  };

  return {
    ...base,
    blocked_explanation: blockedExplanationForResult(base)
  };
}

function stateForSingleResult(result: LocalSearchResult): LocalSearchState {
  if (result.support_classification === "cached_supported") {
    return {
      status: "supported",
      message: "One cached supported asset matched and is safe to open as a local generated asset page.",
      result_count: 1,
      support_classification: result.support_classification,
      requires_disambiguation: false,
      requires_ingestion: false,
      can_open_generated_page: true,
      generated_route: result.generated_route,
      can_request_ingestion: false,
      ingestion_request_route: null,
      blocked_explanation: null
    };
  }

  if (result.support_classification === "eligible_not_cached") {
    return {
      status: "ingestion_needed",
      message:
        "This asset appears eligible for future support, but it is not locally cached. No generated page, chat, or comparison output is available in this task.",
      result_count: 1,
      support_classification: result.support_classification,
      requires_disambiguation: false,
      requires_ingestion: true,
      can_open_generated_page: false,
      generated_route: null,
      can_request_ingestion: true,
      ingestion_request_route: `/api/admin/ingest/${result.ticker}`,
      blocked_explanation: null
    };
  }

  if (result.support_classification === "recognized_unsupported") {
    return {
      status: "unsupported",
      message: result.message ?? "Recognized asset type is outside the current product scope.",
      result_count: 1,
      support_classification: result.support_classification,
      requires_disambiguation: false,
      requires_ingestion: false,
      can_open_generated_page: false,
      generated_route: null,
      can_request_ingestion: false,
      ingestion_request_route: null,
      blocked_explanation: result.blocked_explanation
    };
  }

  if (result.support_classification === "out_of_scope") {
    return {
      status: "out_of_scope",
      message:
        result.message ??
        "Recognized common stock is outside the current Top-500 manifest-backed support scope.",
      result_count: 1,
      support_classification: result.support_classification,
      requires_disambiguation: false,
      requires_ingestion: false,
      can_open_generated_page: false,
      generated_route: null,
      can_request_ingestion: false,
      ingestion_request_route: null,
      blocked_explanation: result.blocked_explanation
    };
  }

  return {
    status: "unknown",
    message: "Unknown or unavailable in local deterministic search data; no facts are invented.",
    result_count: 1,
    support_classification: "unknown",
    requires_disambiguation: false,
    requires_ingestion: false,
    can_open_generated_page: false,
    generated_route: null,
    can_request_ingestion: false,
    ingestion_request_route: null,
    blocked_explanation: null
  };
}

export function resolveLocalSearchResponse(query: string): LocalSearchResponse {
  const raw_query = query.trim();
  const normalized_ticker = normalizeTicker(query);
  const candidates = rankedCandidates(raw_query, normalized_ticker);

  if (candidates.length > 0) {
    const results = candidates.map(([, candidate]) => candidateToResult(candidate));
    if (results.length > 1) {
      return {
        query,
        results,
        state: {
          status: "ambiguous",
          message:
            "Multiple deterministic local candidates matched this search. Choose a ticker before opening any generated asset experience.",
          result_count: results.length,
          support_classification: null,
          requires_disambiguation: true,
          requires_ingestion: false,
          can_open_generated_page: false,
          generated_route: null,
          can_request_ingestion: false,
          ingestion_request_route: null,
          blocked_explanation: null
        }
      };
    }

    return {
      query,
      results,
      state: stateForSingleResult(results[0])
    };
  }

  const unknown_ticker = normalizeTicker(query);
  const unknown: LocalSearchResult = {
    ticker: unknown_ticker,
    name: unknown_ticker,
    asset_type: "unknown",
    exchange: null,
    issuer: null,
    supported: false,
    status: "unknown",
    support_classification: "unknown",
    eligible_for_ingestion: false,
    requires_ingestion: false,
    can_open_generated_page: false,
    can_answer_chat: false,
    can_compare: false,
    generated_route: null,
    can_request_ingestion: false,
    ingestion_request_route: null,
    message: "No deterministic local fixture or recognized eligible asset matched this query.",
    blocked_explanation: null
  };

  return {
    query,
    results: [unknown],
    state: {
      status: "unknown",
      message: "Unknown or unavailable in local deterministic search data; no facts are invented.",
      result_count: 1,
      support_classification: "unknown",
      requires_disambiguation: false,
      requires_ingestion: false,
      can_open_generated_page: false,
      generated_route: null,
      can_request_ingestion: false,
      ingestion_request_route: null,
      blocked_explanation: null
    }
  };
}

export function formatSearchAssetType(result: Pick<LocalSearchResult, "asset_type">) {
  if (result.asset_type === "etf") {
    return "ETF";
  }
  if (result.asset_type === "stock") {
    return "Stock";
  }
  if (result.asset_type === "unsupported") {
    return "Blocked asset";
  }
  return "Unknown asset";
}

export function searchQueryExampleText() {
  return "Try VOO, Apple, S&P 500 ETF, SPY, BTC, GME, or ZZZZ.";
}

export function searchUnknownMessage() {
  return "Unknown or unavailable in local deterministic search data. No facts are invented for this ticker or name.";
}

export function searchQueryNormalizer(value: string) {
  return normalizeQueryText(value);
}
