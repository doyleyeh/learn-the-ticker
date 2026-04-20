export type FreshnessState = "fresh" | "stale" | "unknown" | "unavailable";
export type AssetType = "stock" | "etf";

export type Citation = {
  citationId: string;
  sourceDocumentId: string;
  title: string;
  publisher: string;
  freshnessState: FreshnessState;
};

export type SourceDocument = {
  sourceDocumentId: string;
  sourceType: string;
  title: string;
  publisher: string;
  url: string;
  publishedAt: string;
  retrievedAt: string;
  freshnessState: FreshnessState;
  isOfficial: boolean;
  supportingPassage: string;
};

export type AssetFixture = {
  ticker: string;
  name: string;
  assetType: AssetType;
  exchange: string;
  issuer?: string;
  freshness: {
    pageLastUpdatedAt: string;
    factsAsOf: string;
    holdingsAsOf?: string;
    recentEventsAsOf: string;
  };
  citations: Citation[];
  sourceDocuments: SourceDocument[];
  beginnerSummary: {
    whatItIs: string;
    whyPeopleConsiderIt: string;
    mainCatch: string;
  };
  claims: {
    claimId: string;
    claimText: string;
    citationIds: string[];
  }[];
  topRisks: {
    title: string;
    plainEnglishExplanation: string;
    citationIds: string[];
  }[];
  facts: {
    label: string;
    value: string;
    citationId?: string;
  }[];
  recentDevelopments: {
    title: string;
    summary: string;
    eventDate: string | null;
    citationIds: string[];
    freshnessState: FreshnessState;
  }[];
  suitabilitySummary: {
    mayFit: string;
    mayNotFit: string;
    learnNext: string;
  };
};

const stubTimestamp = "2026-04-20T00:00:00Z";

export const assetFixtures: Record<string, AssetFixture> = {
  VOO: {
    ticker: "VOO",
    name: "Vanguard S&P 500 ETF",
    assetType: "etf",
    exchange: "NYSE Arca",
    issuer: "Vanguard",
    freshness: {
      pageLastUpdatedAt: stubTimestamp,
      factsAsOf: "2026-04-01",
      holdingsAsOf: "2026-04-01",
      recentEventsAsOf: "2026-04-20"
    },
    citations: [
      {
        citationId: "c_voo_profile",
        sourceDocumentId: "src_voo_fact_sheet",
        title: "Vanguard S&P 500 ETF fact sheet",
        publisher: "Vanguard",
        freshnessState: "fresh"
      }
    ],
    sourceDocuments: [
      {
        sourceDocumentId: "src_voo_fact_sheet",
        sourceType: "issuer_fact_sheet",
        title: "Vanguard S&P 500 ETF fact sheet",
        publisher: "Vanguard",
        url: "https://investor.vanguard.com/",
        publishedAt: "2026-04-01",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "Stub passage: VOO seeks to track the S&P 500 Index and publishes fund costs, holdings, and risk information."
      }
    ],
    beginnerSummary: {
      whatItIs: "VOO is a plain-vanilla ETF designed to follow the S&P 500 Index, a basket of large U.S. companies.",
      whyPeopleConsiderIt:
        "Beginners often study it because it offers broad large-company exposure in one fund with a simple index-tracking approach.",
      mainCatch: "It is still stock-market exposure, so it can fall with the market and is not a complete plan by itself."
    },
    claims: [
      {
        claimId: "claim_voo_tracks_index",
        claimText: "VOO is designed to follow the S&P 500 Index.",
        citationIds: ["c_voo_profile"]
      }
    ],
    topRisks: [
      {
        title: "Market risk",
        plainEnglishExplanation: "The fund can lose value when large U.S. stocks fall.",
        citationIds: ["c_voo_profile"]
      },
      {
        title: "Large-company focus",
        plainEnglishExplanation: "The fund does not cover every public company or every asset class.",
        citationIds: ["c_voo_profile"]
      },
      {
        title: "Index tracking limits",
        plainEnglishExplanation: "The fund aims to follow an index rather than avoid weaker areas of the market.",
        citationIds: ["c_voo_profile"]
      }
    ],
    facts: [
      { label: "Issuer", value: "Vanguard", citationId: "c_voo_profile" },
      { label: "Benchmark", value: "S&P 500 Index", citationId: "c_voo_profile" },
      { label: "Expense ratio", value: "0.03%", citationId: "c_voo_profile" },
      { label: "Holdings count", value: "About 500 companies", citationId: "c_voo_profile" },
      { label: "Role", value: "Broad U.S. large-company ETF", citationId: "c_voo_profile" }
    ],
    recentDevelopments: [
      {
        title: "No high-signal recent development in stub data",
        summary:
          "This skeleton keeps recent context separate and reports that no major recent item is available in the local fixture.",
        eventDate: null,
        citationIds: ["c_voo_profile"],
        freshnessState: "fresh"
      }
    ],
    suitabilitySummary: {
      mayFit: "Educationally, it is useful for learning how broad U.S. large-company index ETFs work.",
      mayNotFit: "It may be less useful for learning about bonds, international stocks, or narrow sector exposure.",
      learnNext: "Compare it with a total-market ETF and a more concentrated growth ETF to understand diversification."
    }
  },
  QQQ: {
    ticker: "QQQ",
    name: "Invesco QQQ Trust",
    assetType: "etf",
    exchange: "NASDAQ",
    issuer: "Invesco",
    freshness: {
      pageLastUpdatedAt: stubTimestamp,
      factsAsOf: "2026-04-01",
      holdingsAsOf: "2026-04-01",
      recentEventsAsOf: "2026-04-20"
    },
    citations: [
      {
        citationId: "c_qqq_profile",
        sourceDocumentId: "src_qqq_fact_sheet",
        title: "Invesco QQQ Trust fact sheet",
        publisher: "Invesco",
        freshnessState: "fresh"
      }
    ],
    sourceDocuments: [
      {
        sourceDocumentId: "src_qqq_fact_sheet",
        sourceType: "issuer_fact_sheet",
        title: "Invesco QQQ Trust fact sheet",
        publisher: "Invesco",
        url: "https://www.invesco.com/",
        publishedAt: "2026-04-01",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "Stub passage: QQQ tracks the Nasdaq-100 Index and is more concentrated in large growth-oriented companies."
      }
    ],
    beginnerSummary: {
      whatItIs: "QQQ is an ETF designed to follow the Nasdaq-100 Index.",
      whyPeopleConsiderIt:
        "Beginners often study it to understand concentrated exposure to large non-financial Nasdaq-listed companies.",
      mainCatch:
        "It is narrower than a broad-market fund, so a few large companies and sectors can drive more of the result."
    },
    claims: [
      {
        claimId: "claim_qqq_tracks_index",
        claimText: "QQQ is designed to follow the Nasdaq-100 Index.",
        citationIds: ["c_qqq_profile"]
      }
    ],
    topRisks: [
      {
        title: "Concentration risk",
        plainEnglishExplanation: "A smaller group of large holdings can have an outsized impact on results.",
        citationIds: ["c_qqq_profile"]
      },
      {
        title: "Sector tilt",
        plainEnglishExplanation:
          "The fund can lean heavily toward growth-oriented technology and communication companies.",
        citationIds: ["c_qqq_profile"]
      },
      {
        title: "Market risk",
        plainEnglishExplanation: "The fund can fall when the stocks in its index decline.",
        citationIds: ["c_qqq_profile"]
      }
    ],
    facts: [
      { label: "Issuer", value: "Invesco", citationId: "c_qqq_profile" },
      { label: "Benchmark", value: "Nasdaq-100 Index", citationId: "c_qqq_profile" },
      { label: "Expense ratio", value: "0.20%", citationId: "c_qqq_profile" },
      { label: "Holdings count", value: "About 100 companies", citationId: "c_qqq_profile" },
      { label: "Role", value: "Narrower growth-oriented ETF", citationId: "c_qqq_profile" }
    ],
    recentDevelopments: [
      {
        title: "No high-signal recent development in stub data",
        summary:
          "This skeleton keeps recent context separate and reports that no major recent item is available in the local fixture.",
        eventDate: null,
        citationIds: ["c_qqq_profile"],
        freshnessState: "fresh"
      }
    ],
    suitabilitySummary: {
      mayFit:
        "Educationally, it is useful for learning how narrower growth-oriented ETF exposure differs from broad-market exposure.",
      mayNotFit: "It may be less useful as an example of a diversified total-market fund.",
      learnNext: "Compare its index, holdings count, and top-holding concentration with VOO."
    }
  },
  AAPL: {
    ticker: "AAPL",
    name: "Apple Inc.",
    assetType: "stock",
    exchange: "NASDAQ",
    freshness: {
      pageLastUpdatedAt: stubTimestamp,
      factsAsOf: "2026-04-01",
      recentEventsAsOf: "2026-04-20"
    },
    citations: [
      {
        citationId: "c_aapl_profile",
        sourceDocumentId: "src_aapl_10k",
        title: "Apple Inc. Form 10-K",
        publisher: "U.S. SEC",
        freshnessState: "fresh"
      }
    ],
    sourceDocuments: [
      {
        sourceDocumentId: "src_aapl_10k",
        sourceType: "sec_filing",
        title: "Apple Inc. Form 10-K",
        publisher: "U.S. SEC",
        url: "https://www.sec.gov/",
        publishedAt: "2026-04-01",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "Stub passage: Apple designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and services."
      }
    ],
    beginnerSummary: {
      whatItIs: "Apple is a U.S.-listed company that sells devices, software, and services.",
      whyPeopleConsiderIt:
        "Beginners often study it because its products are familiar and its filings explain a large global consumer technology business.",
      mainCatch: "A single company is less diversified than an ETF, so company-specific problems matter more."
    },
    claims: [
      {
        claimId: "claim_aapl_business",
        claimText: "Apple sells devices, software, and services.",
        citationIds: ["c_aapl_profile"]
      }
    ],
    topRisks: [
      {
        title: "Product concentration",
        plainEnglishExplanation: "A large business line can matter a lot to overall results.",
        citationIds: ["c_aapl_profile"]
      },
      {
        title: "Competition",
        plainEnglishExplanation:
          "Consumer technology markets can change quickly as competitors release new products.",
        citationIds: ["c_aapl_profile"]
      },
      {
        title: "Supply chain and regulation",
        plainEnglishExplanation:
          "Global operations can be affected by manufacturing, legal, or regulatory issues.",
        citationIds: ["c_aapl_profile"]
      }
    ],
    facts: [
      { label: "Sector", value: "Technology", citationId: "c_aapl_profile" },
      { label: "Industry", value: "Consumer electronics", citationId: "c_aapl_profile" },
      { label: "Business model", value: "Sells devices, software, and services", citationId: "c_aapl_profile" },
      { label: "Diversification context", value: "Single-company stock, not a fund", citationId: "c_aapl_profile" }
    ],
    recentDevelopments: [
      {
        title: "No high-signal recent development in stub data",
        summary:
          "This skeleton keeps recent context separate and reports that no major recent item is available in the local fixture.",
        eventDate: null,
        citationIds: ["c_aapl_profile"],
        freshnessState: "fresh"
      }
    ],
    suitabilitySummary: {
      mayFit: "Educationally, it is useful for learning how a large single-company business model works.",
      mayNotFit: "It should not be confused with diversified fund exposure.",
      learnNext: "Compare company-specific risk with ETF diversification."
    }
  }
};

export const unsupportedAssets: Record<string, string> = {
  BTC: "Crypto assets are outside the current U.S. stock and plain-vanilla ETF scope.",
  ETH: "Crypto assets are outside the current U.S. stock and plain-vanilla ETF scope.",
  TQQQ: "Leveraged ETFs are outside the current plain-vanilla ETF scope.",
  SQQQ: "Inverse ETFs are outside the current plain-vanilla ETF scope."
};

export const compareFixture = {
  leftTicker: "VOO",
  rightTicker: "QQQ",
  keyDifferences: [
    {
      dimension: "Exposure",
      plainEnglishSummary:
        "VOO is built around broad U.S. large-company exposure, while QQQ is narrower and more concentrated in Nasdaq-100 companies.",
      citationIds: ["c_voo_profile", "c_qqq_profile"]
    },
    {
      dimension: "Diversification",
      plainEnglishSummary:
        "The local fixture describes VOO as holding about five times as many companies as QQQ.",
      citationIds: ["c_voo_profile", "c_qqq_profile"]
    },
    {
      dimension: "Cost context",
      plainEnglishSummary:
        "The fixtures show a lower stated expense ratio for VOO than QQQ, but costs are only one comparison dimension.",
      citationIds: ["c_voo_profile", "c_qqq_profile"]
    }
  ],
  bottomLineForBeginners: {
    summary:
      "For learning purposes, this comparison highlights broad index exposure versus narrower growth-oriented ETF exposure.",
    citationIds: ["c_voo_profile", "c_qqq_profile"]
  }
};

export function normalizeTicker(ticker: string) {
  return ticker.trim().toUpperCase();
}

export function getAssetFixture(ticker: string) {
  return assetFixtures[normalizeTicker(ticker)];
}

export function getPrimarySource(asset: AssetFixture) {
  return asset.sourceDocuments[0];
}

export function citationLabel(citationId: string) {
  return citationId.replace("c_", "");
}
