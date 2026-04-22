export type FreshnessState = "fresh" | "stale" | "unknown" | "unavailable";
export type AssetType = "stock" | "etf";
export type EvidenceState =
  | "supported"
  | "mixed"
  | "unknown"
  | "unavailable"
  | "stale"
  | "insufficient_evidence"
  | "no_major_recent_development";
export type StockSectionType =
  | "stable_facts"
  | "evidence_gap"
  | "risk"
  | "recent_developments"
  | "educational_suitability";

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
  asOfDate?: string;
  retrievedAt: string;
  freshnessState: FreshnessState;
  isOfficial: boolean;
  supportingPassage: string;
};

export type StockSectionItem = {
  itemId: string;
  title: string;
  summary: string;
  citationIds: string[];
  sourceDocumentIds: string[];
  freshnessState: FreshnessState;
  evidenceState: EvidenceState;
  eventDate?: string | null;
  asOfDate?: string | null;
  retrievedAt?: string | null;
  limitations?: string | null;
};

export type StockSectionMetric = {
  metricId: string;
  label: string;
  value: string;
  citationIds: string[];
  sourceDocumentIds: string[];
  freshnessState: FreshnessState;
  evidenceState: EvidenceState;
  asOfDate?: string | null;
  retrievedAt?: string | null;
  limitations?: string | null;
};

export type StockOverviewSection = {
  sectionId: string;
  title: string;
  sectionType: StockSectionType;
  beginnerSummary: string;
  items: StockSectionItem[];
  metrics?: StockSectionMetric[];
  citationIds: string[];
  sourceDocumentIds: string[];
  freshnessState: FreshnessState;
  evidenceState: EvidenceState;
  asOfDate?: string | null;
  retrievedAt?: string | null;
  limitations?: string | null;
};

export type CitationContext = {
  citationId: string;
  sourceDocumentId: string;
  sectionId: string;
  sectionTitle: string;
  claimContext: string;
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
  stockSections?: StockOverviewSection[];
  citationContexts?: CitationContext[];
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
        sourceDocumentId: "src_aapl_10k_fixture",
        title: "Apple Inc. Form 10-K",
        publisher: "U.S. SEC",
        freshnessState: "fresh"
      },
      {
        citationId: "c_chk_aapl_risks_001",
        sourceDocumentId: "src_aapl_10k_fixture",
        title: "Apple Inc. Form 10-K fixture excerpt",
        publisher: "U.S. SEC",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_aapl_asset_identity",
        sourceDocumentId: "src_aapl_10k_fixture",
        title: "Apple Inc. Form 10-K fixture excerpt",
        publisher: "U.S. SEC",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_aapl_business_quality_strength",
        sourceDocumentId: "src_aapl_10k_fixture",
        title: "Apple Inc. Form 10-K fixture excerpt",
        publisher: "U.S. SEC",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_aapl_primary_business",
        sourceDocumentId: "src_aapl_10k_fixture",
        title: "Apple Inc. Form 10-K fixture excerpt",
        publisher: "U.S. SEC",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_aapl_products_services_detail",
        sourceDocumentId: "src_aapl_10k_fixture",
        title: "Apple Inc. Form 10-K fixture excerpt",
        publisher: "U.S. SEC",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_aapl_revenue_trend",
        sourceDocumentId: "src_aapl_xbrl_fixture",
        title: "Apple Inc. SEC XBRL company facts fixture excerpt",
        publisher: "U.S. SEC",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_aapl_risk_context",
        sourceDocumentId: "src_aapl_10k_fixture",
        title: "Apple Inc. Form 10-K fixture excerpt",
        publisher: "U.S. SEC",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_aapl_valuation_limitation",
        sourceDocumentId: "src_aapl_valuation_limitation",
        title: "AAPL valuation data availability fixture note",
        publisher: "Learn the Ticker fixtures",
        freshnessState: "unavailable"
      },
      {
        citationId: "c_recent_aapl_none",
        sourceDocumentId: "src_aapl_recent_review",
        title: "Apple recent-development local fixture review",
        publisher: "Learn the Ticker fixtures",
        freshnessState: "fresh"
      }
    ],
    sourceDocuments: [
      {
        sourceDocumentId: "src_aapl_10k_fixture",
        sourceType: "sec_filing",
        title: "Apple Inc. Form 10-K fixture excerpt",
        publisher: "U.S. SEC",
        url: "https://www.sec.gov/",
        publishedAt: "2026-04-01",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "Stub passage: Apple designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and services."
      },
      {
        sourceDocumentId: "src_aapl_xbrl_fixture",
        sourceType: "structured_market_data",
        title: "Apple Inc. SEC XBRL company facts fixture excerpt",
        publisher: "U.S. SEC",
        url: "https://www.sec.gov/",
        publishedAt: "2026-04-01",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "The local SEC XBRL fixture records Apple net sales of $383.3 billion for fiscal 2023 and $391.0 billion for fiscal 2024."
      },
      {
        sourceDocumentId: "src_aapl_valuation_limitation",
        sourceType: "structured_market_data",
        title: "AAPL valuation data availability fixture note",
        publisher: "Learn the Ticker fixtures",
        url: "local://fixtures/aapl/valuation-data-limitation",
        publishedAt: "2026-04-20",
        asOfDate: "2026-04-20",
        retrievedAt: stubTimestamp,
        freshnessState: "unavailable",
        isOfficial: false,
        supportingPassage:
          "The local structured-data fixture does not include current P/E, forward P/E, price/sales, price/free-cash-flow, peer context, or own-history valuation metrics for AAPL."
      },
      {
        sourceDocumentId: "src_aapl_recent_review",
        sourceType: "recent_development",
        title: "Apple recent-development local fixture review",
        publisher: "Learn the Ticker fixtures",
        url: "local://fixtures/aapl/recent-review",
        publishedAt: "2026-04-20",
        asOfDate: "2026-04-20",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: false,
        supportingPassage:
          "The local fixture review found no high-signal recent development for Apple to include in this deterministic retrieval pack."
      }
    ],
    beginnerSummary: {
      whatItIs:
        "Apple Inc. is a U.S.-listed company; the local fixture describes its primary business as selling devices, software, accessories, and services.",
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
        title: "Company-specific risk",
        plainEnglishExplanation: "A single company can be affected by its own product demand, execution, and operating problems.",
        citationIds: ["c_chk_aapl_risks_001"]
      },
      {
        title: "Competition",
        plainEnglishExplanation:
          "Consumer technology markets can change quickly when competitors release new products or services.",
        citationIds: ["c_chk_aapl_risks_001"]
      },
      {
        title: "Supply chain and regulation",
        plainEnglishExplanation:
          "Global operations can be affected by manufacturing, legal, or regulatory issues.",
        citationIds: ["c_chk_aapl_risks_001"]
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
        citationIds: ["c_recent_aapl_none"],
        freshnessState: "fresh"
      }
    ],
    suitabilitySummary: {
      mayFit: "Educationally, it is useful for learning how a large single-company business model works.",
      mayNotFit: "It should not be confused with diversified fund exposure.",
      learnNext: "Compare company-specific risk with ETF diversification."
    },
    stockSections: [
      {
        sectionId: "business_overview",
        title: "Business Overview",
        sectionType: "stable_facts",
        beginnerSummary:
          "Apple Inc. is described in the local fixture as a company that sells devices, software, accessories, and services.",
        items: [
          {
            itemId: "primary_business",
            title: "Primary business",
            summary: "Sells devices, software, accessories, and services.",
            citationIds: ["c_fact_aapl_primary_business"],
            sourceDocumentIds: ["src_aapl_10k_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_fact_aapl_primary_business"],
        sourceDocumentIds: ["src_aapl_10k_fixture"],
        freshnessState: "fresh",
        evidenceState: "supported",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: null
      },
      {
        sectionId: "products_services",
        title: "Products Or Services",
        sectionType: "stable_facts",
        beginnerSummary:
          "The current fixture supports a high-level split between product and services activity, but not a full segment table.",
        items: [
          {
            itemId: "products_and_services",
            title: "Products and services",
            summary:
              "Product lines include iPhone, Mac, iPad, and wearables, home, and accessories; services include advertising, AppleCare, cloud services, digital content, and payment services.",
            citationIds: ["c_fact_aapl_products_services_detail"],
            sourceDocumentIds: ["src_aapl_10k_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "business_segments",
            title: "Business segments",
            summary:
              "The local fixture does not include source-backed segment, revenue-driver, geographic-exposure, or competitor detail.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unknown",
            evidenceState: "unknown",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations:
              "The local fixture does not include source-backed segment, revenue-driver, geographic-exposure, or competitor detail."
          }
        ],
        citationIds: ["c_fact_aapl_products_services_detail"],
        sourceDocumentIds: ["src_aapl_10k_fixture"],
        freshnessState: "unknown",
        evidenceState: "mixed",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: null
      },
      {
        sectionId: "strengths",
        title: "Strengths",
        sectionType: "stable_facts",
        beginnerSummary:
          "The fixture describes Apple's business as supported by an installed base of active devices and services activity connected to that device base.",
        items: [
          {
            itemId: "business_quality_strength",
            title: "Business-quality point",
            summary:
              "The fixture describes Apple's business as supported by an installed base of active devices and services activity connected to that device base.",
            citationIds: ["c_fact_aapl_business_quality_strength"],
            sourceDocumentIds: ["src_aapl_10k_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_fact_aapl_business_quality_strength"],
        sourceDocumentIds: ["src_aapl_10k_fixture"],
        freshnessState: "fresh",
        evidenceState: "supported",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: null
      },
      {
        sectionId: "financial_quality",
        title: "Financial Quality",
        sectionType: "stable_facts",
        beginnerSummary:
          "The fixture supports one multi-year net sales trend, while earnings, margins, cash flow, debt, cash, ROE, and ROIC remain unavailable.",
        items: [
          {
            itemId: "net_sales_trend",
            title: "Net sales trend",
            summary:
              "The local fixture records Apple net sales moving from $383.3 billion in fiscal 2023 to $391.0 billion in fiscal 2024.",
            citationIds: ["c_fact_aapl_revenue_trend"],
            sourceDocumentIds: ["src_aapl_xbrl_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "financial_quality_detail_gap",
            title: "Additional financial-quality metrics",
            summary: "The local fixture still lacks earnings, margin, cash-flow, debt, cash, ROE, and ROIC metrics.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unavailable",
            evidenceState: "unavailable",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations: "The local fixture still lacks earnings, margin, cash-flow, debt, cash, ROE, and ROIC metrics."
          }
        ],
        metrics: [
          {
            metricId: "net_sales_trend",
            label: "Net sales trend",
            value: "$383.3 billion in fiscal 2023 to $391.0 billion in fiscal 2024",
            citationIds: ["c_fact_aapl_revenue_trend"],
            sourceDocumentIds: ["src_aapl_xbrl_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_fact_aapl_revenue_trend"],
        sourceDocumentIds: ["src_aapl_xbrl_fixture"],
        freshnessState: "unavailable",
        evidenceState: "mixed",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: "The local fixture still lacks earnings, margin, cash-flow, debt, cash, ROE, and ROIC metrics."
      },
      {
        sectionId: "valuation_context",
        title: "Valuation Context",
        sectionType: "evidence_gap",
        beginnerSummary:
          "The local fixture does not include current P/E, forward P/E, price/sales, price/free-cash-flow, peer context, or own-history valuation metrics for AAPL.",
        items: [
          {
            itemId: "valuation_data_limitation",
            title: "Valuation data limitation",
            summary:
              "The local fixture does not include current P/E, forward P/E, price/sales, price/free-cash-flow, peer context, or own-history valuation metrics for AAPL.",
            citationIds: ["c_fact_aapl_valuation_limitation"],
            sourceDocumentIds: ["src_aapl_valuation_limitation"],
            freshnessState: "unavailable",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-20",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "valuation_metrics_gap",
            title: "Valuation metrics",
            summary:
              "No local fixture evidence is available for valuation context, so retrieval must not invent valuation facts.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unavailable",
            evidenceState: "unavailable",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations:
              "No local fixture evidence is available for valuation context, so retrieval must not invent valuation facts."
          }
        ],
        citationIds: ["c_fact_aapl_valuation_limitation"],
        sourceDocumentIds: ["src_aapl_valuation_limitation"],
        freshnessState: "unavailable",
        evidenceState: "mixed",
        asOfDate: "2026-04-20",
        retrievedAt: stubTimestamp,
        limitations: "No local fixture evidence is available for valuation context, so retrieval must not invent valuation facts."
      },
      {
        sectionId: "top_risks",
        title: "Top Risks",
        sectionType: "risk",
        beginnerSummary: "Exactly three top risks are shown first for beginner readability.",
        items: [
          {
            itemId: "risk_1",
            title: "Company-specific risk",
            summary: "A single company can be affected by its own product demand, execution, and operating problems.",
            citationIds: ["c_chk_aapl_risks_001"],
            sourceDocumentIds: ["src_aapl_10k_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "risk_2",
            title: "Competition",
            summary: "Consumer technology markets can change quickly when competitors release new products or services.",
            citationIds: ["c_chk_aapl_risks_001"],
            sourceDocumentIds: ["src_aapl_10k_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "risk_3",
            title: "Supply chain and regulation",
            summary: "Global operations can be affected by manufacturing, legal, or regulatory issues.",
            citationIds: ["c_chk_aapl_risks_001"],
            sourceDocumentIds: ["src_aapl_10k_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_chk_aapl_risks_001"],
        sourceDocumentIds: ["src_aapl_10k_fixture"],
        freshnessState: "fresh",
        evidenceState: "supported",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: null
      },
      {
        sectionId: "recent_developments",
        title: "Recent Developments",
        sectionType: "recent_developments",
        beginnerSummary: "Recent context is kept separate from stable asset basics.",
        items: [
          {
            itemId: "recent_1",
            title: "No high-signal recent development found in local fixture review",
            summary:
              "The deterministic fixture keeps recent context separate and explicitly records that no major recent item is available.",
            citationIds: ["c_recent_aapl_none"],
            sourceDocumentIds: ["src_aapl_recent_review"],
            freshnessState: "fresh",
            evidenceState: "no_major_recent_development",
            eventDate: null,
            asOfDate: "2026-04-20",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_recent_aapl_none"],
        sourceDocumentIds: ["src_aapl_recent_review"],
        freshnessState: "fresh",
        evidenceState: "no_major_recent_development",
        asOfDate: "2026-04-20",
        retrievedAt: stubTimestamp,
        limitations: null
      },
      {
        sectionId: "educational_suitability",
        title: "Educational Suitability",
        sectionType: "educational_suitability",
        beginnerSummary:
          "Educationally, this overview can help someone learn how a large single-company business model is described from filings.",
        items: [
          {
            itemId: "company_specific_risk_context",
            title: "Company-specific risk context",
            summary:
              "It should not be confused with diversified fund exposure because one company carries company-specific risk. Compare company-specific risk with ETF diversification and review which facts are unavailable in the local fixture.",
            citationIds: ["c_chk_aapl_risks_001"],
            sourceDocumentIds: ["src_aapl_10k_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_chk_aapl_risks_001"],
        sourceDocumentIds: ["src_aapl_10k_fixture"],
        freshnessState: "fresh",
        evidenceState: "supported",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: null
      }
    ],
    citationContexts: [
      {
        citationId: "c_fact_aapl_primary_business",
        sourceDocumentId: "src_aapl_10k_fixture",
        sectionId: "business_overview",
        sectionTitle: "Business Overview",
        claimContext: "Primary business: Sells devices, software, accessories, and services.",
        supportingPassage:
          "Apple designs, manufactures, and markets smartphones, personal computers, tablets, wearables, accessories, and related services."
      },
      {
        citationId: "c_fact_aapl_products_services_detail",
        sourceDocumentId: "src_aapl_10k_fixture",
        sectionId: "products_services",
        sectionTitle: "Products Or Services",
        claimContext:
          "Products and services: Product lines include iPhone, Mac, iPad, and wearables, home, and accessories; services include advertising, AppleCare, cloud services, digital content, and payment services.",
        supportingPassage:
          "Apple product lines in this fixture include iPhone, Mac, iPad, and wearables, home, and accessories; services include advertising, AppleCare, cloud services, digital content, and payment services."
      },
      {
        citationId: "c_fact_aapl_business_quality_strength",
        sourceDocumentId: "src_aapl_10k_fixture",
        sectionId: "strengths",
        sectionTitle: "Strengths",
        claimContext:
          "Business-quality point: the fixture describes Apple's business as supported by an installed base of active devices and services activity connected to that device base.",
        supportingPassage:
          "The local filing fixture describes Apple's business as supported by an installed base of active devices and services activity connected to that device base."
      },
      {
        citationId: "c_fact_aapl_revenue_trend",
        sourceDocumentId: "src_aapl_xbrl_fixture",
        sectionId: "financial_quality",
        sectionTitle: "Financial Quality",
        claimContext:
          "Net sales trend: Apple net sales moved from $383.3 billion in fiscal 2023 to $391.0 billion in fiscal 2024.",
        supportingPassage:
          "The local SEC XBRL fixture records Apple net sales of $383.3 billion for fiscal 2023 and $391.0 billion for fiscal 2024."
      },
      {
        citationId: "c_fact_aapl_valuation_limitation",
        sourceDocumentId: "src_aapl_valuation_limitation",
        sectionId: "valuation_context",
        sectionTitle: "Valuation Context",
        claimContext:
          "Valuation data limitation: the local fixture does not include current P/E, forward P/E, price/sales, price/free-cash-flow, peer context, or own-history valuation metrics for AAPL.",
        supportingPassage:
          "The local structured-data fixture does not include current P/E, forward P/E, price/sales, price/free-cash-flow, peer context, or own-history valuation metrics for AAPL."
      },
      {
        citationId: "c_chk_aapl_risks_001",
        sourceDocumentId: "src_aapl_10k_fixture",
        sectionId: "top_risks",
        sectionTitle: "Top Risks",
        claimContext:
          "Top risks: company-specific risk, competition, and supply chain or regulatory issues are the three risks shown first.",
        supportingPassage:
          "Single-company stock results can be affected by product demand, competition, supply chain disruption, regulation, and other company-specific risks."
      },
      {
        citationId: "c_recent_aapl_none",
        sourceDocumentId: "src_aapl_recent_review",
        sectionId: "recent_developments",
        sectionTitle: "Recent Developments",
        claimContext:
          "No high-signal recent development found in local fixture review; recent context remains separate from stable facts.",
        supportingPassage:
          "The local fixture review found no high-signal recent development for Apple to include in this deterministic retrieval pack."
      },
      {
        citationId: "c_chk_aapl_risks_001",
        sourceDocumentId: "src_aapl_10k_fixture",
        sectionId: "educational_suitability",
        sectionTitle: "Educational Suitability",
        claimContext:
          "Company-specific risk context: this stock should not be confused with diversified fund exposure.",
        supportingPassage:
          "Single-company stock results can be affected by product demand, competition, supply chain disruption, regulation, and other company-specific risks."
      }
    ]
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

export function getCitationById(asset: AssetFixture, citationId: string) {
  return asset.citations.find((citation) => citation.citationId === citationId);
}

export function getCitationContextsForSource(asset: AssetFixture, sourceDocumentId: string) {
  return (asset.citationContexts ?? []).filter((context) => context.sourceDocumentId === sourceDocumentId);
}

export function citationLabel(citationId: string) {
  return citationId.replace("c_", "");
}
