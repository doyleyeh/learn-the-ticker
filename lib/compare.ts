import {
  getAssetFixture,
  normalizeTicker,
  unsupportedAssets,
  type Citation,
  type FreshnessState
} from "./fixtures";

type CompareAssetType = "stock" | "etf" | "unsupported" | "unknown";
type CompareStateStatus = "supported" | "unsupported" | "unknown";
type ComparisonFactKind = "benchmark" | "expense_ratio" | "holdings_count" | "role";

export type CompareAssetIdentity = {
  ticker: string;
  name: string;
  assetType: CompareAssetType;
  exchange: string | null;
  issuer: string | null;
  status: CompareStateStatus;
  supported: boolean;
};

export type ComparisonSourceDocument = {
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
  supportingPassage: string;
};

export type ComparisonClaimContext = {
  citationId: string;
  section: "Key difference" | "Bottom line for beginners";
  label: string;
  claimText: string;
};

export type ComparePageFixture = {
  leftAsset: CompareAssetIdentity;
  rightAsset: CompareAssetIdentity;
  state: {
    status: CompareStateStatus;
    message: string;
  };
  comparisonType: string;
  keyDifferences: {
    dimension: string;
    plainEnglishSummary: string;
    citationIds: string[];
  }[];
  bottomLineForBeginners: {
    summary: string;
    citationIds: string[];
  } | null;
  citations: Citation[];
  sourceDocuments: ComparisonSourceDocument[];
};

const retrievedAt = "2026-04-20T00:00:00Z";
const asOfDate = "2026-04-01";

const comparisonCitationIds: Record<"VOO" | "QQQ", Record<ComparisonFactKind, string>> = {
  VOO: {
    benchmark: "c_fact_voo_benchmark",
    expense_ratio: "c_fact_voo_expense_ratio",
    holdings_count: "c_fact_voo_holdings_count",
    role: "c_fact_voo_role"
  },
  QQQ: {
    benchmark: "c_fact_qqq_benchmark",
    expense_ratio: "c_fact_qqq_expense_ratio",
    holdings_count: "c_fact_qqq_holdings_count",
    role: "c_fact_qqq_role"
  }
};

const supportedComparisonFacts: Record<
  "VOO" | "QQQ",
  {
    benchmark: string;
    expenseRatio: string;
    holdingsCount: string;
    holdingsCountNumber: number;
    role: string;
    rolePhrase: string;
    title: string;
    publisher: string;
    sourceDocumentId: string;
    url: string;
    supportingPassage: string;
  }
> = {
  VOO: {
    benchmark: "S&P 500 Index",
    expenseRatio: "0.03%",
    holdingsCount: "500 approximate companies",
    holdingsCountNumber: 500,
    role: "Broad U.S. large-company ETF",
    rolePhrase: "broad U.S. large-company ETF",
    title: "Vanguard S&P 500 ETF fact sheet fixture excerpt",
    publisher: "Vanguard",
    sourceDocumentId: "src_voo_fact_sheet_fixture",
    url: "https://investor.vanguard.com/",
    supportingPassage: "VOO seeks to track the performance of the S&P 500 Index, which represents large U.S. companies."
  },
  QQQ: {
    benchmark: "Nasdaq-100 Index",
    expenseRatio: "0.2%",
    holdingsCount: "100 approximate companies",
    holdingsCountNumber: 100,
    role: "Narrower growth-oriented ETF",
    rolePhrase: "narrower growth-oriented ETF",
    title: "Invesco QQQ Trust fact sheet fixture excerpt",
    publisher: "Invesco",
    sourceDocumentId: "src_qqq_fact_sheet_fixture",
    url: "https://www.invesco.com/",
    supportingPassage: "QQQ seeks investment results that generally correspond to the Nasdaq-100 Index."
  }
};

export function getComparePageFixture(leftTicker: string, rightTicker: string): ComparePageFixture {
  const left = normalizeTicker(leftTicker);
  const right = normalizeTicker(rightTicker);

  if ((left === "VOO" && right === "QQQ") || (left === "QQQ" && right === "VOO")) {
    return buildSupportedComparison(left, right);
  }

  const leftAsset = assetIdentityForTicker(left);
  const rightAsset = assetIdentityForTicker(right);

  return {
    leftAsset,
    rightAsset,
    state: unavailableStateFor(leftAsset, rightAsset),
    comparisonType: "unavailable",
    keyDifferences: [],
    bottomLineForBeginners: null,
    citations: [],
    sourceDocuments: []
  };
}

export function getComparisonCitationMetadata(comparison: ComparePageFixture) {
  const citationsById = new Map(comparison.citations.map((citation) => [citation.citationId, citation]));
  const contextsBySourceDocumentId = new Map<string, ComparisonClaimContext[]>();

  function addContext(citationId: string, context: Omit<ComparisonClaimContext, "citationId">) {
    const citation = citationsById.get(citationId);
    if (!citation) {
      return;
    }

    const contexts = contextsBySourceDocumentId.get(citation.sourceDocumentId) ?? [];
    contexts.push({ citationId, ...context });
    contextsBySourceDocumentId.set(citation.sourceDocumentId, contexts);
  }

  for (const difference of comparison.keyDifferences) {
    for (const citationId of difference.citationIds) {
      addContext(citationId, {
        section: "Key difference",
        label: difference.dimension,
        claimText: difference.plainEnglishSummary
      });
    }
  }

  if (comparison.bottomLineForBeginners) {
    for (const citationId of comparison.bottomLineForBeginners.citationIds) {
      addContext(citationId, {
        section: "Bottom line for beginners",
        label: "Educational context",
        claimText: comparison.bottomLineForBeginners.summary
      });
    }
  }

  return { citationsById, contextsBySourceDocumentId };
}

function buildSupportedComparison(left: "VOO" | "QQQ", right: "VOO" | "QQQ"): ComparePageFixture {
  const leftFacts = supportedComparisonFacts[left];
  const rightFacts = supportedComparisonFacts[right];
  const broader = leftFacts.holdingsCountNumber >= rightFacts.holdingsCountNumber ? left : right;
  const narrower = broader === left ? right : left;

  const keyDifferences = [
    {
      dimension: "Benchmark",
      plainEnglishSummary: `${left} tracks the ${leftFacts.benchmark}, while ${right} tracks the ${rightFacts.benchmark}.`,
      citationIds: [citationIdFor(left, "benchmark"), citationIdFor(right, "benchmark")]
    },
    {
      dimension: "Expense ratio",
      plainEnglishSummary: `The fixture records ${left}'s expense ratio as ${leftFacts.expenseRatio} and ${right}'s as ${rightFacts.expenseRatio}.`,
      citationIds: [citationIdFor(left, "expense_ratio"), citationIdFor(right, "expense_ratio")]
    },
    {
      dimension: "Holdings count",
      plainEnglishSummary: `The local facts list ${left} with about ${leftFacts.holdingsCount} and ${right} with about ${rightFacts.holdingsCount}.`,
      citationIds: [citationIdFor(left, "holdings_count"), citationIdFor(right, "holdings_count")]
    },
    {
      dimension: "Breadth",
      plainEnglishSummary: `Using holdings count as the local breadth signal, ${broader} is broader than ${narrower}; this is not a full overlap calculation.`,
      citationIds: [citationIdFor(left, "holdings_count"), citationIdFor(right, "holdings_count")]
    },
    {
      dimension: "Educational role",
      plainEnglishSummary: `The local education facts frame ${left} as ${leftFacts.rolePhrase} and ${right} as ${rightFacts.rolePhrase}.`,
      citationIds: [citationIdFor(left, "role"), citationIdFor(right, "role")]
    }
  ];

  return {
    leftAsset: assetIdentityForTicker(left),
    rightAsset: assetIdentityForTicker(right),
    state: {
      status: "supported",
      message: "Comparison is supported by deterministic local retrieval fixtures."
    },
    comparisonType: "etf_vs_etf",
    keyDifferences,
    bottomLineForBeginners: {
      summary: `For beginner learning, ${left} is framed as ${leftFacts.rolePhrase}, while ${right} is framed as ${rightFacts.rolePhrase}. Compare their benchmark, cost, and holdings breadth as source-backed structure facts, not as a personal decision rule.`,
      citationIds: [
        citationIdFor(left, "role"),
        citationIdFor(right, "role"),
        citationIdFor(left, "holdings_count"),
        citationIdFor(right, "holdings_count"),
        citationIdFor(left, "expense_ratio"),
        citationIdFor(right, "expense_ratio")
      ]
    },
    citations: [
      citationFor("QQQ", "benchmark"),
      citationFor("QQQ", "expense_ratio"),
      citationFor("QQQ", "holdings_count"),
      citationFor("QQQ", "role"),
      citationFor("VOO", "benchmark"),
      citationFor("VOO", "expense_ratio"),
      citationFor("VOO", "holdings_count"),
      citationFor("VOO", "role")
    ],
    sourceDocuments: [sourceDocumentFor("QQQ"), sourceDocumentFor("VOO")]
  };
}

function assetIdentityForTicker(ticker: string): CompareAssetIdentity {
  const asset = getAssetFixture(ticker);
  if (asset) {
    return {
      ticker: asset.ticker,
      name: asset.name,
      assetType: asset.assetType,
      exchange: asset.exchange,
      issuer: asset.issuer ?? null,
      status: "supported",
      supported: true
    };
  }

  return {
    ticker,
    name: ticker,
    assetType: unsupportedAssets[ticker] ? "unsupported" : "unknown",
    exchange: null,
    issuer: null,
    status: unsupportedAssets[ticker] ? "unsupported" : "unknown",
    supported: false
  };
}

function unavailableStateFor(left: CompareAssetIdentity, right: CompareAssetIdentity) {
  const unsupportedMessage = unsupportedAssets[left.ticker] ?? unsupportedAssets[right.ticker];

  if (unsupportedMessage) {
    return {
      status: "unsupported" as const,
      message: unsupportedMessage
    };
  }

  if (!left.supported || !right.supported) {
    return {
      status: "unknown" as const,
      message: "Unknown ticker in local fixtures. No source-backed comparison evidence is available."
    };
  }

  return {
    status: "unknown" as const,
    message: "No deterministic local comparison knowledge pack is available for these tickers."
  };
}

function citationFor(ticker: "VOO" | "QQQ", fact: ComparisonFactKind): Citation {
  const source = supportedComparisonFacts[ticker];

  return {
    citationId: citationIdFor(ticker, fact),
    sourceDocumentId: source.sourceDocumentId,
    title: source.title,
    publisher: source.publisher,
    freshnessState: "fresh"
  };
}

function citationIdFor(ticker: "VOO" | "QQQ", fact: ComparisonFactKind) {
  return comparisonCitationIds[ticker][fact];
}

function sourceDocumentFor(ticker: "VOO" | "QQQ"): ComparisonSourceDocument {
  const source = supportedComparisonFacts[ticker];

  return {
    sourceDocumentId: source.sourceDocumentId,
    sourceType: "issuer_fact_sheet",
    title: source.title,
    publisher: source.publisher,
    url: source.url,
    publishedAt: asOfDate,
    asOfDate,
    retrievedAt,
    freshnessState: "fresh",
    isOfficial: true,
    supportingPassage: source.supportingPassage
  };
}
