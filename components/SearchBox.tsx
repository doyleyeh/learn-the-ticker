"use client";

import { useMemo, useState } from "react";
import type { AssetFixture } from "../lib/fixtures";

type SearchBoxProps = {
  assets: Record<string, AssetFixture>;
  unsupportedAssets: Record<string, string>;
};

type SearchState = "empty" | "loading" | "supported" | "unsupported" | "unknown";

export function SearchBox({ assets, unsupportedAssets }: SearchBoxProps) {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<SearchState>("empty");
  const normalized = query.trim().toUpperCase();
  const asset = assets[normalized];
  const unsupportedMessage = unsupportedAssets[normalized];

  const helperText = useMemo(() => {
    if (state === "empty") {
      return "Try VOO, QQQ, AAPL, BTC, or ZZZZ.";
    }
    if (state === "loading") {
      return "Checking local fixtures only.";
    }
    if (state === "unsupported") {
      return unsupportedMessage;
    }
    if (state === "unknown") {
      return "Unknown in the local skeleton data. No facts are invented for this ticker.";
    }
    return `${asset.name} is available from deterministic fixture data.`;
  }, [asset, state, unsupportedMessage]);

  function handleChange(value: string) {
    setQuery(value);
    const next = value.trim().toUpperCase();

    if (!next) {
      setState("empty");
      return;
    }

    setState("loading");
    window.setTimeout(() => {
      if (assets[next]) {
        setState("supported");
      } else if (unsupportedAssets[next]) {
        setState("unsupported");
      } else {
        setState("unknown");
      }
    }, 120);
  }

  return (
    <section className="search-workflow" aria-label="Ticker search">
      <label htmlFor="ticker-search">Ticker or asset name</label>
      <div className="search-row">
        <input
          id="ticker-search"
          name="q"
          value={query}
          placeholder="VOO, QQQ, or AAPL"
          onChange={(event) => handleChange(event.target.value)}
        />
        <a
          className={`search-button ${state === "supported" ? "" : "disabled-link"}`}
          aria-disabled={state !== "supported"}
          href={state === "supported" ? `/assets/${normalized}` : "#search-status"}
        >
          Open
        </a>
      </div>
      <p id="search-status" className={`search-status status-${state}`} data-search-state={state}>
        {helperText}
      </p>
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
