import type { RuntimeSectionState } from "./runtimeSectionStates";

export type { RuntimeSectionState } from "./runtimeSectionStates";

export type FreshnessState =
  | "fresh"
  | "stale"
  | "unknown"
  | "unavailable"
  | "partial"
  | "insufficient_evidence";
export type AssetType = "stock" | "etf";
export type EvidenceState =
  | "supported"
  | "partial"
  | "mixed"
  | "unknown"
  | "unavailable"
  | "stale"
  | "insufficient_evidence"
  | "no_high_signal"
  | "no_major_recent_development"
  | "unsupported";
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
  sourceQuality?: SourceQuality;
  source_quality?: SourceQuality;
  allowlistStatus?: SourceAllowlistStatus;
  allowlist_status?: SourceAllowlistStatus;
  sourceUsePolicy?: SourceUsePolicy;
  source_use_policy?: SourceUsePolicy;
  permitted_operations?: {
    can_export_full_text?: boolean;
  };
};

export type SourceQuality =
  | "official"
  | "issuer"
  | "provider"
  | "fixture"
  | "allowlisted"
  | "rejected"
  | "unknown";

export type SourceAllowlistStatus = "allowed" | "rejected" | "pending_review" | "not_allowlisted";

export type SourceUsePolicy =
  | "metadata_only"
  | "link_only"
  | "summary_allowed"
  | "full_text_allowed"
  | "rejected";

export type SourceDrawerSourceDocument = SourceDocument & {
  source_document_id: string;
  source_type: string;
  published_at: string | null;
  as_of_date: string | null;
  retrieved_at: string;
  freshness_state: FreshnessState;
  source_quality: SourceQuality;
  allowlist_status: SourceAllowlistStatus;
  source_use_policy: SourceUsePolicy;
  sourceQuality: SourceQuality;
  allowlistStatus: SourceAllowlistStatus;
  sourceUsePolicy: SourceUsePolicy;
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
  value: string | number | null;
  unit?: string | null;
  citationIds: string[];
  sourceDocumentIds: string[];
  freshnessState: FreshnessState;
  evidenceState: EvidenceState;
  asOfDate?: string | null;
  retrievedAt?: string | null;
  limitations?: string | null;
};

export type OverviewTableColumn = {
  columnId: string;
  label: string;
  valueType: "text" | "number" | "percent" | "currency";
  align: "left" | "right" | "center";
};

export type OverviewTableRow = {
  rowId: string;
  label?: string | null;
  values: Record<string, string | number | null>;
  citationIds: string[];
  sourceDocumentIds: string[];
  freshnessState: FreshnessState;
  evidenceState: EvidenceState;
  asOfDate?: string | null;
  retrievedAt?: string | null;
  limitations?: string | null;
};

export type OverviewTable = {
  tableId: string;
  title: string;
  columns: OverviewTableColumn[];
  rows: OverviewTableRow[];
  citationIds: string[];
  sourceDocumentIds: string[];
  freshnessState: FreshnessState;
  evidenceState: EvidenceState;
  asOfDate?: string | null;
  retrievedAt?: string | null;
  limitations?: string | null;
};

export type OverviewChartPoint = {
  timestamp: string;
  close: number;
  volume?: number | null;
};

export type OverviewChart = {
  chartId: string;
  title: string;
  range: string;
  interval: string;
  points: OverviewChartPoint[];
  currency?: string | null;
  citationIds: string[];
  sourceDocumentIds: string[];
  freshnessState: FreshnessState;
  evidenceState: EvidenceState;
  asOfDate?: string | null;
  retrievedAt?: string | null;
  delayedOrBestEffortLabel?: string | null;
  limitations?: string | null;
};

export type StockOverviewSection = {
  sectionId: string;
  title: string;
  sectionType: StockSectionType;
  beginnerSummary: string;
  items: StockSectionItem[];
  metrics?: StockSectionMetric[];
  table?: OverviewTable | null;
  chart?: OverviewChart | null;
  citationIds: string[];
  sourceDocumentIds: string[];
  freshnessState: FreshnessState;
  evidenceState: EvidenceState;
  asOfDate?: string | null;
  retrievedAt?: string | null;
  limitations?: string | null;
};

export type EtfSectionType = StockSectionType;
export type EtfSectionItem = StockSectionItem;
export type EtfSectionMetric = StockSectionMetric;
export type EtfOverviewSection = StockOverviewSection;

export type CitationContext = {
  citationId: string;
  sourceDocumentId: string;
  sectionId: string;
  sectionTitle: string;
  claimContext: string;
  supportingPassage: string;
};

export type WeeklyNewsContractState =
  | "available"
  | "no_high_signal"
  | "insufficient_evidence"
  | "unavailable"
  | "suppressed";

export type WeeklyNewsEvidenceLimitedState =
  | "full"
  | "limited_verified_set"
  | "empty"
  | "unavailable"
  | "insufficient_evidence";

export type WeeklyNewsWindow = {
  asOfDate: string;
  timezone: "America/New_York";
  previousMarketWeek: {
    start: string | null;
    end: string | null;
  };
  currentWeekToDate: {
    start: string | null;
    end: string | null;
  };
  newsWindowStart: string;
  newsWindowEnd: string;
  includesCurrentWeekToDate: boolean;
};

export type WeeklyNewsSourceMetadata = {
  sourceDocumentId: string;
  sourceType: string;
  title: string;
  publisher: string;
  url: string;
  publishedAt?: string | null;
  asOfDate?: string | null;
  retrievedAt: string;
  freshnessState: FreshnessState;
  isOfficial: boolean;
  sourceQuality: "official" | "issuer" | "provider" | "fixture" | "allowlisted" | "rejected" | "unknown";
  allowlistStatus: "allowed" | "rejected" | "pending_review" | "not_allowlisted";
  sourceUsePolicy: "metadata_only" | "link_only" | "summary_allowed" | "full_text_allowed" | "rejected";
};

export type AnalysisPackRuntimeMetadata = {
  analysisSource: "imported_local_pack" | "backend_generated" | "deterministic_fixture";
  freshnessExpiresAt?: string | null;
  importBundleId?: string | null;
  validationStatus: "passed" | "failed" | "not_applicable";
};

export type GenerationDiagnostics = {
  attemptedLive: boolean;
  usedFallback: boolean;
  fallbackReasonCodes: string[];
  modelName?: string | null;
};

export type EconomicIndicatorItem = {
  indicatorId: string;
  name: string;
  category: "official_historical_actual" | "market_reference";
  value: string;
  numericValue?: number | null;
  unit?: string | null;
  period: string;
  asOfDate: string;
  publishedAt?: string | null;
  retrievedAt: string;
  source: WeeklyNewsSourceMetadata;
  freshnessState: FreshnessState;
  trendDirection: "up" | "down" | "neutral" | "unknown";
  citationIds: string[];
  sourceDocumentIds: string[];
  evidenceState: EvidenceState;
};

export type EconomicIndicatorsPackFixture = {
  schemaVersion: "economic-indicators-pack-v1";
  state: WeeklyNewsContractState;
  region: "US";
  asOfDate: string;
  items: EconomicIndicatorItem[];
  citations: Citation[];
  sourceDocuments: SourceDocument[];
  analysisPackMetadata?: AnalysisPackRuntimeMetadata | null;
  sectionStates?: RuntimeSectionState[];
  noLiveExternalCalls: boolean;
  stableFactsAreSeparate: true;
};

export type WeeklyNewsItem = {
  eventId: string;
  assetTicker: string;
  eventType:
    | "earnings"
    | "guidance"
    | "product_announcement"
    | "merger_acquisition"
    | "leadership_change"
    | "regulatory_event"
    | "legal_event"
    | "capital_allocation"
    | "fee_change"
    | "methodology_change"
    | "index_change"
    | "fund_merger"
    | "fund_liquidation"
    | "sponsor_update"
    | "large_flow_event"
    | "no_major_recent_development"
    | "other";
  title: string;
  summary: string;
  eventDate?: string | null;
  publishedAt?: string | null;
  periodBucket: "previous_market_week" | "current_week_to_date";
  citationIds: string[];
  source: WeeklyNewsSourceMetadata;
  freshnessState: FreshnessState;
  importanceScore: number;
};

export type WeeklyNewsEmptyState = {
  state: WeeklyNewsContractState;
  message: string;
  evidenceState: EvidenceState;
  selectedItemCount: number;
  suppressedCandidateCount: number;
};

export type WeeklyNewsFocusFixture = {
  schemaVersion: "weekly-news-focus-v1";
  state: WeeklyNewsContractState;
  window: WeeklyNewsWindow;
  configuredMaxItemCount: number;
  selectedItemCount: number;
  suppressedCandidateCount: number;
  evidenceState: EvidenceState;
  evidenceLimitedState: WeeklyNewsEvidenceLimitedState;
  items: WeeklyNewsItem[];
  emptyState: WeeklyNewsEmptyState | null;
  citations: Citation[];
  sourceDocuments: SourceDocument[];
  sectionStates?: RuntimeSectionState[];
  noLiveExternalCalls: boolean;
  stableFactsAreSeparate: true;
};

export type AIComprehensiveAnalysisSection = {
  sectionId: "what_changed_this_week" | "market_context" | "business_or_fund_context" | "risk_context";
  label: "What Changed This Week" | "Market Context" | "Business/Fund Context" | "Risk Context";
  analysis: string;
  bullets: string[];
  citationIds: string[];
  uncertainty: string[];
};

export type AIComprehensiveAnalysisFixture = {
  schemaVersion: "ai-comprehensive-analysis-v1";
  state: WeeklyNewsContractState;
  analysisAvailable: boolean;
  minimumWeeklyNewsItemCount: number;
  weeklyNewsSelectedItemCount: number;
  suppressionReason: string | null;
  validationReasonCodes: string[];
  sections: AIComprehensiveAnalysisSection[];
  citationIds: string[];
  sourceDocumentIds: string[];
  weeklyNewsEventIds: string[];
  canonicalFactCitationIds: string[];
  citations: Citation[];
  sourceDocuments: SourceDocument[];
  sectionStates?: RuntimeSectionState[];
  generationDiagnostics?: GenerationDiagnostics | null;
  noLiveExternalCalls: boolean;
  stableFactsAreSeparate: true;
};

export type MarketNewsTopicBucket =
  | "macro_fed"
  | "markets_earnings"
  | "ai_technology_semiconductors"
  | "geopolitics_energy_supply_chain"
  | "credit_liquidity_sentiment";

export type MarketNewsItem = {
  storyId: string;
  title: string;
  summary: string;
  publishedAt: string;
  topicBucket: MarketNewsTopicBucket;
  entities: string[];
  citationIds: string[];
  source: WeeklyNewsSourceMetadata;
  freshnessState: FreshnessState;
  importanceScore: number;
  cluster: {
    clusterId: string;
    representativeArticleId: string;
    supportingSources: string[];
    articleCount: number;
    suppressedDuplicateCount: number;
    topicBucket: MarketNewsTopicBucket;
    criticalClaim: boolean;
    corroborated: boolean;
  };
};

export type MarketNewsFocusFixture = {
  schemaVersion: "market-news-focus-v1";
  state: WeeklyNewsContractState;
  window: WeeklyNewsWindow;
  configuredMaxItemCount: number;
  selectedItemCount: number;
  suppressedCandidateCount: number;
  evidenceState: EvidenceState;
  evidenceLimitedState: WeeklyNewsEvidenceLimitedState;
  items: MarketNewsItem[];
  emptyState: WeeklyNewsEmptyState | null;
  citations: Citation[];
  sourceDocuments: SourceDocument[];
  sectionStates?: RuntimeSectionState[];
  noLiveExternalCalls: boolean;
  stableFactsAreSeparate: true;
  reusableAcrossTickers: true;
};

export type MarketAIComprehensiveAnalysisSection = {
  sectionId:
    | "what_changed_this_week"
    | "macro_policy"
    | "equity_market_drivers"
    | "ai_technology_semiconductors"
    | "geopolitical_energy_risks"
    | "credit_liquidity_sentiment"
    | "scenario_lens"
    | "practical_watchpoints";
  label:
    | "What Changed This Week"
    | "Macro & Policy"
    | "Equity Market Drivers"
    | "AI / Technology / Semiconductors"
    | "Geopolitical & Energy Risks"
    | "Credit / Liquidity / Sentiment"
    | "Scenario Lens"
    | "Practical Watchpoints";
  analysis: string;
  bullets: string[];
  citationIds: string[];
  uncertainty: string[];
};

export type MarketAIComprehensiveAnalysisFixture = {
  schemaVersion: "market-ai-comprehensive-analysis-v1";
  state: WeeklyNewsContractState;
  analysisAvailable: boolean;
  minimumMarketNewsItemCount: number;
  minimumTopicBucketCount: number;
  marketNewsSelectedItemCount: number;
  selectedTopicBucketCount: number;
  suppressionReason: string | null;
  sections: MarketAIComprehensiveAnalysisSection[];
  citationIds: string[];
  sourceDocumentIds: string[];
  marketNewsStoryIds: string[];
  citations: Citation[];
  sourceDocuments: SourceDocument[];
  sectionStates?: RuntimeSectionState[];
  generationDiagnostics?: GenerationDiagnostics | null;
  noLiveExternalCalls: boolean;
  stableFactsAreSeparate: true;
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
  etfSections?: EtfOverviewSection[];
  citationContexts?: CitationContext[];
  sectionStates?: RuntimeSectionState[];
  generationDiagnostics?: Record<string, GenerationDiagnostics>;
};

const stubTimestamp = "2026-04-20T00:00:00Z";
const weeklyNewsWindow: WeeklyNewsWindow = {
  asOfDate: "2026-04-23",
  timezone: "America/New_York",
  previousMarketWeek: {
    start: "2026-04-13",
    end: "2026-04-19"
  },
  currentWeekToDate: {
    start: "2026-04-20",
    end: "2026-04-22"
  },
  newsWindowStart: "2026-04-13",
  newsWindowEnd: "2026-04-22",
  includesCurrentWeekToDate: true
};

function buildEmptyWeeklyNewsFocus(): WeeklyNewsFocusFixture {
  return {
    schemaVersion: "weekly-news-focus-v1",
    state: "no_high_signal",
    window: weeklyNewsWindow,
    configuredMaxItemCount: 8,
    selectedItemCount: 0,
    suppressedCandidateCount: 0,
    evidenceState: "no_high_signal",
    evidenceLimitedState: "empty",
    items: [],
    emptyState: {
      state: "no_high_signal",
      message: "No major Weekly News Focus items found in the deterministic local fixture window.",
      evidenceState: "no_high_signal",
      selectedItemCount: 0,
      suppressedCandidateCount: 0
    },
    citations: [],
    sourceDocuments: [],
    noLiveExternalCalls: true,
    stableFactsAreSeparate: true
  };
}

function buildSuppressedAIComprehensiveAnalysis(
  canonicalFactCitationIds: string[]
): AIComprehensiveAnalysisFixture {
  return {
    schemaVersion: "ai-comprehensive-analysis-v1",
    state: "suppressed",
    analysisAvailable: false,
    minimumWeeklyNewsItemCount: 2,
    weeklyNewsSelectedItemCount: 0,
    suppressionReason:
      "AI Comprehensive Analysis is suppressed because fewer than two approved Weekly News Focus items are available.",
    validationReasonCodes: [],
    sections: [],
    citationIds: [],
    sourceDocumentIds: [],
    weeklyNewsEventIds: [],
    canonicalFactCitationIds,
    citations: [],
    sourceDocuments: [],
    noLiveExternalCalls: true,
    stableFactsAreSeparate: true
  };
}

const marketNewsRows = [
  {
    storyId: "market_story_macro_policy",
    citationId: "c_market_news_macro_policy",
    sourceDocumentId: "src_market_news_macro_policy",
    publisher: "Reuters",
    sourceDomain: "reuters.com",
    title: "Fed officials describe inflation risks as policy debate continues",
    summary: "Federal Reserve reporting kept inflation and labor data in focus for the broad market.",
    publishedAt: "2026-04-22T13:00:00Z",
    topicBucket: "macro_fed" as const,
    entities: ["Federal Reserve", "inflation"],
    importanceScore: 89,
    criticalClaim: true
  },
  {
    storyId: "market_story_equity_earnings",
    citationId: "c_market_news_equity_earnings",
    sourceDocumentId: "src_market_news_equity_earnings",
    publisher: "CNBC",
    sourceDomain: "cnbc.com",
    title: "US stocks end mixed as earnings season drives sector moves",
    summary: "Equity-market reporting connected index moves with earnings updates and sector leadership.",
    publishedAt: "2026-04-22T20:30:00Z",
    topicBucket: "markets_earnings" as const,
    entities: ["S&P 500", "Nasdaq"],
    importanceScore: 82,
    criticalClaim: false
  },
  {
    storyId: "market_story_ai_chips",
    citationId: "c_market_news_ai_chips",
    sourceDocumentId: "src_market_news_ai_chips",
    publisher: "Financial Times",
    sourceDomain: "ft.com",
    title: "Chip demand remains central to AI infrastructure spending",
    summary: "Technology reporting kept AI infrastructure and semiconductor demand in the market-wide discussion.",
    publishedAt: "2026-04-22T10:00:00Z",
    topicBucket: "ai_technology_semiconductors" as const,
    entities: ["AI", "semiconductors"],
    importanceScore: 86,
    criticalClaim: false
  },
  {
    storyId: "market_story_energy_shipping",
    citationId: "c_market_news_energy_shipping",
    sourceDocumentId: "src_market_news_energy_shipping",
    publisher: "Associated Press",
    sourceDomain: "apnews.com",
    title: "Oil markets watch shipping risk after latest geopolitical flare-up",
    summary: "Energy reporting linked shipping risk with oil-market uncertainty and inflation watchpoints.",
    publishedAt: "2026-04-18T12:00:00Z",
    topicBucket: "geopolitics_energy_supply_chain" as const,
    entities: ["oil", "shipping"],
    importanceScore: 80,
    criticalClaim: true
  },
  {
    storyId: "market_story_credit_banks",
    citationId: "c_market_news_credit_banks",
    sourceDocumentId: "src_market_news_credit_banks",
    publisher: "Wall Street Journal",
    sourceDomain: "wsj.com",
    title: "Banks report cautious credit commentary as consumers slow",
    summary: "Bank coverage highlighted credit quality and consumer-stress commentary as broad-market context.",
    publishedAt: "2026-04-22T14:00:00Z",
    topicBucket: "credit_liquidity_sentiment" as const,
    entities: ["banks", "credit"],
    importanceScore: 84,
    criticalClaim: false
  }
];

export const marketNewsFocusFixture: MarketNewsFocusFixture = {
  schemaVersion: "market-news-focus-v1",
  state: "available",
  window: weeklyNewsWindow,
  configuredMaxItemCount: 20,
  selectedItemCount: marketNewsRows.length,
  suppressedCandidateCount: 0,
  evidenceState: "partial",
  evidenceLimitedState: "limited_verified_set",
  items: marketNewsRows.map((row) => ({
    storyId: row.storyId,
    title: row.title,
    summary: row.summary,
    publishedAt: row.publishedAt,
    topicBucket: row.topicBucket,
    entities: row.entities,
    citationIds: [row.citationId],
    source: {
      sourceDocumentId: row.sourceDocumentId,
      sourceType: "market_news_story_cluster",
      title: row.title,
      publisher: row.publisher,
      url: `https://${row.sourceDomain}/markets/${row.storyId}`,
      publishedAt: row.publishedAt,
      asOfDate: row.publishedAt.slice(0, 10),
      retrievedAt: "2026-04-23T12:00:00Z",
      freshnessState: "fresh",
      isOfficial: false,
      sourceQuality: "allowlisted",
      allowlistStatus: "allowed",
      sourceUsePolicy: "summary_allowed"
    },
    freshnessState: "fresh",
    importanceScore: row.importanceScore,
    cluster: {
      clusterId: `market_cluster_${row.storyId}`,
      representativeArticleId: `fixture_${row.storyId}`,
      supportingSources: [row.publisher],
      articleCount: 1,
      suppressedDuplicateCount: 0,
      topicBucket: row.topicBucket,
      criticalClaim: row.criticalClaim,
      corroborated: true
    }
  })),
  emptyState: null,
  citations: marketNewsRows.map((row) => ({
    citationId: row.citationId,
    sourceDocumentId: row.sourceDocumentId,
    title: row.title,
    publisher: row.publisher,
    freshnessState: "fresh"
  })),
  sourceDocuments: marketNewsRows.map((row) => ({
    sourceDocumentId: row.sourceDocumentId,
    sourceType: "market_news_story_cluster",
    title: row.title,
    publisher: row.publisher,
    url: `https://${row.sourceDomain}/markets/${row.storyId}`,
    publishedAt: row.publishedAt,
    asOfDate: row.publishedAt.slice(0, 10),
    retrievedAt: "2026-04-23T12:00:00Z",
    freshnessState: "fresh",
    isOfficial: false,
    supportingPassage: row.summary,
    sourceQuality: "allowlisted",
    source_quality: "allowlisted",
    allowlistStatus: "allowed",
    allowlist_status: "allowed",
    sourceUsePolicy: "summary_allowed",
    source_use_policy: "summary_allowed",
    permitted_operations: {
      can_export_full_text: false
    }
  })),
  noLiveExternalCalls: true,
  stableFactsAreSeparate: true,
  reusableAcrossTickers: true
};

export const marketAIComprehensiveAnalysisFixture: MarketAIComprehensiveAnalysisFixture = {
  schemaVersion: "market-ai-comprehensive-analysis-v1",
  state: "available",
  analysisAvailable: true,
  minimumMarketNewsItemCount: 5,
  minimumTopicBucketCount: 3,
  marketNewsSelectedItemCount: marketNewsFocusFixture.selectedItemCount,
  selectedTopicBucketCount: new Set(marketNewsFocusFixture.items.map((item) => item.topicBucket)).size,
  suppressionReason: null,
  sections: [
    {
      sectionId: "what_changed_this_week",
      label: "What Changed This Week",
      analysis:
        "The market-wide pack selected macro, equity, technology, geopolitical, and credit items for the shared weekly context layer.",
      bullets: ["This market context is reused across supported ticker pages and stays separate from ticker-specific facts."],
      citationIds: marketNewsFocusFixture.citations.map((citation) => citation.citationId),
      uncertainty: []
    },
    {
      sectionId: "macro_policy",
      label: "Macro & Policy",
      analysis: "Policy reporting kept inflation and labor data in focus for beginners reviewing broad market conditions.",
      bullets: ["Read policy items as current context, not as a forecast or personal instruction."],
      citationIds: ["c_market_news_macro_policy"],
      uncertainty: []
    },
    {
      sectionId: "equity_market_drivers",
      label: "Equity Market Drivers",
      analysis: "Earnings coverage connected index moves with sector leadership and company results.",
      bullets: ["Market drivers should be compared with each asset's own holdings or business exposure."],
      citationIds: ["c_market_news_equity_earnings"],
      uncertainty: []
    },
    {
      sectionId: "ai_technology_semiconductors",
      label: "AI / Technology / Semiconductors",
      analysis: "AI infrastructure and semiconductor demand remained a cross-market technology theme in the selected sources.",
      bullets: ["The theme is market context and does not replace ticker-specific exposure analysis."],
      citationIds: ["c_market_news_ai_chips"],
      uncertainty: []
    },
    {
      sectionId: "geopolitical_energy_risks",
      label: "Geopolitical & Energy Risks",
      analysis: "Shipping and oil headlines were selected because they can matter for inflation expectations and sentiment.",
      bullets: ["Later cited updates may confirm whether these stresses ease, continue, or broaden."],
      citationIds: ["c_market_news_energy_shipping"],
      uncertainty: []
    },
    {
      sectionId: "credit_liquidity_sentiment",
      label: "Credit / Liquidity / Sentiment",
      analysis: "Bank and consumer-stress commentary formed the credit and liquidity part of the market context pack.",
      bullets: ["Credit items are watchpoints for learning, not portfolio instructions."],
      citationIds: ["c_market_news_credit_banks"],
      uncertainty: []
    },
    {
      sectionId: "scenario_lens",
      label: "Scenario Lens",
      analysis:
        "If cited policy, energy, or credit stresses persist, beginners may watch whether later approved sources show easing, continuation, or broadening.",
      bullets: ["The scenario lens is conditional education from selected sources, not a return prediction."],
      citationIds: marketNewsFocusFixture.citations.map((citation) => citation.citationId),
      uncertainty: []
    },
    {
      sectionId: "practical_watchpoints",
      label: "Practical Watchpoints",
      analysis: "Use source dates, topic buckets, and citations to separate market-wide context from ticker-specific facts.",
      bullets: ["Compare future market updates with the selected asset's own Weekly News Focus before drawing conclusions."],
      citationIds: marketNewsFocusFixture.citations.map((citation) => citation.citationId),
      uncertainty: []
    }
  ],
  citationIds: marketNewsFocusFixture.citations.map((citation) => citation.citationId),
  sourceDocumentIds: marketNewsFocusFixture.sourceDocuments.map((source) => source.sourceDocumentId),
  marketNewsStoryIds: marketNewsFocusFixture.items.map((item) => item.storyId),
  citations: marketNewsFocusFixture.citations,
  sourceDocuments: marketNewsFocusFixture.sourceDocuments,
  noLiveExternalCalls: true,
  stableFactsAreSeparate: true
};

const economicIndicatorRows = [
  ["gdp", "Gross Domestic Product", "official_historical_actual", "2.0%", 2.0, "percent annualized", "2026-Q1", "2026-04-30", "BEA", "https://www.bea.gov/", "up"],
  ["cpi", "Consumer Price Index", "official_historical_actual", "3.3%", 3.3, "percent year over year", "2026-03", "2026-04-10", "BLS", "https://www.bls.gov/cpi/", "up"],
  ["ppi", "Producer Price Index", "official_historical_actual", "4.0%", 4.0, "percent year over year", "2026-03", "2026-04-11", "BLS", "https://www.bls.gov/ppi/", "up"],
  ["retail_sales", "Retail Sales", "official_historical_actual", "1.7%", 1.7, "percent month over month", "2026-03", "2026-04-15", "U.S. Census Bureau", "https://www.census.gov/retail/", "up"],
  ["nonfarm_payrolls", "Nonfarm Payrolls", "official_historical_actual", "115,000", 115000, "jobs", "2026-04", "2026-05-01", "BLS", "https://www.bls.gov/ces/", "up"],
  ["unemployment", "Unemployment Rate", "official_historical_actual", "4.3%", 4.3, "percent", "2026-04", "2026-05-01", "BLS", "https://www.bls.gov/cps/", "neutral"],
  ["jobless_claims", "Initial Jobless Claims", "official_historical_actual", "200,000", 200000, "claims", "2026-05-02", "2026-05-07", "U.S. Department of Labor", "https://www.dol.gov/ui/data.pdf", "up"],
  ["m2", "M2 Money Supply", "official_historical_actual", "22.69T", 22.69, "USD trillions", "2026-03", "2026-04-22", "Federal Reserve", "https://www.federalreserve.gov/releases/h6/", "up"],
  ["credit_card_delinquency", "Credit Card Delinquency Rate", "official_historical_actual", "2.94%", 2.94, "percent", "2026-Q1", "2026-05-01", "Federal Reserve", "https://www.federalreserve.gov/releases/chargeoff/", "neutral"],
  ["private_investment", "Real Private Fixed Investment", "official_historical_actual", "2.9%", 2.9, "percent annualized", "2026-Q1", "2026-04-30", "BEA", "https://www.bea.gov/data/gdp/gross-domestic-product", "up"],
  ["treasury_10y", "10-Year Treasury Yield", "official_historical_actual", "4.43%", 4.43, "percent", "2026-05-07", "2026-05-07", "U.S. Treasury", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates", "up"],
  ["treasury_3m", "3-Month Treasury Yield", "official_historical_actual", "3.68%", 3.68, "percent", "2026-05-07", "2026-05-07", "U.S. Treasury", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates", "up"],
  ["dxy", "U.S. Dollar Index (DXY)", "market_reference", "97.80", 97.8, "index level", "2026-05-07", "2026-05-07", "Market reference fixture", "local://fixtures/economic-indicators/dxy", "down"],
  ["vix", "Cboe Volatility Index (VIX)", "market_reference", "17.19", 17.19, "index level", "2026-05-07", "2026-05-07", "Market reference fixture", "local://fixtures/economic-indicators/vix", "down"],
  ["wti_oil", "WTI Crude Oil", "market_reference", "120.50", 120.5, "USD per barrel", "2026-05-09", "2026-05-09", "Market reference fixture", "local://fixtures/economic-indicators/wti", "up"]
] as const;

export const economicIndicatorsPackFixture: EconomicIndicatorsPackFixture = {
  schemaVersion: "economic-indicators-pack-v1",
  state: "available",
  region: "US",
  asOfDate: "2026-05-10",
  items: economicIndicatorRows.map(
    ([
      indicatorId,
      name,
      category,
      value,
      numericValue,
      unit,
      period,
      publishedAt,
      publisher,
      url,
      trendDirection
    ]) => ({
      indicatorId,
      name,
      category,
      value,
      numericValue,
      unit,
      period,
      asOfDate: period,
      publishedAt,
      retrievedAt: "2026-05-10T12:00:00Z",
      source: {
        sourceDocumentId: `src_economic_${indicatorId}`,
        sourceType: category === "market_reference" ? "market_reference" : "official_macro_release",
        title: `${name} source record`,
        publisher,
        url,
        publishedAt,
        asOfDate: period,
        retrievedAt: "2026-05-10T12:00:00Z",
        freshnessState: "fresh",
        isOfficial: category !== "market_reference",
        sourceQuality: category === "market_reference" ? "provider" : "official",
        allowlistStatus: "allowed",
        sourceUsePolicy: "summary_allowed"
      },
      freshnessState: "fresh",
      trendDirection,
      citationIds: [`c_economic_${indicatorId}`],
      sourceDocumentIds: [`src_economic_${indicatorId}`],
      evidenceState: "supported"
    })
  ),
  citations: economicIndicatorRows.map(([indicatorId, name, , , , , , , publisher]) => ({
    citationId: `c_economic_${indicatorId}`,
    sourceDocumentId: `src_economic_${indicatorId}`,
    title: `${name} source record`,
    publisher,
    freshnessState: "fresh"
  })),
  sourceDocuments: economicIndicatorRows.map(([indicatorId, name, category, , , , period, publishedAt, publisher, url]) => ({
    sourceDocumentId: `src_economic_${indicatorId}`,
    sourceType: category === "market_reference" ? "market_reference" : "official_macro_release",
    title: `${name} source record`,
    publisher,
    url,
    publishedAt,
    asOfDate: period,
    retrievedAt: "2026-05-10T12:00:00Z",
    freshnessState: "fresh",
    isOfficial: category !== "market_reference",
    supportingPassage:
      "Deterministic economic indicator fixture for contract validation; imported packs should replace it with validated current source records.",
    sourceQuality: category === "market_reference" ? "provider" : "official",
    source_quality: category === "market_reference" ? "provider" : "official",
    allowlistStatus: "allowed",
    allowlist_status: "allowed",
    sourceUsePolicy: "summary_allowed",
    source_use_policy: "summary_allowed",
    permitted_operations: {
      can_export_full_text: false
    }
  })),
  analysisPackMetadata: {
    analysisSource: "deterministic_fixture",
    validationStatus: "passed"
  },
  noLiveExternalCalls: true,
  stableFactsAreSeparate: true
};

export const weeklyNewsFocusFixtures: Record<string, WeeklyNewsFocusFixture> = {
  VOO: buildEmptyWeeklyNewsFocus(),
  AAPL: buildEmptyWeeklyNewsFocus(),
  QQQ: {
    schemaVersion: "weekly-news-focus-v1",
    state: "available",
    window: weeklyNewsWindow,
    configuredMaxItemCount: 8,
    selectedItemCount: 2,
    suppressedCandidateCount: 0,
    evidenceState: "partial",
    evidenceLimitedState: "limited_verified_set",
    items: [
      {
        eventId: "qqq_methodology_notice",
        assetTicker: "QQQ",
        eventType: "methodology_change",
        title: "Nasdaq-100 methodology notice in local fixture",
        summary:
          "The local weekly fixture highlights an index-methodology notice so beginners can separate short-term rule updates from the fund's stable role.",
        eventDate: "2026-04-21",
        publishedAt: "2026-04-21T12:00:00Z",
        periodBucket: "current_week_to_date",
        citationIds: ["c_weekly_qqq_methodology"],
        source: {
          sourceDocumentId: "src_qqq_weekly_methodology",
          sourceType: "issuer_announcement",
          title: "Nasdaq-100 methodology local fixture notice",
          publisher: "Nasdaq fixture",
          url: "local://fixtures/qqq/weekly-news/methodology",
          publishedAt: "2026-04-21",
          asOfDate: "2026-04-21",
          retrievedAt: "2026-04-23T12:00:00Z",
          freshnessState: "fresh",
          isOfficial: true,
          sourceQuality: "issuer",
          allowlistStatus: "allowed",
          sourceUsePolicy: "summary_allowed"
        },
        freshnessState: "fresh",
        importanceScore: 92
      },
      {
        eventId: "qqq_sponsor_update",
        assetTicker: "QQQ",
        eventType: "sponsor_update",
        title: "Invesco sponsor update in local fixture",
        summary:
          "The deterministic weekly fixture keeps a sponsor communication as timely context, without letting it rewrite the fund's core benchmark and holdings facts.",
        eventDate: "2026-04-18",
        publishedAt: "2026-04-18T12:00:00Z",
        periodBucket: "previous_market_week",
        citationIds: ["c_weekly_qqq_sponsor_update"],
        source: {
          sourceDocumentId: "src_qqq_weekly_sponsor_update",
          sourceType: "issuer_press_release",
          title: "Invesco QQQ sponsor-update local fixture notice",
          publisher: "Invesco fixture",
          url: "local://fixtures/qqq/weekly-news/sponsor-update",
          publishedAt: "2026-04-18",
          asOfDate: "2026-04-18",
          retrievedAt: "2026-04-23T12:00:00Z",
          freshnessState: "fresh",
          isOfficial: true,
          sourceQuality: "official",
          allowlistStatus: "allowed",
          sourceUsePolicy: "summary_allowed"
        },
        freshnessState: "fresh",
        importanceScore: 81
      }
    ],
    emptyState: null,
    citations: [
      {
        citationId: "c_weekly_qqq_methodology",
        sourceDocumentId: "src_qqq_weekly_methodology",
        title: "Nasdaq-100 methodology local fixture notice",
        publisher: "Nasdaq fixture",
        freshnessState: "fresh"
      },
      {
        citationId: "c_weekly_qqq_sponsor_update",
        sourceDocumentId: "src_qqq_weekly_sponsor_update",
        title: "Invesco QQQ sponsor-update local fixture notice",
        publisher: "Invesco fixture",
        freshnessState: "fresh"
      }
    ],
    sourceDocuments: [
      {
        sourceDocumentId: "src_qqq_weekly_methodology",
        sourceType: "issuer_announcement",
        title: "Nasdaq-100 methodology local fixture notice",
        publisher: "Nasdaq fixture",
        url: "local://fixtures/qqq/weekly-news/methodology",
        publishedAt: "2026-04-21",
        asOfDate: "2026-04-21",
        retrievedAt: "2026-04-23T12:00:00Z",
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "The local fixture notice flags a methodology update for Nasdaq-100 coverage during the Weekly News Focus window."
      },
      {
        sourceDocumentId: "src_qqq_weekly_sponsor_update",
        sourceType: "issuer_press_release",
        title: "Invesco QQQ sponsor-update local fixture notice",
        publisher: "Invesco fixture",
        url: "local://fixtures/qqq/weekly-news/sponsor-update",
        publishedAt: "2026-04-18",
        asOfDate: "2026-04-18",
        retrievedAt: "2026-04-23T12:00:00Z",
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "The local fixture sponsor update is kept as timely context and does not replace stable benchmark or holdings facts."
      }
    ],
    noLiveExternalCalls: true,
    stableFactsAreSeparate: true
  }
};

export const aiComprehensiveAnalysisFixtures: Record<string, AIComprehensiveAnalysisFixture> = {
  VOO: buildSuppressedAIComprehensiveAnalysis(["c_voo_profile"]),
  AAPL: buildSuppressedAIComprehensiveAnalysis(["c_aapl_profile"]),
  QQQ: {
    schemaVersion: "ai-comprehensive-analysis-v1",
    state: "available",
    analysisAvailable: true,
    minimumWeeklyNewsItemCount: 2,
    weeklyNewsSelectedItemCount: 2,
    suppressionReason: null,
    validationReasonCodes: [],
    sections: [
      {
        sectionId: "what_changed_this_week",
        label: "What Changed This Week",
        analysis:
          "The local Weekly News Focus pack selected a methodology notice and a sponsor update for QQQ, so this analysis stays tied to those two cited developments.",
        bullets: [
          "A methodology notice can matter for how beginners interpret an index ETF's short-term context.",
          "A sponsor update is timely context, not a redefinition of what QQQ is."
        ],
        citationIds: ["c_weekly_qqq_methodology", "c_weekly_qqq_sponsor_update"],
        uncertainty: []
      },
      {
        sectionId: "market_context",
        label: "Market Context",
        analysis:
          "Because QQQ is a narrower growth-oriented ETF than a broad-market fund, index-level context can be more noticeable, even when the local fixture does not include live market-move estimates.",
        bullets: ["The deterministic fixture does not estimate market impact or future performance."],
        citationIds: ["c_weekly_qqq_methodology", "c_qqq_profile"],
        uncertainty: ["No live market quote or performance-impact estimate is included in the local fixture."]
      },
      {
        sectionId: "business_or_fund_context",
        label: "Business/Fund Context",
        analysis:
          "The cited weekly items sit on top of a stable fact base: QQQ still tracks the Nasdaq-100 Index, and the timely context is shown separately so beginners do not confuse short-term updates with the fund's core identity.",
        bullets: ["Canonical facts stay anchored to the fund profile while weekly items explain what changed in the recent window."],
        citationIds: ["c_weekly_qqq_methodology", "c_weekly_qqq_sponsor_update", "c_qqq_profile"],
        uncertainty: []
      },
      {
        sectionId: "risk_context",
        label: "Risk Context",
        analysis:
          "For a more concentrated ETF, methodology or sponsor changes can deserve attention, but the local fixture does not claim that any single weekly item changes the beginner risk profile by itself.",
        bullets: ["Concentration and market exposure remain stable risks that should be learned separately from weekly updates."],
        citationIds: ["c_weekly_qqq_methodology", "c_qqq_profile"],
        uncertainty: ["The local fixture does not quantify any downstream effect from these weekly items."]
      }
    ],
    citationIds: ["c_weekly_qqq_methodology", "c_weekly_qqq_sponsor_update", "c_qqq_profile"],
    sourceDocumentIds: ["src_qqq_weekly_methodology", "src_qqq_weekly_sponsor_update", "src_qqq_fact_sheet_fixture"],
    weeklyNewsEventIds: ["qqq_methodology_notice", "qqq_sponsor_update"],
    canonicalFactCitationIds: ["c_qqq_profile"],
    citations: weeklyNewsFocusFixtures.QQQ.citations,
    sourceDocuments: weeklyNewsFocusFixtures.QQQ.sourceDocuments,
    noLiveExternalCalls: true,
    stableFactsAreSeparate: true
  }
};

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
        sourceDocumentId: "src_voo_fact_sheet_fixture",
        title: "Vanguard S&P 500 ETF fact sheet",
        publisher: "Vanguard",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_voo_benchmark",
        sourceDocumentId: "src_voo_fact_sheet_fixture",
        title: "Vanguard S&P 500 ETF fact sheet fixture excerpt",
        publisher: "Vanguard",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_voo_role",
        sourceDocumentId: "src_voo_fact_sheet_fixture",
        title: "Vanguard S&P 500 ETF fact sheet fixture excerpt",
        publisher: "Vanguard",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_voo_expense_ratio",
        sourceDocumentId: "src_voo_fact_sheet_fixture",
        title: "Vanguard S&P 500 ETF fact sheet fixture excerpt",
        publisher: "Vanguard",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_voo_holdings_count",
        sourceDocumentId: "src_voo_fact_sheet_fixture",
        title: "Vanguard S&P 500 ETF fact sheet fixture excerpt",
        publisher: "Vanguard",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_voo_holdings_exposure_detail",
        sourceDocumentId: "src_voo_holdings_fixture",
        title: "Vanguard S&P 500 ETF holdings fixture excerpt",
        publisher: "Vanguard",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_voo_construction_methodology",
        sourceDocumentId: "src_voo_prospectus_fixture",
        title: "Vanguard S&P 500 ETF summary prospectus fixture excerpt",
        publisher: "Vanguard",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_voo_trading_data_limitation",
        sourceDocumentId: "src_voo_trading_limitation",
        title: "VOO trading data availability fixture note",
        publisher: "Learn the Ticker fixtures",
        freshnessState: "unavailable"
      },
      {
        citationId: "c_chk_voo_risks_001",
        sourceDocumentId: "src_voo_prospectus_fixture",
        title: "Vanguard S&P 500 ETF summary prospectus fixture excerpt",
        publisher: "Vanguard",
        freshnessState: "fresh"
      },
      {
        citationId: "c_recent_voo_none",
        sourceDocumentId: "src_voo_recent_review",
        title: "VOO recent-development local fixture review",
        publisher: "Learn the Ticker fixtures",
        freshnessState: "fresh"
      }
    ],
    sourceDocuments: [
      {
        sourceDocumentId: "src_voo_fact_sheet_fixture",
        sourceType: "issuer_fact_sheet",
        title: "Vanguard S&P 500 ETF fact sheet fixture excerpt",
        publisher: "Vanguard",
        url: "https://investor.vanguard.com/",
        publishedAt: "2026-04-01",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "VOO seeks to track the performance of the S&P 500 Index, which represents large U.S. companies. The local fixture records VOO as an index ETF with a 0.03% expense ratio and about 500 holdings."
      },
      {
        sourceDocumentId: "src_voo_prospectus_fixture",
        sourceType: "summary_prospectus",
        title: "Vanguard S&P 500 ETF summary prospectus fixture excerpt",
        publisher: "Vanguard",
        url: "https://investor.vanguard.com/",
        publishedAt: "2026-04-01",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "The local prospectus fixture describes VOO as using a passive indexing approach to track a market-cap-weighted S&P 500 Index. The fund can lose value when U.S. large-company stocks decline, and index tracking does not remove market risk."
      },
      {
        sourceDocumentId: "src_voo_holdings_fixture",
        sourceType: "holdings_file",
        title: "Vanguard S&P 500 ETF holdings fixture excerpt",
        publisher: "Vanguard",
        url: "https://investor.vanguard.com/",
        publishedAt: "2026-04-01",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "The local holdings fixture records VOO as holding large U.S. companies across sectors; top holdings include Apple, Microsoft, Nvidia, Amazon.com, and Meta Platforms."
      },
      {
        sourceDocumentId: "src_voo_trading_limitation",
        sourceType: "structured_market_data",
        title: "VOO trading data availability fixture note",
        publisher: "Learn the Ticker fixtures",
        url: "local://fixtures/voo/trading-data-limitation",
        publishedAt: "2026-04-20",
        asOfDate: "2026-04-20",
        retrievedAt: stubTimestamp,
        freshnessState: "unavailable",
        isOfficial: false,
        supportingPassage:
          "The local structured-market-data fixture does not include bid-ask spread, average daily volume, or premium/discount metrics for VOO."
      },
      {
        sourceDocumentId: "src_voo_recent_review",
        sourceType: "recent_development",
        title: "VOO recent-development local fixture review",
        publisher: "Learn the Ticker fixtures",
        url: "local://fixtures/voo/recent-review",
        publishedAt: "2026-04-20",
        asOfDate: "2026-04-20",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: false,
        supportingPassage:
          "The local fixture review found no high-signal recent development for VOO to include in this deterministic retrieval pack."
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
        plainEnglishExplanation:
          "VOO owns a basket of stocks, so it can lose value when the market or the index segment it tracks declines.",
        citationIds: ["c_voo_profile"]
      },
      {
        title: "Concentration risk",
        plainEnglishExplanation:
          "VOO may hold many stocks, but large companies and larger index weights can still have an outsized effect on what investors experience.",
        citationIds: ["c_voo_profile"]
      },
      {
        title: "Tracking risk",
        plainEnglishExplanation:
          "An index ETF tries to follow its benchmark, but fees, trading, cash, and implementation details can make fund results differ from the index.",
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
        citationIds: ["c_recent_voo_none"],
        freshnessState: "fresh"
      }
    ],
    suitabilitySummary: {
      mayFit: "Educationally, it is useful for learning how broad U.S. large-company index ETFs work.",
      mayNotFit: "It may be less useful for learning about bonds, international stocks, or narrow sector exposure.",
      learnNext: "Compare it with a total-market ETF and a more concentrated growth ETF to understand diversification."
    },
    etfSections: [
      {
        sectionId: "fund_objective_role",
        title: "Fund Objective Or Role",
        sectionType: "stable_facts",
        beginnerSummary:
          "VOO seeks to track the S&P 500 Index and is represented as a broad U.S. large-company ETF in the local fixture.",
        items: [
          {
            itemId: "benchmark",
            title: "Benchmark",
            summary: "The fund seeks to track the S&P 500 Index.",
            citationIds: ["c_fact_voo_benchmark"],
            sourceDocumentIds: ["src_voo_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "beginner_role",
            title: "Beginner role",
            summary: "Broad U.S. large-company ETF",
            citationIds: ["c_fact_voo_role"],
            sourceDocumentIds: ["src_voo_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        metrics: [
          {
            metricId: "benchmark",
            label: "Benchmark",
            value: "S&P 500 Index",
            citationIds: ["c_fact_voo_benchmark"],
            sourceDocumentIds: ["src_voo_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_fact_voo_benchmark", "c_fact_voo_role"],
        sourceDocumentIds: ["src_voo_fact_sheet_fixture"],
        freshnessState: "fresh",
        evidenceState: "supported",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: null
      },
      {
        sectionId: "holdings_exposure",
        title: "Holdings Or Exposure",
        sectionType: "stable_facts",
        beginnerSummary:
          "The local fixture records about 500 holdings and includes a bounded top-holdings exposure note, but top-10 weights, concentration, sector exposure, country exposure, and largest-position data remain unavailable.",
        items: [
          {
            itemId: "holdings_count",
            title: "Holdings count",
            summary: "The local fixture records about 500 holdings.",
            citationIds: ["c_fact_voo_holdings_count"],
            sourceDocumentIds: ["src_voo_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "holdings_exposure_detail",
            title: "Holdings exposure detail",
            summary:
              "Large U.S. companies across sectors; top holdings include Apple, Microsoft, Nvidia, Amazon.com, and Meta Platforms.",
            citationIds: ["c_fact_voo_holdings_exposure_detail"],
            sourceDocumentIds: ["src_voo_holdings_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "holdings_detail_gap",
            title: "Remaining holdings and exposure gaps",
            summary:
              "The current local fixture does not include top-10 weights, top-10 concentration, sector exposure, country exposure, or largest-position data.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unavailable",
            evidenceState: "unavailable",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations:
              "The current local fixture does not include top-10 weights, top-10 concentration, sector exposure, country exposure, or largest-position data."
          }
        ],
        metrics: [
          {
            metricId: "holdings_count",
            label: "Holdings count",
            value: "500 approximate companies",
            citationIds: ["c_fact_voo_holdings_count"],
            sourceDocumentIds: ["src_voo_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_fact_voo_holdings_count", "c_fact_voo_holdings_exposure_detail"],
        sourceDocumentIds: ["src_voo_fact_sheet_fixture", "src_voo_holdings_fixture"],
        freshnessState: "unavailable",
        evidenceState: "mixed",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations:
          "The current local fixture does not include top-10 weights, top-10 concentration, sector exposure, country exposure, or largest-position data."
      },
      {
        sectionId: "construction_methodology",
        title: "Construction Or Methodology",
        sectionType: "stable_facts",
        beginnerSummary:
          "The local fixture supports VOO's index-tracking and passive market-cap-weighted S&P 500 construction context, but not full rebalancing or screening-rule detail.",
        items: [
          {
            itemId: "index_tracking",
            title: "Index tracking",
            summary: "VOO seeks to track the S&P 500 Index.",
            citationIds: ["c_fact_voo_benchmark"],
            sourceDocumentIds: ["src_voo_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "construction_methodology",
            title: "Construction methodology",
            summary: "Passive indexing approach to track a market-cap-weighted S&P 500 Index.",
            citationIds: ["c_fact_voo_construction_methodology"],
            sourceDocumentIds: ["src_voo_prospectus_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "methodology_detail_gap",
            title: "Remaining methodology details",
            summary:
              "The current local fixture does not include full rebalancing frequency, complete screening rules, or full methodology evidence.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unavailable",
            evidenceState: "unavailable",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations:
              "The current local fixture does not include full rebalancing frequency, complete screening rules, or full methodology evidence."
          }
        ],
        citationIds: ["c_fact_voo_benchmark", "c_fact_voo_construction_methodology"],
        sourceDocumentIds: ["src_voo_fact_sheet_fixture", "src_voo_prospectus_fixture"],
        freshnessState: "unavailable",
        evidenceState: "mixed",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations:
          "The current local fixture does not include full rebalancing frequency, complete screening rules, or full methodology evidence."
      },
      {
        sectionId: "cost_trading_context",
        title: "Cost And Trading Context",
        sectionType: "stable_facts",
        beginnerSummary:
          "Expense ratio is supported by the local fixture; unavailable trading metrics are called out as cited or explicit local limitations.",
        items: [
          {
            itemId: "expense_ratio",
            title: "Expense ratio",
            summary: "The local fixture records a 0.03% expense ratio.",
            citationIds: ["c_fact_voo_expense_ratio"],
            sourceDocumentIds: ["src_voo_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "trading_data_limitation",
            title: "Trading-data limitation",
            summary:
              "The local fixture does not include bid-ask spread, average daily volume, or premium/discount metrics for VOO.",
            citationIds: ["c_fact_voo_trading_data_limitation"],
            sourceDocumentIds: ["src_voo_trading_limitation"],
            freshnessState: "unavailable",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-20",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "bid_ask_spread_gap",
            title: "Bid-ask spread",
            summary: "No local fixture evidence is available for bid-ask spread.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unavailable",
            evidenceState: "unavailable",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations: "No local fixture evidence is available for bid-ask spread."
          },
          {
            itemId: "average_volume_gap",
            title: "Average volume",
            summary: "No local fixture evidence is available for average daily volume.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unavailable",
            evidenceState: "unavailable",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations: "No local fixture evidence is available for average daily volume."
          },
          {
            itemId: "premium_discount_gap",
            title: "Premium/discount",
            summary: "No local fixture evidence is available for premium or discount metrics.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unavailable",
            evidenceState: "unavailable",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations: "No local fixture evidence is available for premium or discount metrics."
          },
          {
            itemId: "stale_fee_snapshot_gap",
            title: "Stale fee snapshot",
            summary: "An older local fee snapshot exists only as a stale example and must not be used as fresh evidence.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "stale",
            evidenceState: "stale",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations: "An older local fee snapshot exists only as a stale example and must not be used as fresh evidence."
          }
        ],
        metrics: [
          {
            metricId: "expense_ratio",
            label: "Expense ratio",
            value: 0.03,
            unit: "%",
            citationIds: ["c_fact_voo_expense_ratio"],
            sourceDocumentIds: ["src_voo_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_fact_voo_expense_ratio", "c_fact_voo_trading_data_limitation"],
        sourceDocumentIds: ["src_voo_fact_sheet_fixture", "src_voo_trading_limitation"],
        freshnessState: "stale",
        evidenceState: "mixed",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations:
          "Bid-ask spread, average volume, premium/discount, and an older fee snapshot are not usable as fresh local evidence."
      },
      {
        sectionId: "etf_specific_risks",
        title: "ETF-Specific Risks",
        sectionType: "risk",
        beginnerSummary: "Exactly three top risks are shown first for beginner readability.",
        items: [
          {
            itemId: "risk_1",
            title: "Market risk",
            summary:
              "VOO owns a basket of stocks, so it can lose value when the market or the index segment it tracks declines.",
            citationIds: ["c_chk_voo_risks_001"],
            sourceDocumentIds: ["src_voo_prospectus_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "risk_2",
            title: "Concentration risk",
            summary:
              "VOO may hold many stocks, but large companies and larger index weights can still have an outsized effect on what investors experience.",
            citationIds: ["c_chk_voo_risks_001"],
            sourceDocumentIds: ["src_voo_prospectus_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "risk_3",
            title: "Tracking risk",
            summary:
              "An index ETF tries to follow its benchmark, but fees, trading, cash, and implementation details can make fund results differ from the index.",
            citationIds: ["c_chk_voo_risks_001"],
            sourceDocumentIds: ["src_voo_prospectus_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_chk_voo_risks_001"],
        sourceDocumentIds: ["src_voo_prospectus_fixture"],
        freshnessState: "fresh",
        evidenceState: "supported",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: null
      },
      {
        sectionId: "similar_assets_alternatives",
        title: "Similar Assets Or Simpler Alternatives",
        sectionType: "evidence_gap",
        beginnerSummary:
          "The current local fixture does not include asset-specific evidence for similar ETFs, simpler alternatives, holdings overlap, or diversification-addition claims.",
        items: [
          {
            itemId: "similar_assets_gap",
            title: "Similar assets and alternatives",
            summary:
              "The current local fixture does not include asset-specific evidence for similar ETFs, simpler alternatives, holdings overlap, or diversification-addition claims.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unknown",
            evidenceState: "unknown",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations:
              "The current local fixture does not include asset-specific evidence for similar ETFs, simpler alternatives, holdings overlap, or diversification-addition claims."
          }
        ],
        citationIds: [],
        sourceDocumentIds: [],
        freshnessState: "unknown",
        evidenceState: "unknown",
        asOfDate: null,
        retrievedAt: null,
        limitations:
          "The current local fixture does not include asset-specific evidence for similar ETFs, simpler alternatives, holdings overlap, or diversification-addition claims."
      },
      {
        sectionId: "evidence_limits",
        title: "Evidence Limits",
        sectionType: "evidence_gap",
        beginnerSummary:
          "Evidence limits are separated from ETF risks so beginners can see what the fund risks are before reading source freshness, issuer-coverage, and provider-fallback warnings.",
        items: [
          {
            itemId: "issuer_facts_are_point_in_time",
            title: "Issuer facts are point-in-time",
            summary:
              "Official issuer fact-sheet, prospectus, holdings, and exposure fields are dated evidence; check as-of dates before treating them as current.",
            citationIds: ["c_voo_profile"],
            sourceDocumentIds: ["src_voo_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "partial",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "provider_fallback_limits",
            title: "Provider fallback limits",
            summary:
              "Provider-derived ETF fields are source-labeled local-test data and should not be confused with official issuer fact sheets, holdings files, or prospectuses.",
            citationIds: ["c_fact_voo_trading_data_limitation"],
            sourceDocumentIds: ["src_voo_trading_limitation"],
            freshnessState: "unavailable",
            evidenceState: "partial",
            eventDate: null,
            asOfDate: null,
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_voo_profile", "c_fact_voo_trading_data_limitation"],
        sourceDocumentIds: ["src_voo_fact_sheet_fixture", "src_voo_trading_limitation"],
        freshnessState: "fresh",
        evidenceState: "partial",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: "This section explains source and freshness limits; it is not one of the asset's Top 3 Risks."
      },
      {
        sectionId: "recent_developments",
        title: "Recent Developments",
        sectionType: "recent_developments",
        beginnerSummary: "Recent context is kept separate from stable ETF facts.",
        items: [
          {
            itemId: "recent_1",
            title: "No high-signal recent development found in local fixture review",
            summary:
              "The deterministic fixture keeps recent context separate and explicitly records that no major recent item is available.",
            citationIds: ["c_recent_voo_none"],
            sourceDocumentIds: ["src_voo_recent_review"],
            freshnessState: "fresh",
            evidenceState: "no_major_recent_development",
            eventDate: null,
            asOfDate: "2026-04-20",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_recent_voo_none"],
        sourceDocumentIds: ["src_voo_recent_review"],
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
        beginnerSummary: "Educationally, it is useful for learning how broad U.S. large-company index ETFs work.",
        items: [
          {
            itemId: "risk_and_role_context",
            title: "Risk and role context",
            summary:
              "It may be less useful for learning about bonds, international stocks, or narrow sector exposure. Compare it with a total-market ETF and a more concentrated growth ETF to understand diversification.",
            citationIds: ["c_chk_voo_risks_001"],
            sourceDocumentIds: ["src_voo_prospectus_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_chk_voo_risks_001"],
        sourceDocumentIds: ["src_voo_prospectus_fixture"],
        freshnessState: "fresh",
        evidenceState: "supported",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: null
      }
    ],
    citationContexts: [
      {
        citationId: "c_fact_voo_benchmark",
        sourceDocumentId: "src_voo_fact_sheet_fixture",
        sectionId: "fund_objective_role",
        sectionTitle: "Fund Objective Or Role",
        claimContext: "Benchmark: the fund seeks to track the S&P 500 Index.",
        supportingPassage: "VOO seeks to track the performance of the S&P 500 Index, which represents large U.S. companies."
      },
      {
        citationId: "c_fact_voo_role",
        sourceDocumentId: "src_voo_fact_sheet_fixture",
        sectionId: "fund_objective_role",
        sectionTitle: "Fund Objective Or Role",
        claimContext: "Beginner role: broad U.S. large-company ETF.",
        supportingPassage: "VOO seeks to track the performance of the S&P 500 Index, which represents large U.S. companies."
      },
      {
        citationId: "c_fact_voo_holdings_count",
        sourceDocumentId: "src_voo_fact_sheet_fixture",
        sectionId: "holdings_exposure",
        sectionTitle: "Holdings Or Exposure",
        claimContext: "Holdings count: the local fixture records about 500 holdings.",
        supportingPassage: "The local fixture records VOO as an index ETF with a 0.03% expense ratio and about 500 holdings."
      },
      {
        citationId: "c_fact_voo_expense_ratio",
        sourceDocumentId: "src_voo_fact_sheet_fixture",
        sectionId: "cost_trading_context",
        sectionTitle: "Cost And Trading Context",
        claimContext: "Expense ratio: the local fixture records a 0.03% expense ratio.",
        supportingPassage: "The local fixture records VOO as an index ETF with a 0.03% expense ratio and about 500 holdings."
      },
      {
        citationId: "c_fact_voo_holdings_exposure_detail",
        sourceDocumentId: "src_voo_holdings_fixture",
        sectionId: "holdings_exposure",
        sectionTitle: "Holdings Or Exposure",
        claimContext:
          "Holdings exposure detail: large U.S. companies across sectors; top holdings include Apple, Microsoft, Nvidia, Amazon.com, and Meta Platforms.",
        supportingPassage:
          "The local holdings fixture records VOO as holding large U.S. companies across sectors; top holdings include Apple, Microsoft, Nvidia, Amazon.com, and Meta Platforms."
      },
      {
        citationId: "c_fact_voo_construction_methodology",
        sourceDocumentId: "src_voo_prospectus_fixture",
        sectionId: "construction_methodology",
        sectionTitle: "Construction Or Methodology",
        claimContext: "Construction methodology: passive indexing approach to track a market-cap-weighted S&P 500 Index.",
        supportingPassage:
          "The local prospectus fixture describes VOO as using a passive indexing approach to track a market-cap-weighted S&P 500 Index."
      },
      {
        citationId: "c_chk_voo_risks_001",
        sourceDocumentId: "src_voo_prospectus_fixture",
        sectionId: "etf_specific_risks",
        sectionTitle: "ETF-Specific Risks",
        claimContext:
          "Top risks: market risk, concentration risk, and tracking risk are the three ETF risks shown first.",
        supportingPassage:
          "The fund can lose value when U.S. large-company stocks decline, and index tracking does not remove market risk."
      },
      {
        citationId: "c_chk_voo_risks_001",
        sourceDocumentId: "src_voo_prospectus_fixture",
        sectionId: "educational_suitability",
        sectionTitle: "Educational Suitability",
        claimContext: "Risk and role context: VOO is useful for learning broad U.S. large-company index ETF exposure.",
        supportingPassage:
          "The fund can lose value when U.S. large-company stocks decline, and index tracking does not remove market risk."
      },
      {
        citationId: "c_fact_voo_trading_data_limitation",
        sourceDocumentId: "src_voo_trading_limitation",
        sectionId: "cost_trading_context",
        sectionTitle: "Cost And Trading Context",
        claimContext:
          "Trading-data limitation: the local fixture does not include bid-ask spread, average daily volume, or premium/discount metrics for VOO.",
        supportingPassage:
          "The local structured-market-data fixture does not include bid-ask spread, average daily volume, or premium/discount metrics for VOO."
      },
      {
        citationId: "c_recent_voo_none",
        sourceDocumentId: "src_voo_recent_review",
        sectionId: "recent_developments",
        sectionTitle: "Recent Developments",
        claimContext:
          "No high-signal recent development found in local fixture review; recent context remains separate from stable facts.",
        supportingPassage:
          "The local fixture review found no high-signal recent development for VOO to include in this deterministic retrieval pack."
      }
    ]
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
        sourceDocumentId: "src_qqq_fact_sheet_fixture",
        title: "Invesco QQQ Trust fact sheet",
        publisher: "Invesco",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_qqq_benchmark",
        sourceDocumentId: "src_qqq_fact_sheet_fixture",
        title: "Invesco QQQ Trust fact sheet fixture excerpt",
        publisher: "Invesco",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_qqq_role",
        sourceDocumentId: "src_qqq_fact_sheet_fixture",
        title: "Invesco QQQ Trust fact sheet fixture excerpt",
        publisher: "Invesco",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_qqq_expense_ratio",
        sourceDocumentId: "src_qqq_fact_sheet_fixture",
        title: "Invesco QQQ Trust fact sheet fixture excerpt",
        publisher: "Invesco",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_qqq_holdings_count",
        sourceDocumentId: "src_qqq_fact_sheet_fixture",
        title: "Invesco QQQ Trust fact sheet fixture excerpt",
        publisher: "Invesco",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_qqq_holdings_exposure_detail",
        sourceDocumentId: "src_qqq_holdings_fixture",
        title: "Invesco QQQ Trust holdings fixture excerpt",
        publisher: "Invesco",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_qqq_construction_methodology",
        sourceDocumentId: "src_qqq_prospectus_fixture",
        title: "Invesco QQQ Trust summary prospectus fixture excerpt",
        publisher: "Invesco",
        freshnessState: "fresh"
      },
      {
        citationId: "c_fact_qqq_trading_data_limitation",
        sourceDocumentId: "src_qqq_trading_limitation",
        title: "QQQ trading data availability fixture note",
        publisher: "Learn the Ticker fixtures",
        freshnessState: "unavailable"
      },
      {
        citationId: "c_chk_qqq_risks_001",
        sourceDocumentId: "src_qqq_prospectus_fixture",
        title: "Invesco QQQ Trust summary prospectus fixture excerpt",
        publisher: "Invesco",
        freshnessState: "fresh"
      },
      {
        citationId: "c_recent_qqq_none",
        sourceDocumentId: "src_qqq_recent_review",
        title: "QQQ recent-development local fixture review",
        publisher: "Learn the Ticker fixtures",
        freshnessState: "fresh"
      }
    ],
    sourceDocuments: [
      {
        sourceDocumentId: "src_qqq_fact_sheet_fixture",
        sourceType: "issuer_fact_sheet",
        title: "Invesco QQQ Trust fact sheet fixture excerpt",
        publisher: "Invesco",
        url: "https://www.invesco.com/",
        publishedAt: "2026-04-01",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "QQQ seeks investment results that generally correspond to the Nasdaq-100 Index. The local fixture records QQQ as an index ETF with a 0.20% expense ratio and about 100 holdings."
      },
      {
        sourceDocumentId: "src_qqq_prospectus_fixture",
        sourceType: "summary_prospectus",
        title: "Invesco QQQ Trust summary prospectus fixture excerpt",
        publisher: "Invesco",
        url: "https://www.invesco.com/",
        publishedAt: "2026-04-01",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "The local prospectus fixture describes QQQ as tracking the Nasdaq-100 Index, a modified market-cap-weighted index that excludes financial companies. QQQ can be more concentrated than broader equity funds, so a smaller group of companies or sectors can drive more of the fund's results."
      },
      {
        sourceDocumentId: "src_qqq_holdings_fixture",
        sourceType: "holdings_file",
        title: "Invesco QQQ Trust holdings fixture excerpt",
        publisher: "Invesco",
        url: "https://www.invesco.com/",
        publishedAt: "2026-04-01",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: true,
        supportingPassage:
          "The local holdings fixture records QQQ as holding large Nasdaq-listed non-financial companies; top holdings include Microsoft, Nvidia, Apple, Amazon.com, and Broadcom."
      },
      {
        sourceDocumentId: "src_qqq_trading_limitation",
        sourceType: "structured_market_data",
        title: "QQQ trading data availability fixture note",
        publisher: "Learn the Ticker fixtures",
        url: "local://fixtures/qqq/trading-data-limitation",
        publishedAt: "2026-04-20",
        asOfDate: "2026-04-20",
        retrievedAt: stubTimestamp,
        freshnessState: "unavailable",
        isOfficial: false,
        supportingPassage:
          "The local structured-market-data fixture does not include bid-ask spread, average daily volume, or premium/discount metrics for QQQ."
      },
      {
        sourceDocumentId: "src_qqq_recent_review",
        sourceType: "recent_development",
        title: "QQQ recent-development local fixture review",
        publisher: "Learn the Ticker fixtures",
        url: "local://fixtures/qqq/recent-review",
        publishedAt: "2026-04-20",
        asOfDate: "2026-04-20",
        retrievedAt: stubTimestamp,
        freshnessState: "fresh",
        isOfficial: false,
        supportingPassage:
          "The local fixture review found no high-signal recent development for QQQ to include in this deterministic retrieval pack."
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
        plainEnglishExplanation:
          "QQQ tracks a narrower or more specialized index segment, so a smaller set of companies or sectors can drive more of the fund's results.",
        citationIds: ["c_qqq_profile"]
      },
      {
        title: "Market risk",
        plainEnglishExplanation:
          "QQQ owns a basket of stocks, so it can lose value when the market or the index segment it tracks declines.",
        citationIds: ["c_qqq_profile"]
      },
      {
        title: "Tracking risk",
        plainEnglishExplanation:
          "An index ETF tries to follow its benchmark, but fees, trading, cash, and implementation details can make fund results differ from the index.",
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
        citationIds: ["c_recent_qqq_none"],
        freshnessState: "fresh"
      }
    ],
    suitabilitySummary: {
      mayFit:
        "Educationally, it is useful for learning how narrower growth-oriented ETF exposure differs from broad-market exposure.",
      mayNotFit: "It may be less useful as an example of a diversified total-market fund.",
      learnNext: "Compare its index, holdings count, and top-holding concentration with VOO."
    },
    etfSections: [
      {
        sectionId: "fund_objective_role",
        title: "Fund Objective Or Role",
        sectionType: "stable_facts",
        beginnerSummary:
          "QQQ seeks to track the Nasdaq-100 Index and is represented as a narrower growth-oriented ETF in the local fixture.",
        items: [
          {
            itemId: "benchmark",
            title: "Benchmark",
            summary: "The fund seeks to track the Nasdaq-100 Index.",
            citationIds: ["c_fact_qqq_benchmark"],
            sourceDocumentIds: ["src_qqq_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "beginner_role",
            title: "Beginner role",
            summary: "Narrower growth-oriented ETF",
            citationIds: ["c_fact_qqq_role"],
            sourceDocumentIds: ["src_qqq_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        metrics: [
          {
            metricId: "benchmark",
            label: "Benchmark",
            value: "Nasdaq-100 Index",
            citationIds: ["c_fact_qqq_benchmark"],
            sourceDocumentIds: ["src_qqq_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_fact_qqq_benchmark", "c_fact_qqq_role"],
        sourceDocumentIds: ["src_qqq_fact_sheet_fixture"],
        freshnessState: "fresh",
        evidenceState: "supported",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: null
      },
      {
        sectionId: "holdings_exposure",
        title: "Holdings Or Exposure",
        sectionType: "stable_facts",
        beginnerSummary:
          "The local fixture records about 100 holdings and includes a bounded top-holdings exposure note, but top-10 weights, concentration, sector exposure, country exposure, and largest-position data remain unavailable.",
        items: [
          {
            itemId: "holdings_count",
            title: "Holdings count",
            summary: "The local fixture records about 100 holdings.",
            citationIds: ["c_fact_qqq_holdings_count"],
            sourceDocumentIds: ["src_qqq_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "holdings_exposure_detail",
            title: "Holdings exposure detail",
            summary:
              "Large Nasdaq-listed non-financial companies; top holdings include Microsoft, Nvidia, Apple, Amazon.com, and Broadcom.",
            citationIds: ["c_fact_qqq_holdings_exposure_detail"],
            sourceDocumentIds: ["src_qqq_holdings_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "holdings_detail_gap",
            title: "Remaining holdings and exposure gaps",
            summary:
              "The current local fixture does not include top-10 weights, top-10 concentration, sector exposure, country exposure, or largest-position data.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unavailable",
            evidenceState: "unavailable",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations:
              "The current local fixture does not include top-10 weights, top-10 concentration, sector exposure, country exposure, or largest-position data."
          }
        ],
        metrics: [
          {
            metricId: "holdings_count",
            label: "Holdings count",
            value: "100 approximate companies",
            citationIds: ["c_fact_qqq_holdings_count"],
            sourceDocumentIds: ["src_qqq_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_fact_qqq_holdings_count", "c_fact_qqq_holdings_exposure_detail"],
        sourceDocumentIds: ["src_qqq_fact_sheet_fixture", "src_qqq_holdings_fixture"],
        freshnessState: "unavailable",
        evidenceState: "mixed",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations:
          "The current local fixture does not include top-10 weights, top-10 concentration, sector exposure, country exposure, or largest-position data."
      },
      {
        sectionId: "construction_methodology",
        title: "Construction Or Methodology",
        sectionType: "stable_facts",
        beginnerSummary:
          "The local fixture supports QQQ's Nasdaq-100 tracking, modified market-cap-weighted construction, and non-financial-company scope, but not full rebalancing or screening-rule detail.",
        items: [
          {
            itemId: "index_tracking",
            title: "Index tracking",
            summary: "QQQ seeks to track the Nasdaq-100 Index.",
            citationIds: ["c_fact_qqq_benchmark"],
            sourceDocumentIds: ["src_qqq_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "construction_methodology",
            title: "Construction methodology",
            summary:
              "Tracks the Nasdaq-100 Index, a modified market-cap-weighted index that excludes financial companies.",
            citationIds: ["c_fact_qqq_construction_methodology"],
            sourceDocumentIds: ["src_qqq_prospectus_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "methodology_detail_gap",
            title: "Remaining methodology details",
            summary:
              "The current local fixture does not include full rebalancing frequency, complete screening rules, or full methodology evidence.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unavailable",
            evidenceState: "unavailable",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations:
              "The current local fixture does not include full rebalancing frequency, complete screening rules, or full methodology evidence."
          }
        ],
        citationIds: ["c_fact_qqq_benchmark", "c_fact_qqq_construction_methodology"],
        sourceDocumentIds: ["src_qqq_fact_sheet_fixture", "src_qqq_prospectus_fixture"],
        freshnessState: "unavailable",
        evidenceState: "mixed",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations:
          "The current local fixture does not include full rebalancing frequency, complete screening rules, or full methodology evidence."
      },
      {
        sectionId: "cost_trading_context",
        title: "Cost And Trading Context",
        sectionType: "stable_facts",
        beginnerSummary:
          "Expense ratio is supported by the local fixture; unavailable trading metrics are called out as cited or explicit local limitations.",
        items: [
          {
            itemId: "expense_ratio",
            title: "Expense ratio",
            summary: "The local fixture records a 0.20% expense ratio.",
            citationIds: ["c_fact_qqq_expense_ratio"],
            sourceDocumentIds: ["src_qqq_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "trading_data_limitation",
            title: "Trading-data limitation",
            summary:
              "The local fixture does not include bid-ask spread, average daily volume, or premium/discount metrics for QQQ.",
            citationIds: ["c_fact_qqq_trading_data_limitation"],
            sourceDocumentIds: ["src_qqq_trading_limitation"],
            freshnessState: "unavailable",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-20",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "bid_ask_spread_gap",
            title: "Bid-ask spread",
            summary: "No local fixture evidence is available for bid-ask spread.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unavailable",
            evidenceState: "unavailable",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations: "No local fixture evidence is available for bid-ask spread."
          },
          {
            itemId: "average_volume_gap",
            title: "Average volume",
            summary: "No local fixture evidence is available for average daily volume.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unavailable",
            evidenceState: "unavailable",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations: "No local fixture evidence is available for average daily volume."
          },
          {
            itemId: "premium_discount_gap",
            title: "Premium/discount",
            summary: "No local fixture evidence is available for premium or discount metrics.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unavailable",
            evidenceState: "unavailable",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations: "No local fixture evidence is available for premium or discount metrics."
          }
        ],
        metrics: [
          {
            metricId: "expense_ratio",
            label: "Expense ratio",
            value: 0.2,
            unit: "%",
            citationIds: ["c_fact_qqq_expense_ratio"],
            sourceDocumentIds: ["src_qqq_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_fact_qqq_expense_ratio", "c_fact_qqq_trading_data_limitation"],
        sourceDocumentIds: ["src_qqq_fact_sheet_fixture", "src_qqq_trading_limitation"],
        freshnessState: "unavailable",
        evidenceState: "mixed",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: "Bid-ask spread, average volume, and premium/discount are not available in the local fixture."
      },
      {
        sectionId: "etf_specific_risks",
        title: "ETF-Specific Risks",
        sectionType: "risk",
        beginnerSummary: "Exactly three top risks are shown first for beginner readability.",
        items: [
          {
            itemId: "risk_1",
            title: "Concentration risk",
            summary:
              "QQQ tracks a narrower or more specialized index segment, so a smaller set of companies or sectors can drive more of the fund's results.",
            citationIds: ["c_chk_qqq_risks_001"],
            sourceDocumentIds: ["src_qqq_prospectus_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "risk_2",
            title: "Market risk",
            summary:
              "QQQ owns a basket of stocks, so it can lose value when the market or the index segment it tracks declines.",
            citationIds: ["c_chk_qqq_risks_001"],
            sourceDocumentIds: ["src_qqq_prospectus_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "risk_3",
            title: "Tracking risk",
            summary:
              "An index ETF tries to follow its benchmark, but fees, trading, cash, and implementation details can make fund results differ from the index.",
            citationIds: ["c_chk_qqq_risks_001"],
            sourceDocumentIds: ["src_qqq_prospectus_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_chk_qqq_risks_001"],
        sourceDocumentIds: ["src_qqq_prospectus_fixture"],
        freshnessState: "fresh",
        evidenceState: "supported",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: null
      },
      {
        sectionId: "similar_assets_alternatives",
        title: "Similar Assets Or Simpler Alternatives",
        sectionType: "evidence_gap",
        beginnerSummary:
          "The fixture has enough evidence for a bounded high-level VOO vs QQQ comparison but not a full holdings-overlap calculation, similar ETF list, simpler-alternative claim, or diversification-addition claim.",
        items: [
          {
            itemId: "similar_assets_gap",
            title: "Similar assets and alternatives",
            summary:
              "The fixture has enough evidence for a bounded high-level VOO vs QQQ comparison but not a full holdings-overlap calculation, similar ETF list, simpler-alternative claim, or diversification-addition claim.",
            citationIds: [],
            sourceDocumentIds: [],
            freshnessState: "unknown",
            evidenceState: "insufficient_evidence",
            eventDate: null,
            asOfDate: null,
            retrievedAt: null,
            limitations:
              "The fixture has enough evidence for a bounded high-level VOO vs QQQ comparison but not a full holdings-overlap calculation, similar ETF list, simpler-alternative claim, or diversification-addition claim."
          }
        ],
        citationIds: [],
        sourceDocumentIds: [],
        freshnessState: "unknown",
        evidenceState: "insufficient_evidence",
        asOfDate: null,
        retrievedAt: null,
        limitations:
          "The fixture has enough evidence for a bounded high-level VOO vs QQQ comparison but not a full holdings-overlap calculation, similar ETF list, simpler-alternative claim, or diversification-addition claim."
      },
      {
        sectionId: "evidence_limits",
        title: "Evidence Limits",
        sectionType: "evidence_gap",
        beginnerSummary:
          "Evidence limits are separated from ETF risks so beginners can see what the fund risks are before reading source freshness, issuer-coverage, and provider-fallback warnings.",
        items: [
          {
            itemId: "issuer_facts_are_point_in_time",
            title: "Issuer facts are point-in-time",
            summary:
              "Official issuer fact-sheet, prospectus, holdings, and exposure fields are dated evidence; check as-of dates before treating them as current.",
            citationIds: ["c_qqq_profile"],
            sourceDocumentIds: ["src_qqq_fact_sheet_fixture"],
            freshnessState: "fresh",
            evidenceState: "partial",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "provider_fallback_limits",
            title: "Provider fallback limits",
            summary:
              "Provider-derived ETF fields are source-labeled local-test data and should not be confused with official issuer fact sheets, holdings files, or prospectuses.",
            citationIds: ["c_fact_qqq_trading_data_limitation"],
            sourceDocumentIds: ["src_qqq_trading_limitation"],
            freshnessState: "unavailable",
            evidenceState: "partial",
            eventDate: null,
            asOfDate: null,
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_qqq_profile", "c_fact_qqq_trading_data_limitation"],
        sourceDocumentIds: ["src_qqq_fact_sheet_fixture", "src_qqq_trading_limitation"],
        freshnessState: "fresh",
        evidenceState: "partial",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: "This section explains source and freshness limits; it is not one of the asset's Top 3 Risks."
      },
      {
        sectionId: "recent_developments",
        title: "Recent Developments",
        sectionType: "recent_developments",
        beginnerSummary: "Recent context is kept separate from stable ETF facts.",
        items: [
          {
            itemId: "recent_1",
            title: "No high-signal recent development found in local fixture review",
            summary:
              "The deterministic fixture keeps recent context separate and explicitly records that no major recent item is available.",
            citationIds: ["c_recent_qqq_none"],
            sourceDocumentIds: ["src_qqq_recent_review"],
            freshnessState: "fresh",
            evidenceState: "no_major_recent_development",
            eventDate: null,
            asOfDate: "2026-04-20",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_recent_qqq_none"],
        sourceDocumentIds: ["src_qqq_recent_review"],
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
          "Educationally, it is useful for learning how narrower growth-oriented ETF exposure differs from broad-market exposure.",
        items: [
          {
            itemId: "risk_and_role_context",
            title: "Risk and role context",
            summary:
              "It may be less useful as an example of a diversified total-market fund. Compare its index, holdings count, and top-holding concentration with VOO.",
            citationIds: ["c_chk_qqq_risks_001"],
            sourceDocumentIds: ["src_qqq_prospectus_fixture"],
            freshnessState: "fresh",
            evidenceState: "supported",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_chk_qqq_risks_001"],
        sourceDocumentIds: ["src_qqq_prospectus_fixture"],
        freshnessState: "fresh",
        evidenceState: "supported",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: null
      }
    ],
    citationContexts: [
      {
        citationId: "c_fact_qqq_benchmark",
        sourceDocumentId: "src_qqq_fact_sheet_fixture",
        sectionId: "fund_objective_role",
        sectionTitle: "Fund Objective Or Role",
        claimContext: "Benchmark: the fund seeks to track the Nasdaq-100 Index.",
        supportingPassage: "QQQ seeks investment results that generally correspond to the Nasdaq-100 Index."
      },
      {
        citationId: "c_fact_qqq_role",
        sourceDocumentId: "src_qqq_fact_sheet_fixture",
        sectionId: "fund_objective_role",
        sectionTitle: "Fund Objective Or Role",
        claimContext: "Beginner role: narrower growth-oriented ETF.",
        supportingPassage: "QQQ seeks investment results that generally correspond to the Nasdaq-100 Index."
      },
      {
        citationId: "c_fact_qqq_holdings_count",
        sourceDocumentId: "src_qqq_fact_sheet_fixture",
        sectionId: "holdings_exposure",
        sectionTitle: "Holdings Or Exposure",
        claimContext: "Holdings count: the local fixture records about 100 holdings.",
        supportingPassage: "The local fixture records QQQ as an index ETF with a 0.20% expense ratio and about 100 holdings."
      },
      {
        citationId: "c_fact_qqq_expense_ratio",
        sourceDocumentId: "src_qqq_fact_sheet_fixture",
        sectionId: "cost_trading_context",
        sectionTitle: "Cost And Trading Context",
        claimContext: "Expense ratio: the local fixture records a 0.20% expense ratio.",
        supportingPassage: "The local fixture records QQQ as an index ETF with a 0.20% expense ratio and about 100 holdings."
      },
      {
        citationId: "c_fact_qqq_holdings_exposure_detail",
        sourceDocumentId: "src_qqq_holdings_fixture",
        sectionId: "holdings_exposure",
        sectionTitle: "Holdings Or Exposure",
        claimContext:
          "Holdings exposure detail: large Nasdaq-listed non-financial companies; top holdings include Microsoft, Nvidia, Apple, Amazon.com, and Broadcom.",
        supportingPassage:
          "The local holdings fixture records QQQ as holding large Nasdaq-listed non-financial companies; top holdings include Microsoft, Nvidia, Apple, Amazon.com, and Broadcom."
      },
      {
        citationId: "c_fact_qqq_construction_methodology",
        sourceDocumentId: "src_qqq_prospectus_fixture",
        sectionId: "construction_methodology",
        sectionTitle: "Construction Or Methodology",
        claimContext:
          "Construction methodology: tracks the Nasdaq-100 Index, a modified market-cap-weighted index that excludes financial companies.",
        supportingPassage:
          "The local prospectus fixture describes QQQ as tracking the Nasdaq-100 Index, a modified market-cap-weighted index that excludes financial companies."
      },
      {
        citationId: "c_chk_qqq_risks_001",
        sourceDocumentId: "src_qqq_prospectus_fixture",
        sectionId: "etf_specific_risks",
        sectionTitle: "ETF-Specific Risks",
        claimContext: "Top risks: concentration risk, market risk, and tracking risk are the three ETF risks shown first.",
        supportingPassage:
          "QQQ can be more concentrated than broader equity funds, so a smaller group of companies or sectors can drive more of the fund's results."
      },
      {
        citationId: "c_chk_qqq_risks_001",
        sourceDocumentId: "src_qqq_prospectus_fixture",
        sectionId: "educational_suitability",
        sectionTitle: "Educational Suitability",
        claimContext: "Risk and role context: QQQ is useful for learning narrower growth-oriented ETF exposure.",
        supportingPassage:
          "QQQ can be more concentrated than broader equity funds, so a smaller group of companies or sectors can drive more of the fund's results."
      },
      {
        citationId: "c_fact_qqq_trading_data_limitation",
        sourceDocumentId: "src_qqq_trading_limitation",
        sectionId: "cost_trading_context",
        sectionTitle: "Cost And Trading Context",
        claimContext:
          "Trading-data limitation: the local fixture does not include bid-ask spread, average daily volume, or premium/discount metrics for QQQ.",
        supportingPassage:
          "The local structured-market-data fixture does not include bid-ask spread, average daily volume, or premium/discount metrics for QQQ."
      },
      {
        citationId: "c_recent_qqq_none",
        sourceDocumentId: "src_qqq_recent_review",
        sectionId: "recent_developments",
        sectionTitle: "Recent Developments",
        claimContext:
          "No high-signal recent development found in local fixture review; recent context remains separate from stable facts.",
        supportingPassage:
          "The local fixture review found no high-signal recent development for QQQ to include in this deterministic retrieval pack."
      }
    ]
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
        title: "Single-company risk",
        plainEnglishExplanation: "AAPL represents one company, so company-specific results, filings, competition, and execution can matter a lot.",
        citationIds: ["c_chk_aapl_risks_001"]
      },
      {
        title: "Business and competition risk",
        plainEnglishExplanation:
          "A company's products, services, customer demand, competitors, and execution can change, so source-backed business facts should be read as a starting point for understanding the company.",
        citationIds: ["c_chk_aapl_risks_001"]
      },
      {
        title: "Financial and valuation risk",
        plainEnglishExplanation:
          "Reported financial results and valuation context can change over time, and market expectations can move faster than the latest filing or provider snapshot.",
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
            title: "Single-company risk",
            summary: "AAPL represents one company, so company-specific results, filings, competition, and execution can matter a lot.",
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
            title: "Business and competition risk",
            summary:
              "A company's products, services, customer demand, competitors, and execution can change, so source-backed business facts should be read as a starting point for understanding the company.",
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
            title: "Financial and valuation risk",
            summary:
              "Reported financial results and valuation context can change over time, and market expectations can move faster than the latest filing or provider snapshot.",
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
        sectionId: "evidence_limits",
        title: "Evidence Limits",
        sectionType: "evidence_gap",
        beginnerSummary:
          "Evidence limits are separated from the main risk cards so beginners can distinguish asset risk from source freshness, provider fallback, and missing-detail warnings.",
        items: [
          {
            itemId: "reported_facts_are_point_in_time",
            title: "Reported facts are point-in-time",
            summary:
              "SEC identity, filing, and XBRL fields are dated evidence. Check filing and period dates before treating a metric as the latest full picture.",
            citationIds: ["c_fact_aapl_revenue_trend"],
            sourceDocumentIds: ["src_aapl_xbrl_fixture"],
            freshnessState: "fresh",
            evidenceState: "partial",
            eventDate: null,
            asOfDate: "2026-04-01",
            retrievedAt: stubTimestamp,
            limitations: null
          },
          {
            itemId: "provider_reference_limits",
            title: "Provider reference limits",
            summary:
              "Provider-derived price, profile, valuation, and quote fields are reference context for learning; they are not official company filings or a valuation conclusion.",
            citationIds: ["c_fact_aapl_valuation_limitation"],
            sourceDocumentIds: ["src_aapl_valuation_limitation"],
            freshnessState: "unavailable",
            evidenceState: "partial",
            eventDate: null,
            asOfDate: null,
            retrievedAt: stubTimestamp,
            limitations: null
          }
        ],
        citationIds: ["c_fact_aapl_revenue_trend", "c_fact_aapl_valuation_limitation"],
        sourceDocumentIds: ["src_aapl_xbrl_fixture", "src_aapl_valuation_limitation"],
        freshnessState: "fresh",
        evidenceState: "partial",
        asOfDate: "2026-04-01",
        retrievedAt: stubTimestamp,
        limitations: "This section explains source and freshness limits; it is not one of the asset's Top 3 Risks."
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
          "Top risks: single-company risk, business and competition risk, and financial and valuation risk are the three risks shown first.",
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

export function toSourceDrawerDocument(source: SourceDocument): SourceDrawerSourceDocument {
  const sourceQuality =
    source.sourceQuality ??
    source.source_quality ??
    (source.isOfficial ? "official" : source.sourceType.startsWith("sec") ? "official" : "fixture");
  const allowlistStatus = source.allowlistStatus ?? source.allowlist_status ?? "allowed";
  const sourceUsePolicy =
    source.sourceUsePolicy ??
    source.source_use_policy ??
    (source.sourceType === "structured_market_data"
      ? "metadata_only"
      : source.isOfficial || source.sourceType.includes("sec")
        ? "full_text_allowed"
        : "summary_allowed");

  return {
    ...source,
    source_document_id: source.sourceDocumentId,
    source_type: source.sourceType,
    published_at: source.publishedAt,
    as_of_date: source.asOfDate ?? null,
    retrieved_at: source.retrievedAt,
    freshness_state: source.freshnessState,
    source_quality: sourceQuality,
    allowlist_status: allowlistStatus,
    source_use_policy: sourceUsePolicy,
    sourceQuality: sourceQuality,
    allowlistStatus: allowlistStatus,
    sourceUsePolicy: sourceUsePolicy
  };
}

export function getWeeklyNewsFocusFixture(ticker: string) {
  return weeklyNewsFocusFixtures[normalizeTicker(ticker)];
}

export function getAIComprehensiveAnalysisFixture(ticker: string) {
  return aiComprehensiveAnalysisFixtures[normalizeTicker(ticker)];
}

export function citationLabel(citationId: string) {
  if (citationId.startsWith("lw_cite_yahoo_")) {
    return "Provider";
  }
  if (citationId.startsWith("lw_cite_provider_issuer_")) {
    return "Issuer";
  }
  if (citationId.length > 42) {
    return "Source";
  }
  return citationId.replace("c_", "");
}
