import { getComparePageFixture, getComparisonAvailabilityState, isComparisonAvailable } from "./compare";
import { getAssetFixture, normalizeTicker } from "./fixtures";

export type ComparisonSuggestionState =
  | "local_comparison_available"
  | "no_local_comparison_pack"
  | "unavailable_with_fixture_examples";

export type ComparisonSuggestion = {
  leftTicker: string;
  rightTicker: string;
  targetTicker: string;
  compareUrl: string;
  title: string;
  description: string;
  accessibleName: string;
};

export type ComparisonSuggestionsModel = {
  scope: "asset" | "compare";
  selectedTicker: string;
  state: ComparisonSuggestionState;
  heading: string;
  body: string;
  suggestions: ComparisonSuggestion[];
  requestedLeftTicker?: string;
  requestedRightTicker?: string;
  requestedAvailabilityState?: string;
};

const localComparisonPairs = [["VOO", "QQQ"] as const];

export function comparePageUrl(leftTicker: string, rightTicker: string) {
  return `/compare?left=${encodeURIComponent(normalizeTicker(leftTicker))}&right=${encodeURIComponent(
    normalizeTicker(rightTicker)
  )}`;
}

export function getAssetComparisonSuggestions(ticker: string): ComparisonSuggestionsModel {
  const selectedTicker = normalizeTicker(ticker);
  const asset = getAssetFixture(selectedTicker);
  const suggestions = asset ? availableSuggestionsForAsset(selectedTicker) : [];

  if (suggestions.length > 0) {
    return {
      scope: "asset",
      selectedTicker,
      state: "local_comparison_available",
      heading: "Available local comparison",
      body:
        "A local source-backed comparison exists for this fixture-backed asset. The comparison page covers benchmark, cost, holdings breadth, and beginner role without making a personal decision rule.",
      suggestions
    };
  }

  return {
    scope: "asset",
    selectedTicker,
    state: "no_local_comparison_pack",
    heading: "No local comparison pack",
    body: `No local source-backed comparison pack is available for ${selectedTicker}. This area does not create a peer list, citation chips, source documents, or generated factual differences.`,
    suggestions: []
  };
}

export function getComparePageSuggestions(leftTicker: string, rightTicker: string): ComparisonSuggestionsModel {
  const requestedLeftTicker = normalizeTicker(leftTicker);
  const requestedRightTicker = normalizeTicker(rightTicker);
  const requestedComparison = getComparePageFixture(requestedLeftTicker, requestedRightTicker);
  const requestedAvailabilityState = getComparisonAvailabilityState(requestedComparison);

  if (isComparisonAvailable(requestedComparison)) {
    return {
      scope: "compare",
      selectedTicker: `${requestedLeftTicker}-${requestedRightTicker}`,
      state: "local_comparison_available",
      heading: "Local comparison examples",
      body:
        "This requested pair has a local source-backed comparison pack. The suggestion links use the same relative in-app comparison route.",
      requestedLeftTicker,
      requestedRightTicker,
      requestedAvailabilityState,
      suggestions: [buildSuggestion(requestedLeftTicker, requestedRightTicker)]
    };
  }

  return {
    scope: "compare",
    selectedTicker: `${requestedLeftTicker}-${requestedRightTicker}`,
    state: "unavailable_with_fixture_examples",
    heading: "Available fixture example",
    body: `The requested ${requestedLeftTicker} and ${requestedRightTicker} comparison is ${formatAvailabilityState(requestedAvailabilityState)} in local deterministic data. The link below is only an existing local fixture example, not facts about the requested pair.`,
    requestedLeftTicker,
    requestedRightTicker,
    requestedAvailabilityState,
    suggestions: availableFixtureExamples()
  };
}

function availableSuggestionsForAsset(selectedTicker: string) {
  return localComparisonPairs.flatMap(([leftTicker, rightTicker]) => {
    if (selectedTicker === leftTicker && isLocalComparisonAvailable(leftTicker, rightTicker)) {
      return [buildSuggestion(leftTicker, rightTicker)];
    }

    if (selectedTicker === rightTicker && isLocalComparisonAvailable(rightTicker, leftTicker)) {
      return [buildSuggestion(rightTicker, leftTicker)];
    }

    return [];
  });
}

function availableFixtureExamples() {
  return localComparisonPairs
    .filter(([leftTicker, rightTicker]) => isLocalComparisonAvailable(leftTicker, rightTicker))
    .map(([leftTicker, rightTicker]) => buildSuggestion(leftTicker, rightTicker));
}

function isLocalComparisonAvailable(leftTicker: string, rightTicker: string) {
  const comparison = getComparePageFixture(leftTicker, rightTicker);
  return isComparisonAvailable(comparison);
}

function buildSuggestion(leftTicker: string, rightTicker: string): ComparisonSuggestion {
  const targetTicker = normalizeTicker(rightTicker);
  const normalizedLeft = normalizeTicker(leftTicker);
  const normalizedRight = normalizeTicker(rightTicker);

  return {
    leftTicker: normalizedLeft,
    rightTicker: normalizedRight,
    targetTicker,
    compareUrl: comparePageUrl(normalizedLeft, normalizedRight),
    title: `${normalizedLeft} vs ${normalizedRight}`,
    description:
      "Open the local source-backed comparison for benchmark, cost, holdings breadth, and beginner role.",
    accessibleName: `Open educational source-backed comparison for ${normalizedLeft} and ${normalizedRight}; this is not personal advice.`
  };
}

function formatAvailabilityState(availabilityState: string) {
  return availabilityState.replace(/_/g, " ");
}
