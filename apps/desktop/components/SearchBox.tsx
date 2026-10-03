"use client";

import { useMemo, useRef, useState } from "react";
import { assetFixtures } from "../lib/fixtures";
import { formatSearchAssetType, resolveLocalSearchResponse, searchQueryExampleText, type LocalSearchResult } from "../lib/search";

type SearchState = "empty" | "loading" | "supported" | "ambiguous" | "ingestion_needed" | "unsupported" | "out_of_scope" | "unknown";
const UNKNOWN_SEARCH_MESSAGE = "Unknown in the local skeleton data. No facts are invented for this ticker or name.";

function resultStateLabel(result: LocalSearchResult) {
  if (result.support_classification === "cached_supported") {
    return "Generated page ready";
  }
  if (result.support_classification === "eligible_not_cached") {
    return "Ingestion needed";
  }
  if (result.support_classification === "recognized_unsupported") {
    return "Unsupported in v1";
  }
  if (result.support_classification === "out_of_scope") {
    return "Outside current stock scope";
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
    if (state === "unsupported" || state === "out_of_scope") {
      return resolution.state.blocked_explanation?.summary ?? resolution.state.message;
    }
    return UNKNOWN_SEARCH_MESSAGE;
  }, [resolution.state.blocked_explanation, resolution.state.message, singleResult, state]);

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
    <section className="search-workflow" aria-label="Ticker or asset name search">
      <label htmlFor="ticker-search">Ticker or asset name</label>
      <div className="search-row">
        <input
          id="ticker-search"
          name="q"
          value={query}
          placeholder="VOO, Apple, SPY, BTC, or GME"
          onChange={(event) => handleChange(event.target.value)}
        />
        <a
          className={`search-button ${canOpenSupportedAsset ? "" : "disabled-link"}`}
          aria-disabled={!canOpenSupportedAsset}
          href={canOpenSupportedAsset && singleResult?.generated_route ? singleResult.generated_route : "#search-status"}
          data-search-open-generated-page={canOpenSupportedAsset}
        >
          Open
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
        >
          {resolution.results.map((result) =>
            result.can_open_generated_page && result.generated_route ? (
              <a
                key={result.ticker}
                href={result.generated_route}
                data-search-result-link
                data-search-support-classification={result.support_classification}
                data-search-can-open-generated-page={result.can_open_generated_page}
              >
                <ResultIdentity result={result} />
              </a>
            ) : (
              <span
                key={result.ticker}
                data-search-ambiguous-candidate
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
          <span data-search-unknown-message>{UNKNOWN_SEARCH_MESSAGE}</span>
        </div>
      ) : null}
      <div className="quick-links" aria-label="Supported examples">
        {Object.values(assetFixtures).map((example) => (
          <a key={example.ticker} href={`/assets/${example.ticker}`}>
            {example.ticker}
          </a>
        ))}
        <a href="/compare?left=VOO&right=QQQ">VOO vs QQQ</a>
      </div>
    </section>
  );
}
