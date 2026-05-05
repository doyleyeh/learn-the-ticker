import type { AssetFixture } from "../lib/fixtures";
import { FreshnessDisclosure } from "./FreshnessLabel";

type AssetHeaderProps = {
  asset: AssetFixture;
  layoutMarker?: string;
};

export function AssetHeader({ asset, layoutMarker = "header" }: AssetHeaderProps) {
  return (
    <section className="asset-hero" data-prd-section={layoutMarker} data-asset-header-layout="supported-asset-header">
      <div className="asset-hero-main">
        <p className="eyebrow">{asset.assetType === "etf" ? "ETF learning page" : "Stock learning page"}</p>
        <h1>
          {asset.name} <span>{asset.ticker}</span>
        </h1>
        <p>
          Source-labeled beginner overview with stable facts kept separate from recent developments and unavailable
          fields called out clearly.
        </p>
        <div className="metadata-row">
          <span>{asset.exchange}</span>
          {asset.issuer ? <span>{asset.issuer}</span> : null}
          <span>{asset.assetType.toUpperCase()}</span>
        </div>
      </div>
      <div className="freshness-row">
        <FreshnessDisclosure label="Page updated" value={asset.freshness.pageLastUpdatedAt} state="fresh" />
        <FreshnessDisclosure label="Facts as of" value={asset.freshness.factsAsOf} state="fresh" />
        <FreshnessDisclosure
          label="Holdings as of"
          value={asset.freshness.holdingsAsOf}
          state={asset.freshness.holdingsAsOf ? "fresh" : "unknown"}
        />
      </div>
    </section>
  );
}
