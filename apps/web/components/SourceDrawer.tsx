import type { CitationContext, SourceDrawerSourceDocument } from "../lib/fixtures";
import { buildTrustMetricSurfaceDescriptor } from "../lib/trustMetrics";

type SourceDrawerRenderableDocument = SourceDrawerSourceDocument & {
  allowedExcerptNote?: string | null;
};

export type SourceDrawerState =
  | "available"
  | "unsupported"
  | "out_of_scope"
  | "unknown"
  | "eligible_not_cached"
  | "deleted"
  | "stale"
  | "partial"
  | "unavailable"
  | "insufficient_evidence";

export function sourceDrawerStateFromSupportState(supportState: string): SourceDrawerState {
  if (supportState === "supported") {
    return "available";
  }
  if (supportState === "unsupported") {
    return "unsupported";
  }
  if (supportState === "out_of_scope") {
    return "out_of_scope";
  }
  if (supportState === "eligible_not_cached") {
    return "eligible_not_cached";
  }
  if (supportState === "unknown") {
    return "unknown";
  }
  if (supportState === "deleted") {
    return "deleted";
  }
  if (supportState === "stale") {
    return "stale";
  }
  if (supportState === "partial") {
    return "partial";
  }
  if (supportState === "unavailable") {
    return "unavailable";
  }
  if (supportState === "insufficient_evidence") {
    return "insufficient_evidence";
  }
  return "unknown";
}

export function sourceDrawerStateFromFreshnessState(freshnessState: string): SourceDrawerState {
  if (freshnessState === "fresh") {
    return "available";
  }
  if (freshnessState === "stale") {
    return "stale";
  }
  if (freshnessState === "unknown") {
    return "unknown";
  }
  if (freshnessState === "unavailable") {
    return "unavailable";
  }
  if (freshnessState === "partial") {
    return "partial";
  }
  if (freshnessState === "insufficient_evidence") {
    return "insufficient_evidence";
  }
  return "unknown";
}

type SourceDrawerProps = {
  source: SourceDrawerRenderableDocument;
  claim: string;
  contexts?: CitationContext[];
  drawerState?: SourceDrawerState;
};

const HIDE_DETAILS_FOR_STATES = new Set<SourceDrawerState>([
  "unsupported",
  "out_of_scope",
  "unknown",
  "eligible_not_cached",
  "deleted",
  "unavailable",
  "partial",
  "insufficient_evidence"
]);
const FRESHNESS_DETAILS_BY_STATE: Record<
  SourceDrawerState,
  { label: string; canExposeSupportingPassage: boolean; canExposeSourceFields: boolean; allowlistStatusLabel: string }
> = {
  available: {
    label: "Source available in local evidence pack",
    canExposeSupportingPassage: true,
    canExposeSourceFields: true,
    allowlistStatusLabel: "Use metadata and supported excerpts only."
  },
  stale: {
    label: "Source freshness is stale",
    canExposeSupportingPassage: true,
    canExposeSourceFields: true,
    allowlistStatusLabel: "Use this source with a stale label."
  },
  unsupported: {
    label: "Source is unavailable for this asset state",
    canExposeSupportingPassage: false,
    canExposeSourceFields: false,
    allowlistStatusLabel: "Source metadata is suppressed in unsupported flows."
  },
  out_of_scope: {
    label: "Source suppressed for out-of-scope contract",
    canExposeSupportingPassage: false,
    canExposeSourceFields: false,
    allowlistStatusLabel: "Source metadata is suppressed for scope safety."
  },
  unknown: {
    label: "Source state is unknown",
    canExposeSupportingPassage: false,
    canExposeSourceFields: false,
    allowlistStatusLabel: "Source metadata is suppressed until a source state is available."
  },
  eligible_not_cached: {
    label: "Source not cached yet for eligible asset",
    canExposeSupportingPassage: false,
    canExposeSourceFields: false,
    allowlistStatusLabel: "Source metadata is suppressed until cached sources are available."
  },
  deleted: {
    label: "Source removed from this local state",
    canExposeSupportingPassage: false,
    canExposeSourceFields: false,
    allowlistStatusLabel: "Source metadata is no longer available."
  },
  partial: {
    label: "Source is partially available",
    canExposeSupportingPassage: false,
    canExposeSourceFields: false,
    allowlistStatusLabel: "Source fields are limited while evidence remains partial."
  },
  unavailable: {
    label: "Source is unavailable",
    canExposeSupportingPassage: false,
    canExposeSourceFields: false,
    allowlistStatusLabel: "Source metadata is suppressed while unavailable."
  },
  insufficient_evidence: {
    label: "Source has insufficient local evidence",
    canExposeSupportingPassage: false,
    canExposeSourceFields: false,
    allowlistStatusLabel: "Source metadata is limited due insufficient evidence."
  }
};

export function SourceDrawer({
  source,
  claim,
  contexts = [],
  drawerState = "available"
}: SourceDrawerProps) {
  const publishedOrAsOf = source.published_at ?? source.as_of_date ?? "Unknown";
  const supportingPassages = contexts.length
    ? [...new Set(contexts.map((context) => context.supportingPassage).filter(Boolean))]
    : [source.supportingPassage].filter(Boolean);
  const stateInfo = FRESHNESS_DETAILS_BY_STATE[drawerState];
  const canExposeSourceFields = stateInfo.canExposeSourceFields;
  const canExposeSupportingPassage = stateInfo.canExposeSupportingPassage;
  const isUnavailableFreshness = HIDE_DETAILS_FOR_STATES.has(drawerState);
  const trustMetricDescriptor = buildTrustMetricSurfaceDescriptor({
    eventType: "source_drawer_usage",
    workflowArea: "source_drawer",
    selectedSection: contexts[0]?.sectionId ?? "source_drawer",
    citationCount: contexts.length || (claim ? 1 : 0),
    sourceDocumentCount: 1,
    freshnessState: source.freshness_state,
    evidenceState: drawerState
  });

  return (
    <details
      className="source-drawer"
      id={`source-${source.source_document_id}`}
      data-source-document-id={source.source_document_id}
      data-source-freshness-state={source.freshness_state}
      data-source-drawer-state={drawerState}
      data-source-use-policy={source.source_use_policy}
      data-source-allowlist-status={source.allowlist_status}
      data-trust-metric-schema-version={trustMetricDescriptor.schemaVersion}
      data-trust-metric-mode={trustMetricDescriptor.mode}
      data-trust-metric-event={trustMetricDescriptor.eventType}
      data-trust-metric-workflow-area={trustMetricDescriptor.workflowArea}
      data-trust-metric-occurred-at={trustMetricDescriptor.occurredAt}
      data-trust-metric-persistence={trustMetricDescriptor.persistence}
      data-trust-metric-external-analytics={trustMetricDescriptor.externalAnalytics}
      data-trust-metric-live-external-calls={trustMetricDescriptor.liveExternalCalls}
      data-trust-metric-citation-count={trustMetricDescriptor.citationCount}
      data-trust-metric-source-document-count={trustMetricDescriptor.sourceDocumentCount}
      data-trust-metric-selected-section={trustMetricDescriptor.selectedSection}
      data-trust-metric-freshness-state={trustMetricDescriptor.freshnessState}
      data-trust-metric-evidence-state={trustMetricDescriptor.evidenceState}
      data-trust-metric-citation-coverage-event="citation_coverage"
      data-trust-metric-freshness-accuracy-event="freshness_accuracy"
      open
    >
      <summary>Source drawer</summary>
      <div className="source-body">
        <div className="source-title-row">
          <h2>{source.title}</h2>
          {source.isOfficial ? <span className="source-badge">Official source</span> : null}
        </div>
        <p className="source-gap-note">{stateInfo.label}</p>
        <dl className="source-meta">
          <div>
            <dt>Source document ID</dt>
            <dd>{source.source_document_id}</dd>
          </div>
          <div>
            <dt>Title</dt>
            <dd>{source.title}</dd>
          </div>
          <div>
            <dt>Type</dt>
            <dd>{source.source_type}</dd>
          </div>
          <div>
            <dt>Publisher</dt>
            <dd>{source.publisher}</dd>
          </div>
          <div>
            <dt>URL</dt>
            <dd>{source.url}</dd>
          </div>
          <div>
            <dt>Published or as of</dt>
            <dd>{publishedOrAsOf}</dd>
          </div>
          <div>
            <dt>Retrieved</dt>
            <dd>{source.retrieved_at}</dd>
          </div>
          <div>
            <dt>Freshness</dt>
            <dd>{source.freshness_state}</dd>
          </div>
          {canExposeSourceFields ? (
            <>
              <div>
                <dt>Source quality</dt>
                <dd>{source.source_quality}</dd>
              </div>
              <div>
                <dt>Allowlist status</dt>
                <dd>{source.allowlist_status}</dd>
              </div>
              <div>
                <dt>Source-use policy</dt>
                <dd>{source.source_use_policy}</dd>
              </div>
              <div>
                <dt>Full-text export allowed</dt>
                <dd>{String(source.permitted_operations?.can_export_full_text)}</dd>
              </div>
            </>
          ) : (
            <div>
              <dt>Source metadata</dt>
              <dd>{stateInfo.allowlistStatusLabel}</dd>
            </div>
          )}
        </dl>
        <div>
          <h3>Source state</h3>
          <p>{source.freshness_state}</p>
        </div>
        {isUnavailableFreshness ? (
          <p className="source-gap-note">{stateInfo.allowlistStatusLabel}</p>
        ) : null}
        <div>
          <h3>Related claim context</h3>
          {contexts.length ? (
            <ul className="source-context-list">
              {contexts.map((context) => (
                <li key={`${context.citationId}-${context.sectionId}-${context.claimContext}`}>
                  <strong>{context.citationId}</strong> supports {context.sectionTitle}: {context.claimContext}
                </li>
              ))}
            </ul>
          ) : (
            <p className="source-claim">{claim}</p>
          )}
        </div>

        <div>
          <h3>Supporting passage</h3>
          {source.allowedExcerptNote ? <p className="source-gap-note">{source.allowedExcerptNote}</p> : null}
          {canExposeSupportingPassage && !contexts.length ? (
            supportingPassages.length ? (
              supportingPassages.map((passage) => <blockquote key={passage}>{passage}</blockquote>)
            ) : (
              <p className="source-gap-note">No excerpt is available for this source drawer state.</p>
            )
          ) : null}
          {canExposeSupportingPassage && contexts.length ? (
            <p className="source-gap-note">
              Supporting passages are bound to related claims and hidden to avoid duplicate display.
            </p>
          ) : null}
          {!canExposeSupportingPassage ? (
            <p className="source-gap-note">{stateInfo.allowlistStatusLabel}</p>
          ) : null}
        </div>
        <a href={source.url}>Open source URL</a>
      </div>
    </details>
  );
}
