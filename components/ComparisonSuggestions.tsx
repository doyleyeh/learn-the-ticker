import type { ComparisonSuggestionsModel } from "../lib/compareSuggestions";

type ComparisonSuggestionsProps = {
  model: ComparisonSuggestionsModel;
};

export function ComparisonSuggestions({ model }: ComparisonSuggestionsProps) {
  const headingId = `comparison-suggestions-${model.selectedTicker.toLowerCase()}`;

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
