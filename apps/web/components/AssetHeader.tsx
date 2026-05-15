import type { AssetFixture } from "../lib/fixtures";
import { CompactCitationSources } from "./CompactCitationSources";

type AssetHeaderProps = {
  asset: AssetFixture;
  layoutMarker?: string;
};

export function AssetHeader({ asset, layoutMarker = "header" }: AssetHeaderProps) {
  const headerMetadata = [
    { label: "Page updated", value: asset.freshness.pageLastUpdatedAt, state: "fresh" },
    { label: "Facts as of", value: asset.freshness.factsAsOf, state: "fresh" },
    { label: "Holdings as of", value: asset.freshness.holdingsAsOf ?? null, state: asset.freshness.holdingsAsOf ? "fresh" : "unknown" },
    { label: "Issuer", value: asset.issuer ?? null }
  ];

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
          <span>{asset.assetType.toUpperCase()}</span>
          <CompactCitationSources
            citations={asset.citations.slice(0, 3)}
            label={`${asset.ticker} page evidence details`}
            metadataRows={headerMetadata}
            dashboardSourceIcon
          />
        </div>
      </div>
    </section>
  );
}
