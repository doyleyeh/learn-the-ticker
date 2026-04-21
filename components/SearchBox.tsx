"use client";

import { useMemo, useRef, useState } from "react";
import type { AssetFixture } from "../lib/fixtures";

type SearchBoxProps = {
  assets: Record<string, AssetFixture>;
  unsupportedAssets: Record<string, string>;
};

type SearchState = "empty" | "loading" | "supported" | "multi" | "unsupported" | "unknown";

type SearchResolution = {
  state: Exclude<SearchState, "loading">;
  matches: AssetFixture[];
  unsupportedMessage?: string;
};

function normalizeSearchText(value: string) {
  return value.trim().toLowerCase();
}

function formatAssetType(asset: AssetFixture) {
  return asset.assetType === "etf" ? "ETF" : "Stock";
}

function searchableFields(asset: AssetFixture) {
  return [
    asset.ticker,
    asset.name,
    asset.assetType,
    asset.exchange,
    asset.issuer ?? "",
    asset.beginnerSummary.whatItIs,
    asset.beginnerSummary.whyPeopleConsiderIt,
    ...asset.claims.map((claim) => claim.claimText),
    ...asset.facts.flatMap((fact) => [fact.label, fact.value]),
    ...asset.sourceDocuments.flatMap((source) => [source.title, source.publisher, source.supportingPassage])
  ];
}

function matchScore(asset: AssetFixture, normalizedQuery: string, normalizedTicker: string) {
  const normalizedName = normalizeSearchText(asset.name);
  if (asset.ticker === normalizedTicker) {
    return 100;
  }
  if (normalizedName === normalizedQuery) {
    return 90;
  }
  if (normalizedName.startsWith(normalizedQuery)) {
    return 80;
  }
  if (normalizeSearchText(asset.issuer ?? "") === normalizedQuery) {
    return 70;
  }
  return 10;
}

function resolveLocalFixtureSearch(
  query: string,
  assets: Record<string, AssetFixture>,
  unsupportedAssets: Record<string, string>
): SearchResolution {
  const trimmed = query.trim();
  const normalizedQuery = normalizeSearchText(query);
  const normalizedTicker = trimmed.toUpperCase();

  if (!trimmed) {
    return { state: "empty", matches: [] };
  }

  const unsupportedMessage = unsupportedAssets[normalizedTicker];
  if (unsupportedMessage) {
    return { state: "unsupported", matches: [], unsupportedMessage };
  }

  const matches = Object.values(assets)
    .filter((asset) => searchableFields(asset).some((field) => normalizeSearchText(field).includes(normalizedQuery)))
    .sort((left, right) => {
      const scoreDifference =
        matchScore(right, normalizedQuery, normalizedTicker) - matchScore(left, normalizedQuery, normalizedTicker);
      return scoreDifference || left.ticker.localeCompare(right.ticker);
    });

  if (matches.length === 1) {
    return { state: "supported", matches };
  }

  if (matches.length > 1) {
    return { state: "multi", matches };
  }

  return { state: "unknown", matches: [] };
}

export function SearchBox({ assets, unsupportedAssets }: SearchBoxProps) {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<SearchState>("empty");
  const searchRequestId = useRef(0);
  const resolution = useMemo(
    () => resolveLocalFixtureSearch(query, assets, unsupportedAssets),
    [assets, query, unsupportedAssets]
  );
  const supportedAsset = resolution.state === "supported" ? resolution.matches[0] : undefined;
  const canOpenSupportedAsset = state === "supported" && Boolean(supportedAsset);

  const helperText = useMemo(() => {
    if (state === "empty") {
      return "Try VOO, QQQ, AAPL, Apple, Vanguard S&P 500 ETF, Invesco QQQ Trust, BTC, or ZZZZ.";
    }
    if (state === "loading") {
      return "Checking local fixtures only.";
    }
    if (state === "unsupported") {
      return resolution.unsupportedMessage ?? "This asset is outside the current local fixture scope.";
    }
    if (state === "unknown") {
      return "Unknown in the local skeleton data. No facts are invented for this ticker or name.";
    }
    if (state === "multi") {
      return "More than one supported local fixture matched. Choose a result instead of guessing.";
    }
    return supportedAsset
      ? `${supportedAsset.ticker} is the canonical ticker for ${supportedAsset.name} in local fixture data.`
      : "";
  }, [resolution.unsupportedMessage, state, supportedAsset]);

  function handleChange(value: string) {
    setQuery(value);
    const nextResolution = resolveLocalFixtureSearch(value, assets, unsupportedAssets);
    searchRequestId.current += 1;
    const requestId = searchRequestId.current;

    if (nextResolution.state === "empty") {
      setState("empty");
      return;
    }

    setState("loading");
    window.setTimeout(() => {
      if (requestId === searchRequestId.current) {
        setState(nextResolution.state);
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
          placeholder="VOO, Apple, or Nasdaq-100"
          onChange={(event) => handleChange(event.target.value)}
        />
        <a
          className={`search-button ${canOpenSupportedAsset ? "" : "disabled-link"}`}
          aria-disabled={!canOpenSupportedAsset}
          href={canOpenSupportedAsset && supportedAsset ? `/assets/${supportedAsset.ticker}` : "#search-status"}
        >
          Open
        </a>
      </div>
      <p id="search-status" className={`search-status status-${state}`} data-search-state={state}>
        {helperText}
      </p>
      {state === "supported" && supportedAsset ? (
        <div className="search-result-panel" data-search-supported-result>
          <a href={`/assets/${supportedAsset.ticker}`} data-search-result-link>
            {supportedAsset.ticker}
          </a>
          <span data-search-result-name>{supportedAsset.name}</span>
          <span data-search-result-type>{formatAssetType(supportedAsset)}</span>
          <span data-search-result-exchange>{supportedAsset.exchange}</span>
          {supportedAsset.issuer ? <span data-search-result-issuer>{supportedAsset.issuer}</span> : null}
        </div>
      ) : null}
      {state === "multi" ? (
        <div className="search-result-panel" data-search-multi-result>
          {resolution.matches.map((match) => (
            <a key={match.ticker} href={`/assets/${match.ticker}`} data-search-result-link>
              <strong>{match.ticker}</strong>
              <span>{match.name}</span>
            </a>
          ))}
        </div>
      ) : null}
      {state === "unsupported" ? <div className="search-state-note" data-search-unsupported-result /> : null}
      {state === "unknown" ? <div className="search-state-note" data-search-unknown-result /> : null}
      <div className="quick-links" aria-label="Supported examples">
        {Object.values(assets).map((example) => (
          <a key={example.ticker} href={`/assets/${example.ticker}`}>
            {example.ticker}
          </a>
        ))}
        <a href="/compare?left=VOO&right=QQQ">VOO vs QQQ</a>
      </div>
    </section>
  );
}
