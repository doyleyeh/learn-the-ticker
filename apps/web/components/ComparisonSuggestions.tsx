import type { ComparisonSuggestionsModel } from "../lib/compareSuggestions";
import { buildTrustMetricSurfaceDescriptor } from "../lib/trustMetrics";

type ComparisonSuggestionsProps = {
  model: ComparisonSuggestionsModel;
};

export function ComparisonSuggestions({ model }: ComparisonSuggestionsProps) {
  const headingId = `comparison-suggestions-${model.selectedTicker.toLowerCase()}`;
  const trustMetricDescriptor = buildTrustMetricSurfaceDescriptor({
    eventType: "comparison_usage",
    workflowArea: "comparison",
    assetTicker: model.selectedTicker,
    comparisonLeftTicker: model.requestedLeftTicker ?? model.selectedTicker,
    comparisonRightTicker: model.requestedRightTicker ?? "",
    comparisonState: model.requestedAvailabilityState ?? model.state,
    selectedSection: "comparison_suggestions",
    citationCount: 0,
    sourceDocumentCount: 0
  });

  return (
    <section
      className="plain-panel comparison-suggestions"
      aria-labelledby={headingId}
      data-comparison-suggestions
      data-comparison-suggestion-scope={model.scope}
      data-comparison-suggestion-selected-ticker={model.selectedTicker}
      data-comparison-suggestion-state={model.state}
      data-comparison-requested-left={model.requestedLeftTicker ?? ""}
      data-comparison-requested-right={model.requestedRightTicker ?? ""}
      data-comparison-requested-availability-state={model.requestedAvailabilityState ?? ""}
      data-trust-metric-schema-version={trustMetricDescriptor.schemaVersion}
      data-trust-metric-mode={trustMetricDescriptor.mode}
      data-trust-metric-event={trustMetricDescriptor.eventType}
      data-trust-metric-workflow-area={trustMetricDescriptor.workflowArea}
      data-trust-metric-occurred-at={trustMetricDescriptor.occurredAt}
      data-trust-metric-persistence={trustMetricDescriptor.persistence}
      data-trust-metric-external-analytics={trustMetricDescriptor.externalAnalytics}
      data-trust-metric-live-external-calls={trustMetricDescriptor.liveExternalCalls}
      data-trust-metric-asset-ticker={trustMetricDescriptor.assetTicker}
      data-trust-metric-left-ticker={trustMetricDescriptor.comparisonLeftTicker}
      data-trust-metric-right-ticker={trustMetricDescriptor.comparisonRightTicker}
      data-trust-metric-comparison-state={trustMetricDescriptor.comparisonState}
      data-trust-metric-selected-section={trustMetricDescriptor.selectedSection}
      data-trust-metric-citation-count={trustMetricDescriptor.citationCount}
      data-trust-metric-source-document-count={trustMetricDescriptor.sourceDocumentCount}
    >
      <div className="section-heading">
        <p className="eyebrow">Compare locally</p>
        <h2 id={headingId}>{model.heading}</h2>
      </div>
      <p>{model.body}</p>

      {model.suggestions.length > 0 ? (
        <div className="comparison-suggestion-list" aria-label="Available local comparison suggestions">
          {model.suggestions.map((suggestion) => (
            <a
              className="comparison-suggestion-link"
              href={suggestion.compareUrl}
              key={`${suggestion.leftTicker}-${suggestion.rightTicker}`}
              data-comparison-suggestion-target={suggestion.targetTicker}
              data-comparison-suggestion-left={suggestion.leftTicker}
              data-comparison-suggestion-right={suggestion.rightTicker}
              data-comparison-suggestion-url={suggestion.compareUrl}
              aria-label={suggestion.accessibleName}
            >
              <strong>{suggestion.title}</strong>
              <span>{suggestion.description}</span>
            </a>
          ))}
        </div>
      ) : (
        <p className="source-gap-note" data-comparison-no-local-pack>
          No relative compare link is shown because no deterministic local comparison pack exists for this fixture.
        </p>
      )}
    </section>
  );
}
