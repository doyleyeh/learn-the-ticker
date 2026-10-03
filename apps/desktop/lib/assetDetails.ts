import {
  normalizeTicker,
  type AssetFixture,
  type AssetType,
  type Citation,
  type FreshnessState
} from "./fixtures";

type Fetcher = typeof fetch;

type BackendAssetIdentity = {
  ticker: string;
  name: string;
  asset_type: string;
  exchange: string | null;
  issuer: string | null;
  status: string;
  supported: boolean;
};

type BackendFreshness = {
  page_last_updated_at: string;
  facts_as_of: string;
  holdings_as_of: string | null;
  recent_events_as_of: string;
  freshness_state: string;
};

type BackendMetricValue = {
  value: string | number | null;
  unit: string | null;
  citation_ids: string[];
};

type BackendDetailsFacts = {
  business_model?: string;
  diversification_context?: string;
  role?: string;
  holdings?: string[];
  cost_context?: BackendMetricValue;
};

type BackendCitation = {
  citation_id: string;
  source_document_id: string;
  title: string;
  publisher: string;
  freshness_state: string;
};

type BackendDetailsResponse = {
  asset: BackendAssetIdentity;
  state: {
    status: string;
    message: string;
  };
  freshness: BackendFreshness;
  facts: BackendDetailsFacts;
  citations: BackendCitation[];
};

export async function fetchSupportedAssetDetails(
  ticker: string,
  fallbackAsset: AssetFixture,
  fetcher: Fetcher = fetch
): Promise<AssetFixture> {
  const normalizedTicker = normalizeTicker(ticker);
  const endpoint = assetDetailsEndpoint(normalizedTicker);
  const response = await fetcher(endpoint);

  if (!response.ok) {
    throw new Error(`Asset details request failed with status ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (!isSupportedAssetDetailsResponse(payload, normalizedTicker, fallbackAsset.assetType)) {
    throw new Error("Asset details response did not match the expected backend response contract.");
  }

  return mergeAssetFixtureWithDetails(fallbackAsset, payload);
}

function assetDetailsEndpoint(ticker: string) {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || process.env.API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new Error("No API base URL is configured for supported asset detail fetches.");
  }
  return new URL(`/api/assets/${encodeURIComponent(ticker)}/details`, apiBaseUrl).toString();
}

function isSupportedAssetDetailsResponse(
  value: unknown,
  requestedTicker: string,
  fallbackAssetType: AssetType
): value is BackendDetailsResponse {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<BackendDetailsResponse>;
  if (
    !candidate.asset ||
    typeof candidate.asset !== "object" ||
    candidate.asset.ticker !== requestedTicker ||
    candidate.asset.supported !== true ||
    candidate.asset.status !== "supported" ||
    candidate.asset.asset_type !== fallbackAssetType ||
    !candidate.state ||
    typeof candidate.state !== "object" ||
    candidate.state.status !== "supported" ||
    !candidate.freshness ||
    typeof candidate.freshness !== "object" ||
    typeof candidate.freshness.page_last_updated_at !== "string" ||
    typeof candidate.freshness.facts_as_of !== "string" ||
    typeof candidate.freshness.recent_events_as_of !== "string" ||
    !candidate.facts ||
    typeof candidate.facts !== "object" ||
    !Array.isArray(candidate.citations)
  ) {
    return false;
  }

  const facts = candidate.facts as BackendDetailsFacts;
  if (candidate.asset.asset_type === "stock") {
    return typeof facts.business_model === "string" && typeof facts.diversification_context === "string";
  }

  return (
    typeof facts.role === "string" &&
    Array.isArray(facts.holdings) &&
    facts.holdings.every((holding) => typeof holding === "string") &&
    isMetricValue(facts.cost_context)
  );
}

function mergeAssetFixtureWithDetails(fallbackAsset: AssetFixture, details: BackendDetailsResponse): AssetFixture {
  const assetWithFreshness = {
    ...fallbackAsset,
    freshness: {
      pageLastUpdatedAt: details.freshness.page_last_updated_at,
      factsAsOf: details.freshness.facts_as_of,
      holdingsAsOf: details.freshness.holdings_as_of ?? fallbackAsset.freshness.holdingsAsOf,
      recentEventsAsOf: details.freshness.recent_events_as_of
    },
    citations: mergeUniqueBy(
      details.citations.map(toCitation),
      fallbackAsset.citations,
      (citation) => citation.citationId
    )
  };

  if (assetWithFreshness.assetType === "stock") {
    return mergeStockDetails(assetWithFreshness, details.facts);
  }

  return mergeEtfDetails(assetWithFreshness, details.facts);
}

function mergeStockDetails(asset: AssetFixture, facts: BackendDetailsFacts): AssetFixture {
  const businessModel = facts.business_model;
  const diversificationContext = facts.diversification_context;
  if (!businessModel || !diversificationContext) {
    return asset;
  }

  const mergedFacts = upsertFact(
    upsertFact(asset.facts, "Business model", businessModel, findFactCitationId(asset, "Business model")),
    "Diversification context",
    diversificationContext,
    findFactCitationId(asset, "Diversification context")
  );

  const stockSections = asset.stockSections?.map((section) => {
    if (section.sectionId === "business_overview") {
      return {
        ...section,
        beginnerSummary: `The backend details contract describes ${asset.name} as a company with this business model: ${businessModel}. ${diversificationContext}.`,
        items: section.items.map((item) =>
          item.itemId === "primary_business"
            ? {
                ...item,
                summary: businessModel,
                asOfDate: asset.freshness.factsAsOf,
                retrievedAt: asset.freshness.pageLastUpdatedAt
              }
            : item
        ),
        asOfDate: asset.freshness.factsAsOf,
        retrievedAt: asset.freshness.pageLastUpdatedAt
      };
    }

    if (section.sectionId === "educational_suitability") {
      return {
        ...section,
        beginnerSummary: `${diversificationContext}. ${section.beginnerSummary}`,
        asOfDate: section.asOfDate ?? asset.freshness.factsAsOf,
        retrievedAt: section.retrievedAt ?? asset.freshness.pageLastUpdatedAt
      };
    }

    return section;
  });

  return {
    ...asset,
    facts: mergedFacts,
    stockSections
  };
}

function mergeEtfDetails(asset: AssetFixture, facts: BackendDetailsFacts): AssetFixture {
  const role = facts.role;
  const holdings = facts.holdings;
  const costContext = facts.cost_context;
  if (!role || !holdings?.length || !costContext) {
    return asset;
  }

  const expenseRatioValue = formatMetricValue(costContext);
  const holdingsSummary = holdings.join("; ");
  const expenseRatioCitationId = costContext.citation_ids[0] ?? findFactCitationId(asset, "Expense ratio");

  const mergedFacts = upsertFact(
    upsertFact(asset.facts, "Role", role, findFactCitationId(asset, "Role")),
    "Expense ratio",
    expenseRatioValue,
    expenseRatioCitationId
  );

  const etfSections = asset.etfSections?.map((section) => {
    if (section.sectionId === "fund_objective_role") {
      return {
        ...section,
        beginnerSummary: `The backend details contract keeps ${asset.ticker} in the role of ${role}.`,
        items: section.items.map((item) =>
          item.itemId === "beginner_role"
            ? {
                ...item,
                summary: role,
                asOfDate: asset.freshness.factsAsOf,
                retrievedAt: asset.freshness.pageLastUpdatedAt
              }
            : item
        ),
        asOfDate: asset.freshness.factsAsOf,
        retrievedAt: asset.freshness.pageLastUpdatedAt
      };
    }

    if (section.sectionId === "holdings_exposure") {
      return {
        ...section,
        beginnerSummary: `The backend details contract keeps holdings context bounded to: ${holdingsSummary}.`,
        items: section.items.map((item) =>
          item.itemId === "holdings_exposure_detail"
            ? {
                ...item,
                summary: holdingsSummary,
                asOfDate: asset.freshness.holdingsAsOf ?? asset.freshness.factsAsOf,
                retrievedAt: asset.freshness.pageLastUpdatedAt
              }
            : item
        ),
        asOfDate: asset.freshness.holdingsAsOf ?? asset.freshness.factsAsOf,
        retrievedAt: asset.freshness.pageLastUpdatedAt
      };
    }

    if (section.sectionId === "cost_trading_context") {
      return {
        ...section,
        beginnerSummary: `The backend details contract records an expense ratio of ${expenseRatioValue}, while any missing trading fields still stay labeled as unavailable or stale.`,
        items: section.items.map((item) =>
          item.itemId === "expense_ratio"
            ? {
                ...item,
                summary: `The backend details contract records a ${expenseRatioValue} expense ratio.`,
                citationIds: costContext.citation_ids.length ? costContext.citation_ids : item.citationIds,
                asOfDate: asset.freshness.factsAsOf,
                retrievedAt: asset.freshness.pageLastUpdatedAt
              }
            : item
        ),
        metrics: section.metrics?.map((metric) =>
          metric.metricId === "expense_ratio"
            ? {
                ...metric,
                value: costContext.value,
                unit: costContext.unit,
                citationIds: costContext.citation_ids.length ? costContext.citation_ids : metric.citationIds,
                asOfDate: asset.freshness.factsAsOf,
                retrievedAt: asset.freshness.pageLastUpdatedAt
              }
            : metric
        ),
        citationIds: mergeUniqueStringIds(
          section.citationIds,
          costContext.citation_ids.length ? costContext.citation_ids : section.citationIds
        ),
        asOfDate: asset.freshness.factsAsOf,
        retrievedAt: asset.freshness.pageLastUpdatedAt
      };
    }

    return section;
  });

  return {
    ...asset,
    facts: mergedFacts,
    etfSections
  };
}

function findFactCitationId(asset: AssetFixture, label: string) {
  return asset.facts.find((fact) => fact.label === label)?.citationId;
}

function upsertFact(
  facts: AssetFixture["facts"],
  label: string,
  value: string,
  citationId: string | undefined
): AssetFixture["facts"] {
  const existing = facts.find((fact) => fact.label === label);
  const nextFact = {
    label,
    value,
    citationId
  };

  if (existing) {
    return facts.map((fact) => (fact.label === label ? nextFact : fact));
  }

  return [...facts, nextFact];
}

function mergeUniqueBy<T>(preferred: T[], fallback: T[], getKey: (item: T) => string): T[] {
  const merged: T[] = [];
  const seen = new Set<string>();

  for (const collection of [preferred, fallback]) {
    for (const item of collection) {
      const key = getKey(item);
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      merged.push(item);
    }
  }

  return merged;
}

function mergeUniqueStringIds(existing: string[], preferred: string[]) {
  return [...new Set([...preferred, ...existing])];
}

function toCitation(citation: BackendCitation): Citation {
  return {
    citationId: citation.citation_id,
    sourceDocumentId: citation.source_document_id,
    title: citation.title,
    publisher: citation.publisher,
    freshnessState: toFreshnessState(citation.freshness_state)
  };
}

function isMetricValue(value: unknown): value is BackendMetricValue {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<BackendMetricValue>;
  return (
    ("value" in candidate) &&
    (candidate.unit === null || typeof candidate.unit === "string") &&
    Array.isArray(candidate.citation_ids) &&
    candidate.citation_ids.every((citationId) => typeof citationId === "string")
  );
}

function formatMetricValue(metric: BackendMetricValue) {
  if (metric.value === null || metric.value === undefined) {
    return "Unavailable";
  }

  return metric.unit ? `${metric.value}${metric.unit}` : String(metric.value);
}

function toFreshnessState(value: string): FreshnessState {
  if (
    value === "fresh" ||
    value === "stale" ||
    value === "unknown" ||
    value === "unavailable" ||
    value === "partial" ||
    value === "insufficient_evidence"
  ) {
    return value;
  }
  return "unknown";
}
