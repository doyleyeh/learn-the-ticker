"use client";

import { useMemo, useRef, useState } from "react";
import { formatSearchAssetType, resolveLocalSearchResponse, searchQueryExampleText, type LocalSearchResult } from "../lib/search";

type SearchState =
  | "empty"
  | "loading"
  | "supported"
  | "ambiguous"
  | "ingestion_needed"
  | "unsupported"
  | "out_of_scope"
  | "unknown"
  | "comparison";
const EXAMPLE_CHIPS = ["VOO", "QQQ", "AAPL", "NVDA", "SOXX"];
const V04_SUPPORT_STATE_CHIPS = [
  "Supported",
  "Pending ingestion",
  "Partial data",
  "Stale data",
  "Unsupported",
  "Out of scope",
  "Unavailable",
  "Unknown"
];

function noSupportedSearchMessage(query: string) {
  return `No supported stock or ETF found for "${query.trim()}".`;
}

function resultStateLabel(result: LocalSearchResult) {
  if (result.support_classification === "comparison_route") {
    return "Compare";
  }
  if (result.support_classification === "cached_supported") {
    return "Supported";
  }
  if (result.support_classification === "eligible_not_cached") {
    return "Pending ingestion";
  }
  if (result.support_classification === "recognized_unsupported") {
    return "Unsupported";
  }
  if (result.support_classification === "out_of_scope") {
    return "Out of scope";
  }
  return "Unknown";
}

function ResultIdentity({ result }: { result: LocalSearchResult }) {
  return (
    <>
      <strong data-search-result-ticker>{result.ticker}</strong>
      <span data-search-result-name>{result.name}</span>
      <span data-search-result-type>{formatSearchAssetType(result)}</span>
      {result.exchange ? <span data-search-result-exchange>{result.exchange}</span> : null}
      {result.issuer ? <span data-search-result-issuer>{result.issuer}</span> : null}
      <span data-search-result-state-label>{resultStateLabel(result)}</span>
    </>
  );
}

export function SearchBox() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<SearchState>("empty");
  const searchRequestId = useRef(0);
  const resolution = useMemo(() => resolveLocalSearchResponse(query), [query]);
  const singleResult = state !== "ambiguous" && state !== "empty" && state !== "loading" ? resolution.results[0] : null;
  const canOpenSupportedAsset = state === "supported" && Boolean(singleResult?.can_open_generated_page && singleResult.generated_route);
  const canOpenComparison = state === "comparison" && Boolean(singleResult?.comparison_route);

  const helperText = useMemo(() => {
    if (state === "empty") {
      return searchQueryExampleText();
    }
    if (state === "loading") {
      return "Checking deterministic local search fixtures only.";
    }
    if (state === "supported" && singleResult) {
      return `${singleResult.ticker} has a cached local generated page available today.`;
    }
    if (state === "ingestion_needed" || state === "ambiguous") {
      return resolution.state.message;
    }
    if (state === "comparison") {
      return resolution.state.message;
    }
    if (state === "unsupported" || state === "out_of_scope") {
      return resolution.state.blocked_explanation?.summary ?? resolution.state.message;
    }
    return noSupportedSearchMessage(query);
  }, [query, resolution.state.blocked_explanation, resolution.state.message, singleResult, state]);

  function handleChange(value: string) {
    setQuery(value);
    const nextResolution = resolveLocalSearchResponse(value);
    searchRequestId.current += 1;
    const requestId = searchRequestId.current;

    if (!value.trim()) {
      setState("empty");
      return;
    }

    setState("loading");
    window.setTimeout(() => {
      if (requestId === searchRequestId.current) {
        setState(nextResolution.state.status);
      }
    }, 120);
  }

  return (
    <section className="search-workflow" aria-label="Single stock or ETF search" data-home-primary-action="single-asset-search">
      <label htmlFor="ticker-search">Ticker or asset name</label>
      <div className="search-row">
        <input
          id="ticker-search"
          name="q"
          value={query}
          placeholder="Search a ticker or name, like VOO, QQQ, or Apple"
          onChange={(event) => handleChange(event.target.value)}
        />
        <a
          className={`search-button ${canOpenSupportedAsset || canOpenComparison ? "" : "disabled-link"}`}
          aria-disabled={!canOpenSupportedAsset && !canOpenComparison}
          href={
            canOpenSupportedAsset && singleResult?.generated_route
              ? singleResult.generated_route
              : canOpenComparison && singleResult?.comparison_route
                ? singleResult.comparison_route
                : "#search-status"
          }
          data-search-open-generated-page={canOpenSupportedAsset}
          data-search-open-comparison-route={canOpenComparison}
        >
          {canOpenComparison ? "Compare" : "Open"}
        </a>
      </div>
      <p
        id="search-status"
        className={`search-status status-${state}`}
        data-search-state={state}
        data-search-support-classification={resolution.state.support_classification ?? "none"}
      >
        {helperText}
      </p>
      <div className="support-state-legend" aria-label="Search support-state labels" data-search-support-state-labels>
        {V04_SUPPORT_STATE_CHIPS.map((label) => (
          <span key={label} data-search-support-state-chip={label}>
            {label}
          </span>
        ))}
      </div>
      {state === "comparison" && singleResult?.comparison_route ? (
        <div
          className="search-result-panel comparison-route-panel"
          data-search-comparison-result
          data-search-special-autocomplete-result
          data-search-comparison-left={singleResult.comparison_left_ticker ?? ""}
          data-search-comparison-right={singleResult.comparison_right_ticker ?? ""}
          data-search-comparison-route={singleResult.comparison_route}
        >
          <a href={singleResult.comparison_route} data-search-comparison-link>
            <ResultIdentity result={singleResult} />
          </a>
          <span data-search-result-message>{singleResult.message}</span>
        </div>
      ) : null}
      {state === "supported" && singleResult ? (
        <div
          className="search-result-panel"
          data-search-supported-result
          data-search-result-status={singleResult.status}
          data-search-support-classification={singleResult.support_classification}
          data-search-can-open-generated-page={singleResult.can_open_generated_page}
        >
          <a href={singleResult.generated_route ?? "#search-status"} data-search-result-link>
            <ResultIdentity result={singleResult} />
          </a>
          <span data-search-result-message>{singleResult.message}</span>
        </div>
      ) : null}
      {state === "ambiguous" ? (
        <div
          className="search-result-panel"
          data-search-ambiguous-result
          data-search-multi-result
          data-search-disambiguation-required
          data-search-result-groups="stock etf"
        >
          {resolution.results.map((result) =>
            result.can_open_generated_page && result.generated_route ? (
              <a
                key={result.ticker}
                href={result.generated_route}
                data-search-result-link
                data-search-result-group={result.asset_type}
                data-search-support-classification={result.support_classification}
                data-search-can-open-generated-page={result.can_open_generated_page}
              >
                <ResultIdentity result={result} />
              </a>
            ) : (
              <span
                key={result.ticker}
                data-search-ambiguous-candidate
                data-search-result-group={result.asset_type}
                data-search-support-classification={result.support_classification}
                data-search-can-open-generated-page={result.can_open_generated_page}
              >
                <ResultIdentity result={result} />
                <span data-search-ambiguous-candidate-note>
                  {result.support_classification === "eligible_not_cached"
                    ? "Choose the ticker first. This candidate still needs ingestion before any generated page can open."
                    : "Choose the ticker first before opening any generated asset experience."}
                </span>
              </span>
            )
          )}
        </div>
      ) : null}
      {state === "ingestion_needed" && singleResult ? (
        <div
          className="search-result-panel"
          data-search-ingestion-needed-result
          data-search-eligible-not-cached-result
          data-search-result-status={singleResult.status}
          data-search-support-classification={singleResult.support_classification}
          data-search-can-open-generated-page={singleResult.can_open_generated_page}
        >
          <span>
            <ResultIdentity result={singleResult} />
          </span>
          <span data-search-result-message>{singleResult.message}</span>
          <span data-search-ingestion-needed-message>
            No generated asset page, grounded chat, or comparison is available today. A future ingestion step would be
            required first.
          </span>
        </div>
      ) : null}
      {state === "unsupported" && singleResult ? (
        <div
          className="search-result-panel"
          data-search-unsupported-result
          data-search-blocked-result
          data-search-result-status={singleResult.status}
          data-search-support-classification={singleResult.support_classification}
        >
          <span>
            <ResultIdentity result={singleResult} />
          </span>
          <span data-search-blocked-summary>{singleResult.blocked_explanation?.summary ?? singleResult.message}</span>
          <span data-search-blocked-rationale>{singleResult.blocked_explanation?.scope_rationale}</span>
          <span data-search-blocked-scope>{singleResult.blocked_explanation?.supported_v1_scope}</span>
        </div>
      ) : null}
      {state === "out_of_scope" && singleResult ? (
        <div
          className="search-result-panel"
          data-search-out-of-scope-result
          data-search-blocked-result
          data-search-result-status={singleResult.status}
          data-search-support-classification={singleResult.support_classification}
        >
          <span>
            <ResultIdentity result={singleResult} />
          </span>
          <span data-search-blocked-summary>{singleResult.blocked_explanation?.summary ?? singleResult.message}</span>
          <span data-search-blocked-rationale>{singleResult.blocked_explanation?.scope_rationale}</span>
          <span data-search-blocked-scope>{singleResult.blocked_explanation?.supported_v1_scope}</span>
        </div>
      ) : null}
      {state === "unknown" ? (
        <div className="search-result-panel unknown-state" data-search-unknown-result data-search-no-invented-facts>
          <span data-search-unknown-message>{noSupportedSearchMessage(query)}</span>
          <span data-search-unknown-evidence-note>No facts are invented for this ticker or name.</span>
        </div>
      ) : null}
      <div className="quick-links example-chip-row" aria-label="Example searches only, not recommendations">
        <span className="example-chip-note">Examples only, not recommendations</span>
        {EXAMPLE_CHIPS.map((example) => (
          <button key={example} type="button" className="example-chip" onClick={() => handleChange(example)}>
            {example}
          </button>
        ))}
      </div>
    </section>
  );
}
