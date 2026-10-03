import type { ReactNode } from "react";
import type { AssetFixture } from "../lib/fixtures";

type AssetModeLayoutProps = {
  asset: AssetFixture;
  beginnerMode: ReactNode;
  deepDiveMode: ReactNode;
  sourceTools: ReactNode;
};

export function AssetModeLayout({ asset, beginnerMode, deepDiveMode, sourceTools }: AssetModeLayoutProps) {
  const beginnerHeadingId = `beginner-mode-${asset.ticker.toLowerCase()}`;
  const deepDiveHeadingId = `deep-dive-mode-${asset.ticker.toLowerCase()}`;

  return (
    <section className="content-band two-column asset-mode-layout" data-asset-mode-layout data-asset-ticker={asset.ticker}>
      <div className="section-stack mode-stack">
        <section
          className="asset-mode-region beginner-mode-region"
          aria-labelledby={beginnerHeadingId}
          data-asset-mode-region="beginner"
          data-beginner-mode-region={asset.ticker}
        >
          <div className="mode-heading">
            <p className="eyebrow">Beginner Mode</p>
            <h2 id={beginnerHeadingId}>Beginner Mode</h2>
          </div>
          {beginnerMode}
        </section>

        <section
          className="asset-mode-region deep-dive-mode-region"
          aria-labelledby={deepDiveHeadingId}
          data-asset-mode-region="deep-dive"
          data-deep-dive-mode-region={asset.ticker}
        >
          <div className="mode-heading">
            <p className="eyebrow">Deep-Dive Mode</p>
            <h2 id={deepDiveHeadingId}>Deep-Dive Mode</h2>
          </div>
          {deepDiveMode}
        </section>
      </div>

      <aside className="sidebar" aria-label="Source and learning tools">
        {sourceTools}
      </aside>
    </section>
  );
}
