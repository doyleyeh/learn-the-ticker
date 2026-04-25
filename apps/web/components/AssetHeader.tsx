import type { AssetFixture } from "../lib/fixtures";
import { assetPageExportUrl } from "../lib/exportControls";
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
      <div className="asset-header-actions" data-asset-header-actions="compare,export,sources">
        <a href="#compare-this-asset" data-asset-header-action="compare">
          Compare this asset
        </a>
        <a href={assetPageExportUrl(asset.ticker)} data-asset-header-action="export">
          Export
        </a>
        <a href="#asset-sources" data-asset-header-action="sources">
          View sources
        </a>
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
