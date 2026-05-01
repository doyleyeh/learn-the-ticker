import { publicApiEndpoint } from "./apiEndpoints";
import { getAssetFixture, normalizeTicker, type FreshnessState } from "./fixtures";
import { resolveLocalSearchResponse } from "./search";

type Fetcher = typeof fetch;

type CompareAssetType = "stock" | "etf" | "unsupported" | "unknown";
type CompareStateStatus = "supported" | "unsupported" | "unknown";
type ComparisonFactKind = "benchmark" | "expense_ratio" | "holdings_count" | "beginner_role";
export type ComparisonEvidenceAvailabilityState =
  | "available"
  | "unsupported"
  | "out_of_scope"
  | "unknown"
  | "eligible_not_cached"
  | "no_local_pack"
  | "stale"
  | "partial"
  | "unavailable"
  | "insufficient_evidence";
type ComparisonEvidenceState =
  | "supported"
  | "partial"
  | "unavailable"
  | "unknown"
  | "stale"
  | "mixed"
  | "insufficient_evidence"
  | "unsupported";
type ComparisonSourceQuality = "official" | "issuer" | "provider" | "fixture" | "allowlisted" | "rejected" | "unknown";
type ComparisonSourceAllowlistStatus = "allowed" | "rejected" | "pending_review" | "not_allowlisted";
type ComparisonSourceUsePolicy = "metadata_only" | "link_only" | "summary_allowed" | "full_text_allowed" | "rejected";
type ComparisonEvidenceSide = "left" | "right" | "shared";
type ComparisonEvidenceSideRole = "left_side_support" | "right_side_support" | "shared_comparison_support";
type ComparisonClaimKind = "key_difference" | "beginner_bottom_line";
type ComparisonRequiredDimension = "Benchmark" | "Expense ratio" | "Holdings count" | "Breadth" | "Educational role";
type StockEtfRequiredDimension = "Structure" | "Basket membership" | "Breadth" | "Cost model" | "Educational role";
type StockEtfRelationshipState =
  | "direct_holding"
  | "sector_or_theme"
  | "broad_market_context"
  | "weak_relationship"
  | "unknown";
type SearchSupportClassification =
  | "cached_supported"
  | "eligible_not_cached"
  | "recognized_unsupported"
  | "out_of_scope"
  | "unknown";

export type CompareRequest = {
  left_ticker: string;
  right_ticker: string;
};

export async function fetchComparisonResponse(
  leftTicker: string,
  rightTicker: string,
  fetcher: Fetcher = fetch
): Promise<ComparePageFixture> {
  const endpoint = publicApiEndpoint("/api/compare");
  const response = await fetcher(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      left_ticker: normalizeTicker(leftTicker),
      right_ticker: normalizeTicker(rightTicker)
    } satisfies CompareRequest)
  });

  if (!response.ok) {
    throw new Error(`Compare request failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (!isCompareResponsePayload(payload)) {
    throw new Error("Compare response did not match the expected backend response contract.");
  }

  return payload;
}

function isCompareResponsePayload(value: unknown): value is ComparePageFixture {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<ComparePageFixture>;
  const hasValidStockEtfRelationship =
    candidate.stock_etf_relationship == null || isStockEtfRelationshipModel(candidate.stock_etf_relationship);

  return (
    typeof candidate.left_asset === "object" &&
    candidate.left_asset !== null &&
    typeof candidate.left_asset.ticker === "string" &&
    typeof candidate.left_asset.name === "string" &&
    typeof candidate.left_asset.asset_type === "string" &&
    typeof candidate.left_asset.status === "string" &&
    typeof candidate.left_asset.supported === "boolean" &&
    typeof candidate.right_asset === "object" &&
    candidate.right_asset !== null &&
    typeof candidate.right_asset.ticker === "string" &&
    typeof candidate.right_asset.name === "string" &&
    typeof candidate.right_asset.asset_type === "string" &&
    typeof candidate.right_asset.status === "string" &&
    typeof candidate.right_asset.supported === "boolean" &&
    typeof candidate.state === "object" &&
    candidate.state !== null &&
    typeof candidate.state.status === "string" &&
    typeof candidate.state.message === "string" &&
    typeof candidate.comparison_type === "string" &&
    Array.isArray(candidate.key_differences) &&
    Array.isArray(candidate.citations) &&
    Array.isArray(candidate.source_documents) &&
    (candidate.evidence_availability == null || typeof candidate.evidence_availability === "object") &&
    hasValidStockEtfRelationship
  );
}

function isStockEtfRelationshipState(value: unknown): value is StockEtfRelationshipState {
  return (
    value === "direct_holding" ||
    value === "sector_or_theme" ||
    value === "broad_market_context" ||
    value === "weak_relationship" ||
    value === "unknown"
  );
}

function isStockEtfRelationshipModel(value: unknown): value is StockEtfRelationshipModel {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<StockEtfRelationshipModel>;
  const basketStructure = candidate.basket_structure as Partial<StockEtfBasketStructure> | undefined;

  return (
    candidate.schema_version === "stock-etf-relationship-v1" &&
    candidate.comparison_type === "stock_vs_etf" &&
    typeof candidate.stock_ticker === "string" &&
    typeof candidate.etf_ticker === "string" &&
    isStockEtfRelationshipState(candidate.relationship_state) &&
    Array.isArray(candidate.badges) &&
    candidate.badges.every(
      (badge) =>
        Boolean(badge) &&
        typeof badge === "object" &&
        isStockEtfRelationshipState((badge as Partial<StockEtfRelationshipBadge>).relationship_state)
    ) &&
    Boolean(basketStructure) &&
    isStockEtfRelationshipState(basketStructure?.overlap_or_membership_state)
  );
}

export type CompareAssetIdentity = {
  ticker: string;
  name: string;
  asset_type: CompareAssetType;
  exchange: string | null;
  issuer: string | null;
  status: CompareStateStatus;
  supported: boolean;
};

export type ComparisonCitation = {
  citation_id: string;
  source_document_id: string;
  title: string;
  publisher: string;
  freshness_state: FreshnessState;
};

type ComparisonSourceOperationPermissions = {
  can_store_metadata: boolean;
  can_store_raw_text: boolean;
  can_display_metadata: boolean;
  can_display_excerpt: boolean;
  can_summarize: boolean;
  can_cache: boolean;
  can_export_metadata: boolean;
  can_export_excerpt: boolean;
  can_export_full_text: boolean;
  can_support_generated_output: boolean;
  can_support_citations: boolean;
  can_support_canonical_facts: boolean;
  can_support_recent_developments: boolean;
};

export type ComparisonSourceDocument = {
  source_document_id: string;
  source_type: string;
  title: string;
  publisher: string;
  url: string;
  published_at: string | null;
  as_of_date: string | null;
  retrieved_at: string;
  freshness_state: FreshnessState;
  is_official: boolean;
  supporting_passage: string;
  source_quality: ComparisonSourceQuality;
  allowlist_status: ComparisonSourceAllowlistStatus;
  source_use_policy: ComparisonSourceUsePolicy;
  permitted_operations: ComparisonSourceOperationPermissions;
};

export type ComparisonClaimContext = {
  citation_id: string;
  section: "Key difference" | "Bottom line for beginners";
  label: string;
  claim_text: string;
};

export type ComparisonKeyDifference = {
  dimension: string;
  plain_english_summary: string;
  citation_ids: string[];
};

export type ComparisonBeginnerBottomLine = {
  summary: string;
  citation_ids: string[];
};

export type StockEtfRelationshipBadge = {
  label: string;
  value: string;
  marker: "comparison_type" | "stock_ticker" | "etf_ticker" | "relationship_state" | "evidence_boundary";
  relationship_state: StockEtfRelationshipState;
  evidence_state: ComparisonEvidenceState;
  citation_ids: string[];
};

export type StockEtfBasketStructure = {
  stock_ticker: string;
  etf_ticker: string;
  stock_role_summary: string;
  etf_basket_summary: string;
  relationship_summary: string;
  overlap_or_membership_state: StockEtfRelationshipState;
  evidence_state: ComparisonEvidenceState;
  unavailable_detail: string | null;
  citation_ids: string[];
};

export type StockEtfRelationshipModel = {
  schema_version: "stock-etf-relationship-v1";
  comparison_type: "stock_vs_etf";
  stock_ticker: string;
  etf_ticker: string;
  relationship_state: StockEtfRelationshipState;
  evidence_state: ComparisonEvidenceState;
  badges: StockEtfRelationshipBadge[];
  basket_structure: StockEtfBasketStructure;
};

type ComparisonEvidenceItem = {
  evidence_item_id: string;
  dimension: string;
  side: ComparisonEvidenceSide;
  side_role: ComparisonEvidenceSideRole;
  asset_ticker: string;
  field_name: string | null;
  fact_id: string | null;
  source_chunk_id: string | null;
  source_document_id: string | null;
  citation_ids: string[];
  evidence_state: ComparisonEvidenceState;
  freshness_state: FreshnessState;
  as_of_date: string | null;
  retrieved_at: string | null;
  is_official: boolean;
  source_quality: ComparisonSourceQuality;
  allowlist_status: ComparisonSourceAllowlistStatus;
  source_use_policy: ComparisonSourceUsePolicy;
  permitted_operations: ComparisonSourceOperationPermissions;
  unavailable_reason?: string | null;
};

type ComparisonEvidenceDimension = {
  dimension: string;
  required: true;
  availability_state: ComparisonEvidenceAvailabilityState;
  evidence_state: ComparisonEvidenceState;
  freshness_state: FreshnessState;
  left_evidence_item_ids: string[];
  right_evidence_item_ids: string[];
  shared_evidence_item_ids: string[];
  citation_ids: string[];
  source_document_ids: string[];
  generated_claim_ids: string[];
  unavailable_reason?: string | null;
};

type ComparisonEvidenceClaimBinding = {
  claim_id: string;
  claim_kind: ComparisonClaimKind;
  dimension: string;
  side_role: ComparisonEvidenceSideRole;
  citation_ids: string[];
  source_document_ids: string[];
  evidence_item_ids: string[];
  availability_state: ComparisonEvidenceAvailabilityState;
};

type ComparisonEvidenceCitationBinding = {
  binding_id: string;
  claim_id: string;
  dimension: string;
  citation_id: string;
  source_document_id: string;
  asset_ticker: string;
  side_role: ComparisonEvidenceSideRole;
  freshness_state: FreshnessState;
  source_quality: ComparisonSourceQuality;
  allowlist_status: ComparisonSourceAllowlistStatus;
  source_use_policy: ComparisonSourceUsePolicy;
  permitted_operations: ComparisonSourceOperationPermissions;
  supports_generated_claim: boolean;
};

type ComparisonEvidenceDiagnostics = {
  no_live_external_calls: true;
  live_provider_calls_attempted: false;
  live_llm_calls_attempted: false;
  availability_contract_created_generated_output: false;
  no_new_generated_output: true;
  generated_comparison_available: boolean;
  source_policy_enforced: true;
  same_comparison_pack_sources_only: true;
  unavailable_reasons: string[];
  empty_state_reason: string | null;
};

type ComparisonEvidenceSourceReference = {
  source_document_id: string;
  asset_ticker: string;
  source_type: string;
  title: string;
  publisher: string;
  url: string;
  published_at: string | null;
  as_of_date: string | null;
  retrieved_at: string;
  freshness_state: FreshnessState;
  is_official: boolean;
  source_quality: ComparisonSourceQuality;
  allowlist_status: ComparisonSourceAllowlistStatus;
  source_use_policy: ComparisonSourceUsePolicy;
  permitted_operations: ComparisonSourceOperationPermissions;
};

export type ComparisonEvidenceAvailability = {
  schema_version: "comparison-evidence-availability-v1";
  comparison_id: string;
  comparison_type: string;
  left_asset: CompareAssetIdentity;
  right_asset: CompareAssetIdentity;
  availability_state: ComparisonEvidenceAvailabilityState;
  required_dimensions: string[];
  required_evidence_dimensions: ComparisonEvidenceDimension[];
  evidence_items: ComparisonEvidenceItem[];
  claim_bindings: ComparisonEvidenceClaimBinding[];
  citation_bindings: ComparisonEvidenceCitationBinding[];
  source_references: ComparisonEvidenceSourceReference[];
  diagnostics: ComparisonEvidenceDiagnostics;
};

export type ComparePageFixture = {
  left_asset: CompareAssetIdentity;
  right_asset: CompareAssetIdentity;
  state: {
    status: CompareStateStatus;
    message: string;
  };
  comparison_type: string;
  key_differences: ComparisonKeyDifference[];
  bottom_line_for_beginners: ComparisonBeginnerBottomLine | null;
  citations: ComparisonCitation[];
  source_documents: ComparisonSourceDocument[];
  evidence_availability: ComparisonEvidenceAvailability | null;
  stock_etf_relationship?: StockEtfRelationshipModel | null;
};

const retrieved_at = "2026-04-20T00:00:00Z";
const as_of_date = "2026-04-01";
const REQUIRED_COMPARISON_DIMENSIONS: ComparisonRequiredDimension[] = [
  "Benchmark",
  "Expense ratio",
  "Holdings count",
  "Breadth",
  "Educational role"
];
const STOCK_ETF_COMPARISON_DIMENSIONS: StockEtfRequiredDimension[] = [
  "Structure",
  "Basket membership",
  "Breadth",
  "Cost model",
  "Educational role"
];
const DEFAULT_ALLOWED_SOURCE_OPERATIONS: ComparisonSourceOperationPermissions = {
  can_store_metadata: true,
  can_store_raw_text: true,
  can_display_metadata: true,
  can_display_excerpt: true,
  can_summarize: true,
  can_cache: true,
  can_export_metadata: true,
  can_export_excerpt: true,
  can_export_full_text: false,
  can_support_generated_output: true,
  can_support_citations: true,
  can_support_canonical_facts: true,
  can_support_recent_developments: false
};

const comparisonCitationIds: Record<"VOO" | "QQQ", Record<ComparisonFactKind, string>> = {
  VOO: {
    benchmark: "c_fact_voo_benchmark",
    expense_ratio: "c_fact_voo_expense_ratio",
    holdings_count: "c_fact_voo_holdings_count",
    beginner_role: "c_fact_voo_role"
  },
  QQQ: {
    benchmark: "c_fact_qqq_benchmark",
    expense_ratio: "c_fact_qqq_expense_ratio",
    holdings_count: "c_fact_qqq_holdings_count",
    beginner_role: "c_fact_qqq_role"
  }
};

const supportedComparisonFacts: Record<
  "VOO" | "QQQ",
  {
    benchmark: string;
    expense_ratio: string;
    holdings_count: string;
    holdings_count_number: number;
    beginner_role: string;
    role_phrase: string;
    title: string;
    publisher: string;
    source_document_id: string;
    url: string;
    supporting_passage: string;
  }
> = {
  VOO: {
    benchmark: "S&P 500 Index",
    expense_ratio: "0.03%",
    holdings_count: "500 approximate companies",
    holdings_count_number: 500,
    beginner_role: "Broad U.S. large-company ETF",
    role_phrase: "broad U.S. large-company ETF",
    title: "Vanguard S&P 500 ETF fact sheet fixture excerpt",
    publisher: "Vanguard",
    source_document_id: "src_voo_fact_sheet_fixture",
    url: "https://investor.vanguard.com/",
    supporting_passage: "VOO seeks to track the performance of the S&P 500 Index, which represents large U.S. companies."
  },
  QQQ: {
    benchmark: "Nasdaq-100 Index",
    expense_ratio: "0.2%",
    holdings_count: "100 approximate companies",
    holdings_count_number: 100,
    beginner_role: "Narrower growth-oriented ETF",
    role_phrase: "narrower growth-oriented ETF",
    title: "Invesco QQQ Trust fact sheet fixture excerpt",
    publisher: "Invesco",
    source_document_id: "src_qqq_fact_sheet_fixture",
    url: "https://www.invesco.com/",
    supporting_passage: "QQQ seeks investment results that generally correspond to the Nasdaq-100 Index."
  }
};

export function getComparePageFixture(leftTicker: string, rightTicker: string): ComparePageFixture {
  const left = normalizeTicker(leftTicker);
  const right = normalizeTicker(rightTicker);

  if ((left === "VOO" && right === "QQQ") || (left === "QQQ" && right === "VOO")) {
    return buildSupportedComparison(left, right);
  }

  if ((left === "AAPL" && right === "VOO") || (left === "VOO" && right === "AAPL")) {
    return buildSupportedStockEtfComparison(left as "AAPL" | "VOO", right as "AAPL" | "VOO");
  }

  const left_asset = assetIdentityForTicker(left);
  const right_asset = assetIdentityForTicker(right);
  const state = unavailableStateFor(left_asset, right_asset);
  const availability_state = unavailableAvailabilityStateFor(left, right);

  return {
    left_asset,
    right_asset,
    state,
    comparison_type: "unavailable",
    key_differences: [],
    bottom_line_for_beginners: null,
    citations: [],
    source_documents: [],
    evidence_availability: buildUnavailableEvidenceAvailability(left_asset, right_asset, availability_state, state.message)
  };
}

export function getComparisonAvailabilityState(comparison: ComparePageFixture): ComparisonEvidenceAvailabilityState {
  return comparison.evidence_availability?.availability_state ?? "unavailable";
}

export function isComparisonAvailable(comparison: ComparePageFixture) {
  return getComparisonAvailabilityState(comparison) === "available";
}

export function getComparisonCitationMetadata(comparison: ComparePageFixture) {
  const citations_by_id = new Map(comparison.citations.map((citation) => [citation.citation_id, citation]));
  const contexts_by_source_document_id = new Map<string, ComparisonClaimContext[]>();

  function addContext(citation_id: string, context: Omit<ComparisonClaimContext, "citation_id">) {
    const citation = citations_by_id.get(citation_id);
    if (!citation) {
      return;
    }

    const contexts = contexts_by_source_document_id.get(citation.source_document_id) ?? [];
    contexts.push({ citation_id, ...context });
    contexts_by_source_document_id.set(citation.source_document_id, contexts);
  }

  for (const difference of comparison.key_differences) {
    for (const citation_id of difference.citation_ids) {
      addContext(citation_id, {
        section: "Key difference",
        label: difference.dimension,
        claim_text: difference.plain_english_summary
      });
    }
  }

  if (comparison.bottom_line_for_beginners) {
    for (const citation_id of comparison.bottom_line_for_beginners.citation_ids) {
      addContext(citation_id, {
        section: "Bottom line for beginners",
        label: "Educational context",
        claim_text: comparison.bottom_line_for_beginners.summary
      });
    }
  }

  return { citations_by_id, contexts_by_source_document_id };
}

function buildSupportedComparison(left: "VOO" | "QQQ", right: "VOO" | "QQQ"): ComparePageFixture {
  const left_facts = supportedComparisonFacts[left];
  const right_facts = supportedComparisonFacts[right];
  const broader = left_facts.holdings_count_number >= right_facts.holdings_count_number ? left : right;
  const narrower = broader === left ? right : left;

  const key_differences: ComparisonKeyDifference[] = [
    {
      dimension: "Benchmark",
      plain_english_summary: `${left} tracks the ${left_facts.benchmark}, while ${right} tracks the ${right_facts.benchmark}.`,
      citation_ids: [citationIdFor(left, "benchmark"), citationIdFor(right, "benchmark")]
    },
    {
      dimension: "Expense ratio",
      plain_english_summary: `The fixture records ${left}'s expense ratio as ${left_facts.expense_ratio} and ${right}'s as ${right_facts.expense_ratio}.`,
      citation_ids: [citationIdFor(left, "expense_ratio"), citationIdFor(right, "expense_ratio")]
    },
    {
      dimension: "Holdings count",
      plain_english_summary: `The local facts list ${left} with about ${left_facts.holdings_count} and ${right} with about ${right_facts.holdings_count}.`,
      citation_ids: [citationIdFor(left, "holdings_count"), citationIdFor(right, "holdings_count")]
    },
    {
      dimension: "Breadth",
      plain_english_summary: `Using holdings count as the local breadth signal, ${broader} is broader than ${narrower}; this is not a full overlap calculation.`,
      citation_ids: [citationIdFor(left, "holdings_count"), citationIdFor(right, "holdings_count")]
    },
    {
      dimension: "Educational role",
      plain_english_summary: `The local education facts frame ${left} as ${left_facts.role_phrase} and ${right} as ${right_facts.role_phrase}.`,
      citation_ids: [citationIdFor(left, "beginner_role"), citationIdFor(right, "beginner_role")]
    }
  ];

  const bottom_line_for_beginners: ComparisonBeginnerBottomLine = {
    summary: `For beginner learning, ${left} is framed as ${left_facts.role_phrase}, while ${right} is framed as ${right_facts.role_phrase}. Compare their benchmark, cost, and holdings breadth as source-backed structure facts, not as a personal decision rule.`,
    citation_ids: [
      citationIdFor(left, "beginner_role"),
      citationIdFor(right, "beginner_role"),
      citationIdFor(left, "holdings_count"),
      citationIdFor(right, "holdings_count"),
      citationIdFor(left, "expense_ratio"),
      citationIdFor(right, "expense_ratio")
    ]
  };

  const response: ComparePageFixture = {
    left_asset: assetIdentityForTicker(left),
    right_asset: assetIdentityForTicker(right),
    state: {
      status: "supported",
      message: "Comparison is supported by deterministic local retrieval fixtures."
    },
    comparison_type: "etf_vs_etf",
    key_differences,
    bottom_line_for_beginners,
    citations: [
      citationFor("QQQ", "benchmark"),
      citationFor("QQQ", "expense_ratio"),
      citationFor("QQQ", "holdings_count"),
      citationFor("QQQ", "beginner_role"),
      citationFor("VOO", "benchmark"),
      citationFor("VOO", "expense_ratio"),
      citationFor("VOO", "holdings_count"),
      citationFor("VOO", "beginner_role")
    ],
    source_documents: [sourceDocumentFor("QQQ"), sourceDocumentFor("VOO")],
    evidence_availability: null,
    stock_etf_relationship: null
  };

  response.evidence_availability = buildAvailableEvidenceAvailability(response);
  return response;
}

function buildSupportedStockEtfComparison(left: "AAPL" | "VOO", right: "AAPL" | "VOO"): ComparePageFixture {
  const stockTicker = left === "AAPL" ? left : right;
  const etfTicker = stockTicker === left ? right : left;
  const stockCitation = "c_compare_aapl_company_profile";
  const etfProfileCitation = "c_compare_voo_basket_profile";
  const etfHoldingsCitation = "c_compare_voo_aapl_top_holding";
  const etfHoldingsCountCitation = "c_compare_voo_holdings_count";
  const etfExpenseCitation = "c_compare_voo_expense_ratio";

  const key_differences: ComparisonKeyDifference[] = [
    {
      dimension: "Structure",
      plain_english_summary: `${stockTicker} is represented by the local filing fixture as one operating company, while ${etfTicker} is represented by issuer fixtures as an ETF basket that tracks the S&P 500 Index.`,
      citation_ids: [stockCitation, etfProfileCitation]
    },
    {
      dimension: "Basket membership",
      plain_english_summary: `${etfTicker}'s local holdings fixture lists Apple among top holdings, but the deterministic pack does not include a verified holding weight or full overlap calculation.`,
      citation_ids: [etfHoldingsCitation]
    },
    {
      dimension: "Breadth",
      plain_english_summary: `${stockTicker} is one company in this comparison, while the local facts list ${etfTicker} with about 500 holdings.`,
      citation_ids: [stockCitation, etfHoldingsCountCitation]
    },
    {
      dimension: "Cost model",
      plain_english_summary: `${etfTicker} has an ETF expense-ratio fact in the local issuer fixture; ${stockTicker} is a common stock in this pack, so an ETF expense ratio is not the matching comparison field.`,
      citation_ids: [stockCitation, etfExpenseCitation]
    },
    {
      dimension: "Educational role",
      plain_english_summary: `This stock-vs-ETF view separates learning about ${stockTicker}'s single business from learning about ${etfTicker}'s basket exposure.`,
      citation_ids: [stockCitation, etfProfileCitation, etfHoldingsCitation]
    }
  ];

  const bottom_line_for_beginners: ComparisonBeginnerBottomLine = {
    summary: `${stockTicker} and ${etfTicker} are different structures: one is a single company, and the other is an ETF basket. The local evidence verifies that Apple appears in the VOO holdings fixture, but it does not verify a precise holding weight or full overlap calculation, so this page treats the relationship as partial educational context rather than a decision rule.`,
    citation_ids: [stockCitation, etfProfileCitation, etfHoldingsCitation, etfHoldingsCountCitation]
  };

  const response: ComparePageFixture = {
    left_asset: assetIdentityForTicker(left),
    right_asset: assetIdentityForTicker(right),
    state: {
      status: "supported",
      message: "Stock-vs-ETF comparison is supported by deterministic local retrieval fixtures."
    },
    comparison_type: "stock_vs_etf",
    key_differences,
    bottom_line_for_beginners,
    citations: [
      {
        citation_id: stockCitation,
        source_document_id: "src_aapl_10k_fixture",
        title: "Apple Inc. Form 10-K fixture excerpt",
        publisher: "Apple",
        freshness_state: "fresh"
      },
      {
        citation_id: etfProfileCitation,
        source_document_id: "src_voo_fact_sheet_fixture",
        title: "Vanguard S&P 500 ETF fact sheet fixture excerpt",
        publisher: "Vanguard",
        freshness_state: "fresh"
      },
      {
        citation_id: etfHoldingsCitation,
        source_document_id: "src_voo_holdings_fixture",
        title: "Vanguard S&P 500 ETF holdings fixture excerpt",
        publisher: "Vanguard",
        freshness_state: "fresh"
      },
      {
        citation_id: etfHoldingsCountCitation,
        source_document_id: "src_voo_fact_sheet_fixture",
        title: "Vanguard S&P 500 ETF fact sheet fixture excerpt",
        publisher: "Vanguard",
        freshness_state: "fresh"
      },
      {
        citation_id: etfExpenseCitation,
        source_document_id: "src_voo_fact_sheet_fixture",
        title: "Vanguard S&P 500 ETF fact sheet fixture excerpt",
        publisher: "Vanguard",
        freshness_state: "fresh"
      }
    ],
    source_documents: [
      stockEtfSourceDocumentFor("src_aapl_10k_fixture"),
      stockEtfSourceDocumentFor("src_voo_fact_sheet_fixture"),
      stockEtfSourceDocumentFor("src_voo_holdings_fixture")
    ],
    evidence_availability: null,
    stock_etf_relationship: {
      schema_version: "stock-etf-relationship-v1",
      comparison_type: "stock_vs_etf",
      stock_ticker: stockTicker,
      etf_ticker: etfTicker,
      relationship_state: "direct_holding",
      evidence_state: "partial",
      badges: [
        {
          label: "Comparison type",
          value: "Stock vs ETF",
          marker: "comparison_type",
          relationship_state: "direct_holding",
          evidence_state: "supported",
          citation_ids: [stockCitation, etfProfileCitation]
        },
        {
          label: "Stock ticker",
          value: stockTicker,
          marker: "stock_ticker",
          relationship_state: "direct_holding",
          evidence_state: "supported",
          citation_ids: [stockCitation]
        },
        {
          label: "ETF ticker",
          value: etfTicker,
          marker: "etf_ticker",
          relationship_state: "direct_holding",
          evidence_state: "supported",
          citation_ids: [etfProfileCitation]
        },
        {
          label: "Relationship state",
          value: "Top-holding membership verified; exact overlap weight unavailable",
          marker: "relationship_state",
          relationship_state: "direct_holding",
          evidence_state: "partial",
          citation_ids: [etfHoldingsCitation]
        },
        {
          label: "Evidence boundary",
          value: "Same comparison pack only",
          marker: "evidence_boundary",
          relationship_state: "direct_holding",
          evidence_state: "supported",
          citation_ids: [stockCitation, etfProfileCitation, etfHoldingsCitation]
        }
      ],
      basket_structure: {
        stock_ticker: stockTicker,
        etf_ticker: etfTicker,
        stock_role_summary: `${stockTicker} is shown as a single company with products, services, and company-specific risks.`,
        etf_basket_summary: `${etfTicker} is shown as an ETF basket with about 500 holdings in the local fixture.`,
        relationship_summary:
          "The local VOO holdings fixture lists Apple among top holdings. The pack does not include exact holding weight or full overlap evidence, so the relationship is labeled partial.",
        overlap_or_membership_state: "direct_holding",
        evidence_state: "partial",
        unavailable_detail: "Exact holding weight, top-10 concentration, sector exposure, and full overlap are unavailable in this deterministic pack.",
        citation_ids: [stockCitation, etfProfileCitation, etfHoldingsCitation, etfHoldingsCountCitation]
      }
    }
  };

  response.evidence_availability = buildStockEtfEvidenceAvailability(response);
  return response;
}

function assetIdentityForTicker(ticker: string): CompareAssetIdentity {
  const normalized = normalizeTicker(ticker);
  const fixture = getAssetFixture(normalized);
  if (fixture) {
    return {
      ticker: fixture.ticker,
      name: fixture.name,
      asset_type: fixture.assetType,
      exchange: fixture.exchange,
      issuer: fixture.issuer ?? null,
      status: "supported",
      supported: true
    };
  }

  const resolved = resolveLocalSearchResponse(normalized).results[0];
  const support_classification = (resolved?.support_classification ?? "unknown") as SearchSupportClassification;

  return {
    ticker: resolved?.ticker ?? normalized,
    name: resolved?.name ?? normalized,
    asset_type: resolved?.asset_type ?? "unknown",
    exchange: resolved?.exchange ?? null,
    issuer: resolved?.issuer ?? null,
    status: support_classification === "recognized_unsupported" ? "unsupported" : "unknown",
    supported: false
  };
}

function unavailableStateFor(left_asset: CompareAssetIdentity, right_asset: CompareAssetIdentity) {
  if (!left_asset.supported) {
    return {
      status: left_asset.status,
      message: unavailableMessageForTicker(left_asset.ticker)
    };
  }

  if (!right_asset.supported) {
    return {
      status: right_asset.status,
      message: unavailableMessageForTicker(right_asset.ticker)
    };
  }

  return {
    status: "unknown" as const,
    message: "No deterministic local comparison knowledge pack is available for these tickers."
  };
}

function unavailableAvailabilityStateFor(
  leftTicker: string,
  rightTicker: string
): ComparisonEvidenceAvailabilityState {
  for (const ticker of [leftTicker, rightTicker]) {
    const support_classification = supportClassificationForTicker(ticker);
    if (support_classification === "out_of_scope") {
      return "out_of_scope";
    }
    if (support_classification === "eligible_not_cached") {
      return "eligible_not_cached";
    }
    if (support_classification === "recognized_unsupported") {
      return "unsupported";
    }
    if (support_classification === "unknown") {
      return "unknown";
    }
  }

  return "no_local_pack";
}

function buildAvailableEvidenceAvailability(comparison: ComparePageFixture): ComparisonEvidenceAvailability {
  const source_documents_by_id = new Map(
    comparison.source_documents.map((source_document) => [source_document.source_document_id, source_document])
  );
  const citation_by_id = new Map(comparison.citations.map((citation) => [citation.citation_id, citation]));
  const evidence_items: ComparisonEvidenceItem[] = [];
  const required_evidence_dimensions: ComparisonEvidenceDimension[] = [];
  const claim_bindings: ComparisonEvidenceClaimBinding[] = [];
  const citation_bindings: ComparisonEvidenceCitationBinding[] = [];
  const evidence_item_ids_by_dimension = new Map<string, string[]>();

  for (const dimension of REQUIRED_COMPARISON_DIMENSIONS) {
    const left_items = availableEvidenceItemsForDimension(dimension, "left", comparison.left_asset.ticker);
    const right_items = availableEvidenceItemsForDimension(dimension, "right", comparison.right_asset.ticker);
    const dimension_items = [...left_items, ...right_items];

    evidence_items.push(...dimension_items);
    evidence_item_ids_by_dimension.set(
      dimension,
      dimension_items.map((item) => item.evidence_item_id)
    );

    required_evidence_dimensions.push({
      dimension,
      required: true,
      availability_state: "available",
      evidence_state: "supported",
      freshness_state: "fresh",
      left_evidence_item_ids: left_items.map((item) => item.evidence_item_id),
      right_evidence_item_ids: right_items.map((item) => item.evidence_item_id),
      shared_evidence_item_ids: [],
      citation_ids: Array.from(new Set(dimension_items.flatMap((item) => item.citation_ids))),
      source_document_ids: Array.from(
        new Set(
          dimension_items
            .map((item) => item.source_document_id)
            .filter((source_document_id): source_document_id is string => source_document_id !== null)
        )
      ),
      generated_claim_ids: [claimIdForDimension(dimension)]
    });
  }

  for (const difference of comparison.key_differences) {
    const claim_id = claimIdForDimension(difference.dimension as ComparisonRequiredDimension);
    claim_bindings.push({
      claim_id,
      claim_kind: "key_difference",
      dimension: difference.dimension,
      side_role: "shared_comparison_support",
      citation_ids: difference.citation_ids,
      source_document_ids: sourceDocumentIdsForCitations(difference.citation_ids, citation_by_id),
      evidence_item_ids: evidence_item_ids_by_dimension.get(difference.dimension) ?? [],
      availability_state: "available"
    });
    citation_bindings.push(
      ...buildCitationBindings(
        claim_id,
        difference.dimension,
        difference.citation_ids,
        source_documents_by_id,
        comparison.left_asset.ticker,
        comparison.right_asset.ticker
      )
    );
  }

  if (comparison.bottom_line_for_beginners) {
    const bottom_line_dimensions = ["Expense ratio", "Holdings count", "Educational role"];
    const bottom_line_evidence_item_ids = bottom_line_dimensions.flatMap(
      (dimension) => evidence_item_ids_by_dimension.get(dimension) ?? []
    );

    claim_bindings.push({
      claim_id: "claim_comparison_bottom_line",
      claim_kind: "beginner_bottom_line",
      dimension: "Beginner bottom line",
      side_role: "shared_comparison_support",
      citation_ids: comparison.bottom_line_for_beginners.citation_ids,
      source_document_ids: sourceDocumentIdsForCitations(comparison.bottom_line_for_beginners.citation_ids, citation_by_id),
      evidence_item_ids: bottom_line_evidence_item_ids,
      availability_state: "available"
    });
    citation_bindings.push(
      ...buildCitationBindings(
        "claim_comparison_bottom_line",
        "Beginner bottom line",
        comparison.bottom_line_for_beginners.citation_ids,
        source_documents_by_id,
        comparison.left_asset.ticker,
        comparison.right_asset.ticker
      )
    );
  }

  return {
    schema_version: "comparison-evidence-availability-v1",
    comparison_id: comparisonId(comparison.left_asset.ticker, comparison.right_asset.ticker),
    comparison_type: comparison.comparison_type,
    left_asset: comparison.left_asset,
    right_asset: comparison.right_asset,
    availability_state: "available",
    required_dimensions: REQUIRED_COMPARISON_DIMENSIONS,
    required_evidence_dimensions,
    evidence_items,
    claim_bindings,
    citation_bindings,
    source_references: comparison.source_documents.map((source_document) => ({
      source_document_id: source_document.source_document_id,
      asset_ticker: assetTickerForSourceDocumentId(source_document.source_document_id),
      source_type: source_document.source_type,
      title: source_document.title,
      publisher: source_document.publisher,
      url: source_document.url,
      published_at: source_document.published_at,
      as_of_date: source_document.as_of_date,
      retrieved_at: source_document.retrieved_at,
      freshness_state: source_document.freshness_state,
      is_official: source_document.is_official,
      source_quality: source_document.source_quality,
      allowlist_status: source_document.allowlist_status,
      source_use_policy: source_document.source_use_policy,
      permitted_operations: source_document.permitted_operations
    })),
    diagnostics: {
      no_live_external_calls: true,
      live_provider_calls_attempted: false,
      live_llm_calls_attempted: false,
      availability_contract_created_generated_output: false,
      no_new_generated_output: true,
      generated_comparison_available: true,
      source_policy_enforced: true,
      same_comparison_pack_sources_only: true,
      unavailable_reasons: [],
      empty_state_reason: null
    }
  };
}

function buildStockEtfEvidenceAvailability(comparison: ComparePageFixture): ComparisonEvidenceAvailability {
  const source_documents_by_id = new Map(
    comparison.source_documents.map((source_document) => [source_document.source_document_id, source_document])
  );
  const citation_by_id = new Map(comparison.citations.map((citation) => [citation.citation_id, citation]));
  const evidence_items: ComparisonEvidenceItem[] = [];
  const required_evidence_dimensions: ComparisonEvidenceDimension[] = [];
  const claim_bindings: ComparisonEvidenceClaimBinding[] = [];
  const citation_bindings: ComparisonEvidenceCitationBinding[] = [];
  const evidence_item_ids_by_dimension = new Map<string, string[]>();

  for (const difference of comparison.key_differences) {
    const dimension_items = difference.citation_ids.flatMap((citation_id, index) => {
      const citation = citation_by_id.get(citation_id);
      if (!citation) {
        return [];
      }
      const source_document = source_documents_by_id.get(citation.source_document_id);
      if (!source_document) {
        return [];
      }
      const asset_ticker = assetTickerForStockEtfCitationId(citation_id);
      const item: ComparisonEvidenceItem = {
        evidence_item_id: `evidence_${claimSlug(difference.dimension)}_${asset_ticker.toLowerCase()}_${index + 1}`,
        dimension: difference.dimension,
        side: comparison.left_asset.ticker === asset_ticker ? "left" : "right",
        side_role: sideRoleForAsset(asset_ticker, comparison.left_asset.ticker, comparison.right_asset.ticker),
        asset_ticker,
        field_name: claimSlug(difference.dimension),
        fact_id: `fact_compare_${asset_ticker.toLowerCase()}_${claimSlug(difference.dimension)}_${index + 1}`,
        source_chunk_id: `chunk_compare_${asset_ticker.toLowerCase()}_${claimSlug(difference.dimension)}_${index + 1}`,
        source_document_id: source_document.source_document_id,
        citation_ids: [citation_id],
        evidence_state: difference.dimension === "Basket membership" ? "partial" : "supported",
        freshness_state: source_document.freshness_state,
        as_of_date: source_document.as_of_date,
        retrieved_at: source_document.retrieved_at,
        is_official: source_document.is_official,
        source_quality: source_document.source_quality,
        allowlist_status: source_document.allowlist_status,
        source_use_policy: source_document.source_use_policy,
        permitted_operations: source_document.permitted_operations,
        unavailable_reason:
          difference.dimension === "Basket membership"
            ? "Exact holding weight and full overlap calculation are unavailable in this deterministic comparison pack."
            : null
      };
      return [item];
    });

    evidence_items.push(...dimension_items);
    evidence_item_ids_by_dimension.set(
      difference.dimension,
      dimension_items.map((item) => item.evidence_item_id)
    );

    required_evidence_dimensions.push({
      dimension: difference.dimension,
      required: true,
      availability_state: "available",
      evidence_state: difference.dimension === "Basket membership" ? "partial" : "supported",
      freshness_state: "fresh",
      left_evidence_item_ids: dimension_items
        .filter((item) => item.side === "left")
        .map((item) => item.evidence_item_id),
      right_evidence_item_ids: dimension_items
        .filter((item) => item.side === "right")
        .map((item) => item.evidence_item_id),
      shared_evidence_item_ids: [],
      citation_ids: difference.citation_ids,
      source_document_ids: sourceDocumentIdsForCitations(difference.citation_ids, citation_by_id),
      generated_claim_ids: [claimIdForDimension(difference.dimension as ComparisonRequiredDimension)],
      unavailable_reason:
        difference.dimension === "Basket membership"
          ? "Exact holding weight and full overlap calculation are unavailable in this deterministic comparison pack."
          : null
    });

    const claim_id = claimIdForDimension(difference.dimension as ComparisonRequiredDimension);
    claim_bindings.push({
      claim_id,
      claim_kind: "key_difference",
      dimension: difference.dimension,
      side_role: "shared_comparison_support",
      citation_ids: difference.citation_ids,
      source_document_ids: sourceDocumentIdsForCitations(difference.citation_ids, citation_by_id),
      evidence_item_ids: evidence_item_ids_by_dimension.get(difference.dimension) ?? [],
      availability_state: "available"
    });

    citation_bindings.push(
      ...buildCitationBindings(
        claim_id,
        difference.dimension,
        difference.citation_ids,
        source_documents_by_id,
        comparison.left_asset.ticker,
        comparison.right_asset.ticker
      )
    );
  }

  if (comparison.bottom_line_for_beginners) {
    claim_bindings.push({
      claim_id: "claim_stock_etf_bottom_line",
      claim_kind: "beginner_bottom_line",
      dimension: "Beginner bottom line",
      side_role: "shared_comparison_support",
      citation_ids: comparison.bottom_line_for_beginners.citation_ids,
      source_document_ids: sourceDocumentIdsForCitations(comparison.bottom_line_for_beginners.citation_ids, citation_by_id),
      evidence_item_ids: Array.from(evidence_item_ids_by_dimension.values()).flat(),
      availability_state: "available"
    });
    citation_bindings.push(
      ...buildCitationBindings(
        "claim_stock_etf_bottom_line",
        "Beginner bottom line",
        comparison.bottom_line_for_beginners.citation_ids,
        source_documents_by_id,
        comparison.left_asset.ticker,
        comparison.right_asset.ticker
      )
    );
  }

  return {
    schema_version: "comparison-evidence-availability-v1",
    comparison_id: comparisonId(comparison.left_asset.ticker, comparison.right_asset.ticker),
    comparison_type: comparison.comparison_type,
    left_asset: comparison.left_asset,
    right_asset: comparison.right_asset,
    availability_state: "available",
    required_dimensions: STOCK_ETF_COMPARISON_DIMENSIONS,
    required_evidence_dimensions,
    evidence_items,
    claim_bindings,
    citation_bindings,
    source_references: comparison.source_documents.map((source_document) => ({
      source_document_id: source_document.source_document_id,
      asset_ticker: assetTickerForStockEtfSourceDocumentId(source_document.source_document_id),
      source_type: source_document.source_type,
      title: source_document.title,
      publisher: source_document.publisher,
      url: source_document.url,
      published_at: source_document.published_at,
      as_of_date: source_document.as_of_date,
      retrieved_at: source_document.retrieved_at,
      freshness_state: source_document.freshness_state,
      is_official: source_document.is_official,
      source_quality: source_document.source_quality,
      allowlist_status: source_document.allowlist_status,
      source_use_policy: source_document.source_use_policy,
      permitted_operations: source_document.permitted_operations
    })),
    diagnostics: {
      no_live_external_calls: true,
      live_provider_calls_attempted: false,
      live_llm_calls_attempted: false,
      availability_contract_created_generated_output: false,
      no_new_generated_output: true,
      generated_comparison_available: true,
      source_policy_enforced: true,
      same_comparison_pack_sources_only: true,
      unavailable_reasons: [
        "Exact holding weight and full overlap calculation are unavailable in this deterministic comparison pack."
      ],
      empty_state_reason: null
    }
  };
}

function buildUnavailableEvidenceAvailability(
  left_asset: CompareAssetIdentity,
  right_asset: CompareAssetIdentity,
  availability_state: ComparisonEvidenceAvailabilityState,
  message: string
): ComparisonEvidenceAvailability {
  return {
    schema_version: "comparison-evidence-availability-v1",
    comparison_id: comparisonId(left_asset.ticker, right_asset.ticker),
    comparison_type: "unavailable",
    left_asset,
    right_asset,
    availability_state,
    required_dimensions: REQUIRED_COMPARISON_DIMENSIONS,
    required_evidence_dimensions: REQUIRED_COMPARISON_DIMENSIONS.map((dimension) => ({
      dimension,
      required: true,
      availability_state,
      evidence_state: evidenceStateForAvailability(availability_state),
      freshness_state: availability_state === "stale" ? "stale" : "unavailable",
      left_evidence_item_ids: [],
      right_evidence_item_ids: [],
      shared_evidence_item_ids: [],
      citation_ids: [],
      source_document_ids: [],
      generated_claim_ids: [],
      unavailable_reason: message
    })),
    evidence_items: [],
    claim_bindings: [],
    citation_bindings: [],
    source_references: [],
    diagnostics: {
      no_live_external_calls: true,
      live_provider_calls_attempted: false,
      live_llm_calls_attempted: false,
      availability_contract_created_generated_output: false,
      no_new_generated_output: true,
      generated_comparison_available: false,
      source_policy_enforced: true,
      same_comparison_pack_sources_only: true,
      unavailable_reasons: [message],
      empty_state_reason: message
    }
  };
}

function availableEvidenceItemsForDimension(
  dimension: ComparisonRequiredDimension,
  side: "left" | "right",
  ticker: string
): ComparisonEvidenceItem[] {
  const normalized = normalizeTicker(ticker) as "VOO" | "QQQ";
  const field_name = fieldNameForDimension(dimension);
  const citation_id = citationIdFor(normalized, field_name);
  const source_document = sourceDocumentFor(normalized);
  const side_role = side === "left" ? "left_side_support" : "right_side_support";

  return [
    {
      evidence_item_id: `evidence_${claimSlug(dimension)}_${side}_${normalized.toLowerCase()}_${field_name}`,
      dimension,
      side,
      side_role,
      asset_ticker: normalized,
      field_name,
      fact_id: `fact_compare_${normalized.toLowerCase()}_${field_name}`,
      source_chunk_id: `chunk_compare_${normalized.toLowerCase()}_${field_name}`,
      source_document_id: source_document.source_document_id,
      citation_ids: [citation_id],
      evidence_state: "supported",
      freshness_state: "fresh",
      as_of_date,
      retrieved_at,
      is_official: true,
      source_quality: source_document.source_quality,
      allowlist_status: source_document.allowlist_status,
      source_use_policy: source_document.source_use_policy,
      permitted_operations: source_document.permitted_operations
    }
  ];
}

function buildCitationBindings(
  claim_id: string,
  dimension: string,
  citation_ids: string[],
  source_documents_by_id: Map<string, ComparisonSourceDocument>,
  leftTicker: string,
  rightTicker: string
) {
  return citation_ids.flatMap((citation_id) => {
    const asset_ticker = assetTickerForCitationId(citation_id);
    const source_document = source_documents_by_id.get(sourceDocumentIdForCitationId(citation_id));
    if (!source_document) {
      return [];
    }

    return [
      {
        binding_id: `${claim_id}_${citation_id}`,
        claim_id,
        dimension,
        citation_id,
        source_document_id: source_document.source_document_id,
        asset_ticker,
        side_role: sideRoleForAsset(asset_ticker, leftTicker, rightTicker),
        freshness_state: source_document.freshness_state,
        source_quality: source_document.source_quality,
        allowlist_status: source_document.allowlist_status,
        source_use_policy: source_document.source_use_policy,
        permitted_operations: source_document.permitted_operations,
        supports_generated_claim: true
      }
    ];
  });
}

function sourceDocumentIdsForCitations(
  citation_ids: string[],
  citation_by_id: Map<string, ComparisonCitation>
) {
  return Array.from(
    new Set(
      citation_ids
        .map((citation_id) => citation_by_id.get(citation_id)?.source_document_id)
        .filter((source_document_id): source_document_id is string => Boolean(source_document_id))
    )
  );
}

function evidenceStateForAvailability(
  availability_state: ComparisonEvidenceAvailabilityState
): ComparisonEvidenceState {
  if (availability_state === "unsupported") {
    return "unsupported";
  }
  if (availability_state === "stale") {
    return "stale";
  }
  if (availability_state === "partial" || availability_state === "no_local_pack") {
    return "mixed";
  }
  if (availability_state === "insufficient_evidence") {
    return "insufficient_evidence";
  }
  if (availability_state === "unknown") {
    return "unknown";
  }
  return "unavailable";
}

function supportClassificationForTicker(ticker: string): SearchSupportClassification {
  const normalized = normalizeTicker(ticker);
  return (resolveLocalSearchResponse(normalized).results[0]?.support_classification ?? "unknown") as SearchSupportClassification;
}

function unavailableMessageForTicker(ticker: string) {
  const normalized = normalizeTicker(ticker);
  const result = resolveLocalSearchResponse(normalized).results[0];
  const support_classification = (result?.support_classification ?? "unknown") as SearchSupportClassification;

  if (support_classification === "recognized_unsupported") {
    return result?.message ?? "Recognized asset type is outside the current product scope.";
  }
  if (support_classification === "out_of_scope") {
    return (
      result?.message ??
      "Recognized U.S.-listed common stock outside the current Top-500 manifest-backed support scope."
    );
  }
  if (support_classification === "eligible_not_cached") {
    return (
      result?.message ??
      "Eligible U.S.-listed common stock or plain-vanilla ETF, but no local cached knowledge pack is available yet."
    );
  }
  return "No local retrieval fixture is available for this ticker.";
}

function citationFor(ticker: "VOO" | "QQQ", fact: ComparisonFactKind): ComparisonCitation {
  const source = supportedComparisonFacts[ticker];

  return {
    citation_id: citationIdFor(ticker, fact),
    source_document_id: source.source_document_id,
    title: source.title,
    publisher: source.publisher,
    freshness_state: "fresh"
  };
}

function citationIdFor(ticker: "VOO" | "QQQ", fact: ComparisonFactKind) {
  return comparisonCitationIds[ticker][fact];
}

function sourceDocumentFor(ticker: "VOO" | "QQQ"): ComparisonSourceDocument {
  const source = supportedComparisonFacts[ticker];

  return {
    source_document_id: source.source_document_id,
    source_type: "issuer_fact_sheet",
    title: source.title,
    publisher: source.publisher,
    url: source.url,
    published_at: as_of_date,
    as_of_date,
    retrieved_at,
    freshness_state: "fresh",
    is_official: true,
    supporting_passage: source.supporting_passage,
    source_quality: "issuer",
    allowlist_status: "allowed",
    source_use_policy: "full_text_allowed",
    permitted_operations: DEFAULT_ALLOWED_SOURCE_OPERATIONS
  };
}

function stockEtfSourceDocumentFor(sourceDocumentId: "src_aapl_10k_fixture" | "src_voo_fact_sheet_fixture" | "src_voo_holdings_fixture"): ComparisonSourceDocument {
  if (sourceDocumentId === "src_aapl_10k_fixture") {
    return {
      source_document_id: "src_aapl_10k_fixture",
      source_type: "sec_filing",
      title: "Apple Inc. Form 10-K fixture excerpt",
      publisher: "Apple",
      url: "https://www.sec.gov/",
      published_at: as_of_date,
      as_of_date,
      retrieved_at,
      freshness_state: "fresh",
      is_official: true,
      supporting_passage:
        "Apple designs, manufactures, and markets smartphones, personal computers, tablets, wearables, accessories, and related services.",
      source_quality: "official",
      allowlist_status: "allowed",
      source_use_policy: "full_text_allowed",
      permitted_operations: DEFAULT_ALLOWED_SOURCE_OPERATIONS
    };
  }

  if (sourceDocumentId === "src_voo_holdings_fixture") {
    return {
      source_document_id: "src_voo_holdings_fixture",
      source_type: "holdings_file",
      title: "Vanguard S&P 500 ETF holdings fixture excerpt",
      publisher: "Vanguard",
      url: "https://investor.vanguard.com/",
      published_at: as_of_date,
      as_of_date,
      retrieved_at,
      freshness_state: "fresh",
      is_official: true,
      supporting_passage:
        "The local holdings fixture records VOO as holding large U.S. companies across sectors; top holdings include Apple, Microsoft, Nvidia, Amazon.com, and Meta Platforms.",
      source_quality: "issuer",
      allowlist_status: "allowed",
      source_use_policy: "full_text_allowed",
      permitted_operations: DEFAULT_ALLOWED_SOURCE_OPERATIONS
    };
  }

  return sourceDocumentFor("VOO");
}

function fieldNameForDimension(dimension: ComparisonRequiredDimension): ComparisonFactKind {
  if (dimension === "Benchmark") {
    return "benchmark";
  }
  if (dimension === "Expense ratio") {
    return "expense_ratio";
  }
  if (dimension === "Educational role") {
    return "beginner_role";
  }
  return "holdings_count";
}

function claimIdForDimension(dimension: ComparisonRequiredDimension) {
  return `claim_comparison_${claimSlug(dimension)}`;
}

function claimSlug(dimension: string) {
  return dimension.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function comparisonId(leftTicker: string, rightTicker: string) {
  return `comparison-${leftTicker.toLowerCase()}-to-${rightTicker.toLowerCase()}-local-fixture-v1`;
}

function assetTickerForSourceDocumentId(sourceDocumentId: string): "VOO" | "QQQ" {
  return sourceDocumentId.includes("_qqq_") ? "QQQ" : "VOO";
}

function assetTickerForCitationId(citationId: string): "AAPL" | "VOO" | "QQQ" {
  if (citationId.includes("_aapl_")) {
    return "AAPL";
  }
  return citationId.includes("_qqq_") ? "QQQ" : "VOO";
}

function assetTickerForStockEtfCitationId(citationId: string): "AAPL" | "VOO" {
  return citationId.includes("_aapl_") ? "AAPL" : "VOO";
}

function assetTickerForStockEtfSourceDocumentId(sourceDocumentId: string): "AAPL" | "VOO" {
  return sourceDocumentId.includes("_aapl_") ? "AAPL" : "VOO";
}

function sourceDocumentIdForAssetTicker(assetTicker: "VOO" | "QQQ") {
  return supportedComparisonFacts[assetTicker].source_document_id;
}

function sourceDocumentIdForCitationId(citationId: string) {
  if (citationId === "c_compare_aapl_company_profile") {
    return "src_aapl_10k_fixture";
  }
  if (citationId === "c_compare_voo_aapl_top_holding") {
    return "src_voo_holdings_fixture";
  }
  if (citationId.startsWith("c_compare_voo_")) {
    return "src_voo_fact_sheet_fixture";
  }
  return sourceDocumentIdForAssetTicker(assetTickerForCitationId(citationId) as "VOO" | "QQQ");
}

function sideRoleForAsset(assetTicker: string, leftTicker: string, rightTicker: string): ComparisonEvidenceSideRole {
  if (assetTicker === leftTicker) {
    return "left_side_support";
  }
  if (assetTicker === rightTicker) {
    return "right_side_support";
  }
  return "shared_comparison_support";
}
