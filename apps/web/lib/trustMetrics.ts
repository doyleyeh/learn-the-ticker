export const TRUST_METRICS_SCHEMA_VERSION = "trust-metrics-event-v1";
export const TRUST_METRICS_DEFAULT_TIMESTAMP = "1970-01-01T00:00:00Z";
export const TRUST_METRICS_CATALOG_ROUTE = "/api/trust-metrics/catalog";
export const TRUST_METRICS_MODE = "validation_only";
export const TRUST_METRICS_PERSISTENCE = "none";
export const TRUST_METRICS_EXTERNAL_ANALYTICS = "none";
export const TRUST_METRICS_LIVE_EXTERNAL_CALLS = "none";

export const REQUIRED_PRODUCT_TRUST_METRIC_EVENTS = [
  "source_drawer_usage",
  "glossary_usage",
  "comparison_usage",
  "export_usage",
  "chat_answer_outcome",
  "chat_safety_redirect"
] as const;

export const REQUIRED_TRUST_METRIC_EVENTS = [
  "citation_coverage",
  "freshness_accuracy",
  "safety_redirect_rate"
] as const;

export type TrustMetricProductEventType = (typeof REQUIRED_PRODUCT_TRUST_METRIC_EVENTS)[number];
export type TrustMetricTrustEventType = (typeof REQUIRED_TRUST_METRIC_EVENTS)[number];
export type TrustMetricEventType = TrustMetricProductEventType | TrustMetricTrustEventType;

export type TrustMetricWorkflowArea =
  | "source_drawer"
  | "glossary"
  | "comparison"
  | "export"
  | "chat"
  | "citation"
  | "freshness"
  | "safety";

export type TrustMetricSurfaceDescriptor = {
  schemaVersion: typeof TRUST_METRICS_SCHEMA_VERSION;
  eventType: TrustMetricEventType;
  workflowArea: TrustMetricWorkflowArea;
  occurredAt: typeof TRUST_METRICS_DEFAULT_TIMESTAMP;
  mode: typeof TRUST_METRICS_MODE;
  persistence: typeof TRUST_METRICS_PERSISTENCE;
  externalAnalytics: typeof TRUST_METRICS_EXTERNAL_ANALYTICS;
  liveExternalCalls: typeof TRUST_METRICS_LIVE_EXTERNAL_CALLS;
  assetTicker?: string;
  assetSupportState?: string;
  comparisonLeftTicker?: string;
  comparisonRightTicker?: string;
  comparisonState?: string;
  exportContentType?: string;
  exportFormat?: string;
  citationCount?: number;
  sourceDocumentCount?: number;
  selectedSection?: string;
  freshnessState?: string;
  evidenceState?: string;
  safetyClassification?: string;
  chatOutcome?: string;
};

export type TrustMetricsCatalogValidation = {
  schemaVersion: string;
  validationOnly: boolean;
  persistenceEnabled: boolean;
  externalAnalyticsEnabled: boolean;
  noLiveExternalCalls: boolean;
  deterministicTimestampDefault: string;
  missingProductEventTypes: string[];
  missingTrustEventTypes: string[];
  isValid: boolean;
};

type CatalogEvent = {
  event_type?: unknown;
};

type CatalogResponseShape = {
  schema_version?: unknown;
  deterministic_timestamp_default?: unknown;
  validation_only?: unknown;
  persistence_enabled?: unknown;
  external_analytics_enabled?: unknown;
  no_live_external_calls?: unknown;
  product_events?: unknown;
  trust_events?: unknown;
};

export function buildTrustMetricSurfaceDescriptor(
  descriptor: Omit<
    TrustMetricSurfaceDescriptor,
    "schemaVersion" | "occurredAt" | "mode" | "persistence" | "externalAnalytics" | "liveExternalCalls"
  >
): TrustMetricSurfaceDescriptor {
  return {
    schemaVersion: TRUST_METRICS_SCHEMA_VERSION,
    occurredAt: TRUST_METRICS_DEFAULT_TIMESTAMP,
    mode: TRUST_METRICS_MODE,
    persistence: TRUST_METRICS_PERSISTENCE,
    externalAnalytics: TRUST_METRICS_EXTERNAL_ANALYTICS,
    liveExternalCalls: TRUST_METRICS_LIVE_EXTERNAL_CALLS,
    ...descriptor
  };
}

export function validateTrustMetricsCatalogResponse(value: unknown): TrustMetricsCatalogValidation {
  const candidate = isRecord(value) ? (value as CatalogResponseShape) : {};
  const productEventTypes = eventTypesFromCatalog(candidate.product_events);
  const trustEventTypes = eventTypesFromCatalog(candidate.trust_events);
  const missingProductEventTypes = REQUIRED_PRODUCT_TRUST_METRIC_EVENTS.filter(
    (eventType) => !productEventTypes.has(eventType)
  );
  const missingTrustEventTypes = REQUIRED_TRUST_METRIC_EVENTS.filter((eventType) => !trustEventTypes.has(eventType));
  const schemaVersion = typeof candidate.schema_version === "string" ? candidate.schema_version : "unknown";
  const deterministicTimestampDefault =
    typeof candidate.deterministic_timestamp_default === "string"
      ? candidate.deterministic_timestamp_default
      : "unknown";
  const validationOnly = candidate.validation_only === true;
  const persistenceEnabled = candidate.persistence_enabled === true;
  const externalAnalyticsEnabled = candidate.external_analytics_enabled === true;
  const noLiveExternalCalls = candidate.no_live_external_calls === true;

  return {
    schemaVersion,
    validationOnly,
    persistenceEnabled,
    externalAnalyticsEnabled,
    noLiveExternalCalls,
    deterministicTimestampDefault,
    missingProductEventTypes,
    missingTrustEventTypes,
    isValid:
      schemaVersion === TRUST_METRICS_SCHEMA_VERSION &&
      deterministicTimestampDefault === TRUST_METRICS_DEFAULT_TIMESTAMP &&
      validationOnly &&
      !persistenceEnabled &&
      !externalAnalyticsEnabled &&
      noLiveExternalCalls &&
      missingProductEventTypes.length === 0 &&
      missingTrustEventTypes.length === 0
  };
}

function eventTypesFromCatalog(value: unknown): Set<string> {
  if (!Array.isArray(value)) {
    return new Set();
  }

  return new Set(
    value
      .map((event) => (isRecord(event) ? (event as CatalogEvent).event_type : null))
      .filter((eventType): eventType is string => typeof eventType === "string")
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
