import type { AssetFixture } from "../lib/fixtures";
import { FreshnessLabel } from "./FreshnessLabel";

type AssetHeaderProps = {
  asset: AssetFixture;
  layoutMarker?: string;
};

export function AssetHeader({ asset, layoutMarker = "header" }: AssetHeaderProps) {
  return (
    <section className="asset-hero" data-prd-section={layoutMarker} data-asset-header-layout="supported-asset-header">
      <p className="eyebrow">{asset.assetType === "etf" ? "ETF learning page" : "Stock learning page"}</p>
      <h1>
        {asset.name} <span>{asset.ticker}</span>
      </h1>
      <p>
        Deterministic fixture-backed overview for beginners, with stable facts kept separate from recent developments.
      </p>
      <div className="metadata-row">
        <span>{asset.exchange}</span>
        {asset.issuer ? <span>{asset.issuer}</span> : null}
        <span>{asset.assetType.toUpperCase()}</span>
      </div>
      <div className="freshness-row">
        <FreshnessLabel label="Page last updated" value={asset.freshness.pageLastUpdatedAt} state="fresh" />
        <FreshnessLabel label="Facts as of" value={asset.freshness.factsAsOf} state="fresh" />
        <FreshnessLabel
          label="Holdings as of"
          value={asset.freshness.holdingsAsOf}
          state={asset.freshness.holdingsAsOf ? "fresh" : "unknown"}
        />
      </div>
    </section>
  );
}
